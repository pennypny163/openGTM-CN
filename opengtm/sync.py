"""
sync.py - CRM同步，通过企业微信群机器人Webhook推送。

将线索数据推送到企业微信群，支持Markdown格式的消息卡片。
也支持通用HTTP Webhook（如飞书、钉钉等）。

配置环境变量：
  CRM_WEBHOOK_URL   - 企业微信群机器人Webhook URL
  CRM_WEBHOOK_TOKEN - 认证令牌（作为?token=查询参数发送）
"""

from __future__ import annotations

import json
import os
import subprocess
import time
from typing import Optional

CRM_WEBHOOK_URL = os.environ.get("CRM_WEBHOOK_URL", "")
CRM_WEBHOOK_TOKEN = os.environ.get("CRM_WEBHOOK_TOKEN", "")


def _post_to_webhook(
    data: list[dict],
    webhook_url: str,
    token: str,
    timeout: int = 120,
) -> bool:
    """通过curl向Webhook发送POST数据。"""
    if not webhook_url:
        raise ValueError(
            "CRM_WEBHOOK_URL 未设置。"
            "请在 .env 文件或环境变量中设置。"
        )

    url = f"{webhook_url}?token={token}" if token else webhook_url

    # 构建企业微信群机器人格式的消息
    # 如果是企业微信webhook，使用markdown格式
    if "qyapi.weixin.qq.com" in webhook_url:
        for item in data:
            markdown_content = _build_wecom_markdown(item)
            payload = json.dumps({
                "msgtype": "markdown",
                "markdown": {"content": markdown_content}
            })
            result = subprocess.run(
                ["curl", "-s", "-L", "--max-time", str(timeout),
                 "-H", "Content-Type: application/json",
                 "-d", payload, url],
                capture_output=True, text=True, timeout=timeout + 10,
            )
            if result.returncode != 0:
                raise RuntimeError(f"curl退出码 {result.returncode}: {result.stderr[:200]}")
            time.sleep(0.5)  # 避免频率限制
        return True
    else:
        # 通用webhook格式
        payload = json.dumps(data)
        result = subprocess.run(
            ["curl", "-s", "-L", "--max-time", str(timeout),
             "-H", "Content-Type: application/json",
             "-d", payload, url],
            capture_output=True, text=True, timeout=timeout + 10,
        )

        if result.returncode != 0:
            raise RuntimeError(f"curl退出码 {result.returncode}: {result.stderr[:200]}")

        try:
            resp = json.loads(result.stdout)
            return resp.get("status") == "ok" or resp.get("errcode") == 0
        except json.JSONDecodeError:
            return "ok" in result.stdout.lower()


def _build_wecom_markdown(lead: dict) -> str:
    """构建企业微信Markdown格式的线索卡片。"""
    company = lead.get("company", "未知")
    domain = lead.get("domain", "")
    industry = lead.get("industry", "")
    contact_name = lead.get("contact_name", "")
    contact_title = lead.get("contact_title", "")
    email = lead.get("contact_email", "")
    linkedin = lead.get("linkedin_url", "")
    status = lead.get("status", "新线索")
    notes = lead.get("research_notes", "")

    lines = [
        f"### 🎯 新线索：{company}",
        f"> **域名**：{domain}",
    ]
    if industry:
        lines.append(f"> **行业**：{industry}")
    if contact_name:
        lines.append(f"> **联系人**：{contact_name}")
    if contact_title:
        lines.append(f"> **职位**：{contact_title}")
    if email:
        lines.append(f"> **邮箱**：{email}")
    if linkedin:
        lines.append(f"> **LinkedIn**：[查看主页]({linkedin})")
    lines.append(f"> **状态**：{status}")
    if notes:
        lines.append(f"\n**调研备注**：{notes[:200]}")

    return "\n".join(lines)


