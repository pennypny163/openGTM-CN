"""
tencent_integration.py - 腾讯生态集成（企业微信 + 腾讯文档）。

提供：
  - 企业微信：发送外展提醒消息、创建日程
  - 腾讯文档：读写线索数据（替代Google Sheets）

配置：
  通过企业微信群机器人Webhook实现消息推送，无需复杂OAuth流程。
  腾讯文档通过开放API读写数据。

环境变量：
  CRM_WEBHOOK_URL          - 企业微信群机器人Webhook URL
  TENCENT_DOC_APP_ID       - 腾讯文档应用ID（可选）
  TENCENT_DOC_APP_SECRET   - 腾讯文档应用密钥（可选）
  TENCENT_DOC_SPREADSHEET_ID - 腾讯文档电子表格ID（可选）
"""

from __future__ import annotations

import json
import os
import subprocess
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

CRM_WEBHOOK_URL = os.environ.get("CRM_WEBHOOK_URL", "")
TENCENT_DOC_APP_ID = os.environ.get("TENCENT_DOC_APP_ID", "")
TENCENT_DOC_APP_SECRET = os.environ.get("TENCENT_DOC_APP_SECRET", "")
TENCENT_DOC_SPREADSHEET_ID = os.environ.get("TENCENT_DOC_SPREADSHEET_ID", "")


# =========================================================================
# 企业微信群机器人集成
# =========================================================================

def _send_wecom_message(webhook_url: str, msg_type: str, content: dict, timeout: int = 30) -> bool:
    """通过企业微信群机器人Webhook发送消息。"""
    if not webhook_url:
        raise ValueError("CRM_WEBHOOK_URL 未设置。请在 .env 中配置企业微信群机器人Webhook URL。")

    payload = json.dumps({"msgtype": msg_type, msg_type: content})
    result = subprocess.run(
        ["curl", "-s", "-L", "--max-time", str(timeout),
         "-H", "Content-Type: application/json",
         "-d", payload, webhook_url],
        capture_output=True, text=True, timeout=timeout + 10,
    )
    if result.returncode != 0:
        raise RuntimeError(f"curl退出码 {result.returncode}: {result.stderr[:200]}")
    try:
        resp = json.loads(result.stdout)
        return resp.get("errcode") == 0
    except json.JSONDecodeError:
        return False


def send_outreach_reminder(
    lead: dict,
    touch_number: int = 1,
    webhook_url: Optional[str] = None,
) -> bool:
    """
    通过企业微信群机器人发送外展提醒。

    Args:
        lead: 线索字典，包含company, domain, contact_name, messages等
        touch_number: 触点编号（1-4）
        webhook_url: Webhook URL（默认使用CRM_WEBHOOK_URL环境变量）

    Returns:
        是否发送成功
    """
    url = webhook_url or CRM_WEBHOOK_URL

    company = lead.get("company", lead.get("domain", "未知"))
    contact = lead.get("contact_name", "")
    domain = lead.get("domain", "")
    tier = lead.get("qualification", {}).get("tier", "") if "qualification" in lead else lead.get("tier", "")
    score = lead.get("qualification", {}).get("score", "") if "qualification" in lead else lead.get("score", "")

    touch_labels = {
        1: "LinkedIn连接请求",
        2: "跟进私信",
        3: "同行对比消息",
        4: "告别消息",
    }
    touch_label = touch_labels.get(touch_number, f"触点{touch_number}")

    messages = lead.get("messages", {})
    msg_keys = {1: "connection_note", 2: "first_dm", 3: "followup", 4: "followup_2"}
    message_text = messages.get(msg_keys.get(touch_number, ""), "")

    tier_map = {"hot": "🔥热门", "warm": "🌤温暖", "cold": "❄️冷淡"}
    tier_display = tier_map.get(tier, tier.upper() if tier else "N/A")

    markdown = (
        f"### 🎯 外展提醒：触点#{touch_number} - {touch_label}\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"> **公司**：{company}\n"
        f"> **域名**：{domain}\n"
        f"> **联系人**：{contact}\n"
        f"> **等级**：{tier_display} | **评分**：{score}\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"📝 **待发送消息**：\n{message_text}\n\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"LinkedIn：{lead.get('linkedin_url', 'N/A')}\n"
        f"邮箱：{lead.get('contact_email', 'N/A')}"
    )

    return _send_wecom_message(url, "markdown", {"content": markdown})


def schedule_outreach_sequence(
    leads: list[dict],
    start_date: Optional[str] = None,
    daily_limit: int = 20,
    webhook_url: Optional[str] = None,
) -> list[dict]:
    """
    为多个线索安排完整的外展序列提醒。

    Args:
        leads: 线索字典列表（包含messages）
        start_date: 开始日期 YYYY-MM-DD（默认：明天）
        daily_limit: 每日最大事件数（默认：20）
        webhook_url: Webhook URL

    Returns:
        已发送提醒的列表
    """
    url = webhook_url or CRM_WEBHOOK_URL
    sent_reminders = []
    daily_count = 0

    if start_date:
        current_date = datetime.strptime(start_date, "%Y-%m-%d")
    else:
        current_date = datetime.now() + timedelta(days=1)

    for lead in leads:
        if daily_count >= daily_limit:
            current_date += timedelta(days=1)
            daily_count = 0

        # 仅发送触点1的提醒（其他触点由序列管理器自动触发）
        try:
            ok = send_outreach_reminder(lead, touch_number=1, webhook_url=url)
            if ok:
                sent_reminders.append({"company": lead.get("company", ""), "touch": 1, "status": "已发送"})
        except Exception as e:
            print(f"  发送触点1提醒失败 {lead.get('company', '?')}：{e}")

        daily_count += 1

    return sent_reminders


# =========================================================================
# 企业微信邮件/消息集成
# =========================================================================

def send_text_message(
    content: str,
    webhook_url: Optional[str] = None,
    mentioned_list: Optional[list] = None,
) -> bool:
    """
    通过企业微信群机器人发送文本消息。

    Args:
        content: 消息内容
        webhook_url: Webhook URL
        mentioned_list: @的用户列表

    Returns:
        是否发送成功
    """
    url = webhook_url or CRM_WEBHOOK_URL
    msg = {"content": content}
    if mentioned_list:
        msg["mentioned_list"] = mentioned_list
    return _send_wecom_message(url, "text", msg)


def send_lead_card(
    lead: dict,
    webhook_url: Optional[str] = None,
) -> bool:
    """
    发送线索卡片到企业微信群。

    Args:
        lead: 线索字典
        webhook_url: Webhook URL

    Returns:
        是否发送成功
    """
    url = webhook_url or CRM_WEBHOOK_URL

    company = lead.get("company", "未知")
    domain = lead.get("domain", "")
    industry = lead.get("industry", "")
    contact = lead.get("contact_name", "")
    score = lead.get("qualification", {}).get("score", "N/A") if "qualification" in lead else "N/A"
    tier = lead.get("qualification", {}).get("tier", "") if "qualification" in lead else ""

    tier_map = {"hot": "🔥热门", "warm": "🌤温暖", "cold": "❄️冷淡"}
    tier_display = tier_map.get(tier, "未评分")

    markdown = (
        f"### 📋 线索卡片：{company}\n"
        f"> **域名**：[{domain}](https://{domain})\n"
        f"> **行业**：{industry}\n"
        f"> **联系人**：{contact}\n"
        f"> **ICP评分**：{score}/100 {tier_display}\n"
    )

    return _send_wecom_message(url, "markdown", {"content": markdown})


# =========================================================================
# 腾讯文档集成（简化版 - 通过HTTP API）
# =========================================================================

def write_leads_to_doc(
    leads: list[dict],
    spreadsheet_id: Optional[str] = None,
    sheet_name: str = "线索",
) -> dict:
    """
    将线索写入腾讯文档电子表格（占位实现）。

    注意：完整的腾讯文档API集成需要企业微信开放平台的应用授权。
    当前版本提供数据格式化功能，实际写入需配置API凭证。

    Args:
        leads: 线索字典列表
        spreadsheet_id: 腾讯文档电子表格ID
        sheet_name: 工作表名称（默认："线索"）

    Returns:
        操作结果字典
    """
    sid = spreadsheet_id or TENCENT_DOC_SPREADSHEET_ID

    if not sid:
        return {
            "status": "未配置",
            "message": "请设置 TENCENT_DOC_SPREADSHEET_ID 环境变量",
            "data_prepared": len(leads),
        }

    # 定义列头
    headers = [
        "公司", "域名", "行业", "地区",
        "联系人", "职位", "邮箱", "LinkedIn",
        "ICP评分", "等级", "推荐操作",
        "消息模式", "连接请求", "首次私信",
        "调研备注", "状态",
    ]

    rows = [headers]
    for lead in leads:
        qual = lead.get("qualification", {})
        msgs = lead.get("messages", {})
        audit = lead.get("audit", lead.get("research", {}))

        tier_map = {"hot": "热门", "warm": "温暖", "cold": "冷淡"}
        rows.append([
            lead.get("company", ""),
            lead.get("domain", ""),
            lead.get("industry", ""),
            lead.get("region", ""),
            lead.get("contact_name", ""),
            lead.get("contact_title", ""),
            lead.get("contact_email", ""),
            lead.get("linkedin_url", ""),
            qual.get("score", ""),
            tier_map.get(qual.get("tier", ""), qual.get("tier", "")),
            qual.get("recommended_action", ""),
            msgs.get("pattern", ""),
            msgs.get("connection_note", ""),
            msgs.get("first_dm", ""),
            audit.get("overall_assessment", "") if isinstance(audit, dict) else "",
            "新线索",
        ])

    # TODO: 实际调用腾讯文档API写入数据
    # 当前返回准备好的数据
    return {
        "status": "数据已准备",
        "message": f"已准备 {len(leads)} 条线索数据，待写入腾讯文档",
        "spreadsheet_id": sid,
        "sheet_name": sheet_name,
        "rows": len(rows),
        "data": rows,
    }