def sync_leads(
    leads: list[dict],
    webhook_url: Optional[str] = None,
    token: Optional[str] = None,
    batch_size: int = 50,
    dry_run: bool = False,
    verbose: bool = True,
) -> dict:
    """
    将线索列表同步到CRM（通过企业微信群机器人Webhook）。

    每个线索字典映射为一条CRM消息。预期键：
      company, domain, industry, contact_name, contact_title,
      linkedin_url, contact_email, status, research_notes,
      linkedin_connection, linkedin_followup

    Args:
        leads:       线索字典列表
        webhook_url: Webhook URL（默认使用CRM_WEBHOOK_URL环境变量）
        token:       认证令牌（默认使用CRM_WEBHOOK_TOKEN环境变量）
        batch_size:  每次HTTP调用的行数（默认50）
        dry_run:     仅打印将要同步的内容，不实际发送
        verbose:     是否输出进度

    Returns:
        包含以下键的字典：synced (int), skipped (int), errors (list)
    """
    url = webhook_url or CRM_WEBHOOK_URL
    tok = token or CRM_WEBHOOK_TOKEN

    if dry_run:
        if verbose:
            print(f"[同步] 模拟运行：将同步 {len(leads)} 条线索", flush=True)
            for lead in leads[:5]:
                print(f"  {lead.get('company', '?')}（{lead.get('domain', '?')}）", flush=True)
            if len(leads) > 5:
                print(f"  ... 以及其他 {len(leads) - 5} 条", flush=True)
        return {"synced": 0, "skipped": 0, "errors": [], "dry_run": True}

    synced = 0
    errors = []

    for i in range(0, len(leads), batch_size):
        batch = leads[i:i + batch_size]
        batch_num = i // batch_size + 1
        total_batches = (len(leads) + batch_size - 1) // batch_size

        try:
            ok = _post_to_webhook(batch, url, tok)
            if ok:
                synced += len(batch)
                if verbose:
                    print(
                        f"  批次 [{batch_num}/{total_batches}]："
                        f"{len(batch)} 条已同步",
                        flush=True,
                    )
            else:
                errors.append(f"批次 {batch_num}：Webhook返回非成功状态")
                if verbose:
                    print(f"  批次 [{batch_num}/{total_batches}]：失败", flush=True)
        except Exception as e:
            errors.append(f"批次 {batch_num}：{e}")
            if verbose:
                print(f"  批次 [{batch_num}/{total_batches}]：错误 - {e}", flush=True)

        if i + batch_size < len(leads):
            time.sleep(1)

    if verbose:
        print(f"[同步] 完成：{synced}/{len(leads)} 已同步，{len(errors)} 个错误", flush=True)

    return {"synced": synced, "skipped": len(leads) - synced, "errors": errors}


def build_sync_payload(prospect: dict) -> dict:
    """
    将完整的潜客字典（来自流水线）转换为CRM行格式。

    Args:
        prospect: 包含以下键的字典：company, domain, industry, contact_name,
                  contact_title, linkedin_url, contact_email, audit, messages

    Returns:
        准备好发送到Webhook的扁平字典
    """
    messages = prospect.get("messages", {})
    audit = prospect.get("audit", {})

    # 从最佳发现构建调研备注
    best = messages.get("best_finding", "")
    if best and isinstance(best, dict):
        research_notes = best.get("detail", str(best))
    elif best:
        research_notes = str(best)
    elif messages.get("pattern") == "E":
        research_notes = audit.get("overall_assessment", "")
    else:
        research_notes = messages.get("pattern_reason", "")

    return {
        "company": prospect.get("company", ""),
        "domain": prospect.get("domain", ""),
        "industry": prospect.get("industry", ""),
        "contact_name": prospect.get("contact_name", ""),
        "contact_title": prospect.get("contact_title", ""),
        "linkedin_url": prospect.get("linkedin_url"),
        "contact_email": prospect.get("contact_email"),
        "status": "新线索",
        "research_notes": research_notes,
        "linkedin_connection": messages.get("connection_note", ""),
        "linkedin_followup": messages.get("first_dm", ""),
    }