def read_leads_from_doc(
    spreadsheet_id: Optional[str] = None,
    sheet_name: str = "线索",
) -> list[dict]:
    """
    从腾讯文档电子表格读取线索（占位实现）。

    Args:
        spreadsheet_id: 腾讯文档电子表格ID
        sheet_name: 工作表名称

    Returns:
        线索字典列表
    """
    sid = spreadsheet_id or TENCENT_DOC_SPREADSHEET_ID

    if not sid:
        print("[腾讯文档] 未配置 TENCENT_DOC_SPREADSHEET_ID", flush=True)
        return []

    # TODO: 实际调用腾讯文档API读取数据
    print(f"[腾讯文档] 读取功能待实现（表格ID：{sid}，工作表：{sheet_name}）", flush=True)
    return []


def write_analytics_to_doc(
    analytics_data: dict,
    spreadsheet_id: Optional[str] = None,
    sheet_name: str = "分析报告",
) -> dict:
    """
    将AEO健康检查结果写入腾讯文档。

    Args:
        analytics_data: 来自analytics.run_health_check()的字典
        spreadsheet_id: 腾讯文档电子表格ID
        sheet_name: 工作表名称

    Returns:
        操作结果字典
    """
    sid = spreadsheet_id or TENCENT_DOC_SPREADSHEET_ID

    headers = ["检查项", "状态", "严重度", "详情"]
    rows = [headers]

    findings = analytics_data.get("findings", analytics_data.get("health", {}).get("findings", []))
    for f in findings:
        rows.append([
            f.get("check", f.get("type", "")),
            f.get("status", ""),
            f.get("severity", ""),
            f.get("detail", ""),
        ])

    score = analytics_data.get("score", analytics_data.get("health", {}).get("score", ""))
    grade = analytics_data.get("grade", analytics_data.get("health", {}).get("grade", ""))
    rows.append([])
    rows.append(["总分", str(score), grade, ""])

    return {
        "status": "数据已准备",
        "spreadsheet_id": sid,
        "sheet_name": sheet_name,
        "rows": len(rows),
        "data": rows,
    }


def write_keywords_to_doc(
    keywords: list[dict],
    spreadsheet_id: Optional[str] = None,
    sheet_name: str = "关键词",
) -> dict:
    """
    将SEO关键词研究结果写入腾讯文档。

    Args:
        keywords: 来自keywords.research_keywords()的关键词字典列表
        spreadsheet_id: 腾讯文档电子表格ID
        sheet_name: 工作表名称

    Returns:
        操作结果字典
    """
    sid = spreadsheet_id or TENCENT_DOC_SPREADSHEET_ID

    headers = ["关键词", "评分", "聚类", "搜索意图", "难度", "内容简报"]
    rows = [headers]

    for kw in keywords:
        brief = kw.get("content_brief", {})
        brief_summary = brief.get("title", "") if isinstance(brief, dict) else str(brief)[:100]
        rows.append([
            kw.get("keyword", ""),
            kw.get("score", ""),
            kw.get("cluster", ""),
            kw.get("search_intent", ""),
            kw.get("difficulty", ""),
            brief_summary,
        ])

    return {
        "status": "数据已准备",
        "spreadsheet_id": sid,
        "sheet_name": sheet_name,
        "rows": len(rows),
        "data": rows,
    }


# =========================================================================
# 便捷方法：检查集成是否已配置
# =========================================================================

def is_configured() -> bool:
    """检查企业微信Webhook是否已配置。"""
    return bool(CRM_WEBHOOK_URL)


def is_doc_configured() -> bool:
    """检查腾讯文档API是否已配置。"""
    return bool(TENCENT_DOC_APP_ID and TENCENT_DOC_APP_SECRET)
