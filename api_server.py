"""
api_server.py - Flask Web服务器，为OpenGTM提供REST API和前端页面。

提供：
  - 静态前端页面（现代化仪表盘UI）
  - REST API端点，暴露所有后端功能
"""

import json
import os
import sys
import traceback
from pathlib import Path

from flask import Flask, jsonify, request, render_template, send_from_directory
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

# 确保opengtm包可导入
sys.path.insert(0, str(Path(__file__).parent))

from opengtm.analytics import run_health_check
from opengtm.qualify import qualify, qualify_batch, ICP_PROFILES, INDUSTRY_TIERS
from opengtm.discover import discover
from opengtm.research import research
from opengtm.outreach import OutreachSequence
from opengtm.sync import sync_leads, build_sync_payload
from opengtm.context import extract_context
from opengtm.tencent_integration import (
    is_configured as wecom_configured,
    is_doc_configured as doc_configured,
    send_lead_card,
    send_text_message,
)

app = Flask(
    __name__,
    template_folder="templates",
    static_folder="static",
)

# 全局外展序列实例（内存中）
_outreach_seq = OutreachSequence()


# =========================================================================
# 页面路由
# =========================================================================

@app.route("/")
def index():
    """主页面"""
    return render_template("index.html")


# =========================================================================
# API: 系统状态
# =========================================================================

@app.route("/api/status")
def api_status():
    """返回系统配置状态"""
    return jsonify({
        "version": "0.2.0",
        "llm_configured": bool(os.environ.get("OPENAI_API_KEY") or os.environ.get("HUNYUAN_API_KEY")),
        "wecom_configured": wecom_configured(),
        "doc_configured": doc_configured(),
        "model": os.environ.get("HUNYUAN_MODEL") or os.environ.get("LLM_MODEL") or "hunyuan-lite",
        "language": os.environ.get("DEFAULT_LANGUAGE", "zh"),
        "daily_limit": int(os.environ.get("DEFAULT_DAILY_LIMIT", "20")),
        "icp_profiles": list(ICP_PROFILES.keys()),
        "industry_tiers": INDUSTRY_TIERS,
    })


# =========================================================================
# API: AEO健康检查
# =========================================================================

@app.route("/api/health-check", methods=["POST"])
def api_health_check():
    """运行AEO/SEO健康检查"""
    data = request.get_json(force=True)
    url = data.get("url", "").strip()
    timeout = data.get("timeout", 30)

    if not url:
        return jsonify({"error": "请输入URL"}), 400

    if not url.startswith("http"):
        url = "https://" + url

    try:
        result = run_health_check(url, timeout=timeout)
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": f"健康检查失败：{str(e)}"}), 500


# =========================================================================
# API: 线索发现
# =========================================================================

@app.route("/api/discover", methods=["POST"])
def api_discover():
    """通过LLM发现目标公司"""
    data = request.get_json(force=True)
    industry = data.get("industry", "").strip()
    region = data.get("region", "").strip()
    limit = min(int(data.get("limit", 10)), 30)
    validate = data.get("validate", True)

    if not industry or not region:
        return jsonify({"error": "请输入行业和地区"}), 400

    try:
        leads = discover(
            industry=industry,
            region=region,
            limit=limit,
            validate=validate,
            verbose=False,
        )
        return jsonify({"leads": leads, "count": len(leads)})
    except Exception as e:
        return jsonify({"error": f"线索发现失败：{str(e)}"}), 500


# =========================================================================
# API: 公司调研
# =========================================================================

@app.route("/api/research", methods=["POST"])
def api_research():
    """调研公司网站"""
    data = request.get_json(force=True)
    domain = data.get("domain", "").strip()
    company = data.get("company", "").strip()
    industry = data.get("industry", "").strip()

    if not domain:
        return jsonify({"error": "请输入域名"}), 400

    try:
        result = research(
            domain=domain,
            company=company,
            industry=industry,
            verbose=False,
        )
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": f"调研失败：{str(e)}"}), 500


# =========================================================================
# API: ICP评分
# =========================================================================

@app.route("/api/qualify", methods=["POST"])
def api_qualify():
    """对线索进行ICP评分"""
    data = request.get_json(force=True)
    lead = data.get("lead", data)
    icp_profile = data.get("icp_profile", "default")

    try:
        result = qualify(lead, icp_profile=icp_profile)
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": f"评分失败：{str(e)}"}), 500


@app.route("/api/qualify-batch", methods=["POST"])
def api_qualify_batch():
    """批量ICP评分"""
    data = request.get_json(force=True)
    leads = data.get("leads", [])
    icp_profile = data.get("icp_profile", "default")

    if not leads:
        return jsonify({"error": "请提供线索列表"}), 400

    try:
        results = qualify_batch(leads, icp_profile=icp_profile, verbose=False)
        return jsonify({"results": results, "count": len(results)})
    except Exception as e:
        return jsonify({"error": f"批量评分失败：{str(e)}"}), 500


# =========================================================================
# API: 公司上下文提取
# =========================================================================

@app.route("/api/context", methods=["POST"])
def api_context():
    """提取公司上下文信息"""
    data = request.get_json(force=True)
    url = data.get("url", "").strip()

    if not url:
        return jsonify({"error": "请输入URL"}), 400

    try:
        result = extract_context(url, fallback_on_error=True)
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": f"上下文提取失败：{str(e)}"}), 500


# =========================================================================
# API: 外展序列
# =========================================================================

@app.route("/api/outreach/stats")
def api_outreach_stats():
    """获取外展序列统计"""
    return jsonify(_outreach_seq.get_stats())


@app.route("/api/outreach/due")
def api_outreach_due():
    """获取今日待处理线索"""
    due = _outreach_seq.get_due_today()
    return jsonify({"due": due, "count": len(due)})


@app.route("/api/outreach/add", methods=["POST"])
def api_outreach_add():
    """添加线索到外展序列"""
    data = request.get_json(force=True)
    leads = data.get("leads", [data] if "domain" in data else [])
    added = _outreach_seq.add_leads(leads)
    return jsonify({"added": added, "total": len(_outreach_seq._state)})


@app.route("/api/outreach/send", methods=["POST"])
def api_outreach_send():
    """标记触点已发送"""
    data = request.get_json(force=True)
    domain = data.get("domain", "")
    touch = int(data.get("touch", 1))
    ok = _outreach_seq.mark_sent(domain, touch)
    return jsonify({"success": ok})


# =========================================================================
# API: CRM同步
# =========================================================================

@app.route("/api/sync", methods=["POST"])
def api_sync():
    """同步线索到企业微信"""
    data = request.get_json(force=True)
    leads = data.get("leads", [])
    dry_run = data.get("dry_run", False)

    if not leads:
        return jsonify({"error": "请提供线索列表"}), 400

    try:
        result = sync_leads(leads, dry_run=dry_run, verbose=False)
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": f"同步失败：{str(e)}"}), 500


@app.route("/api/sync/send-card", methods=["POST"])
def api_sync_send_card():
    """发送线索卡片到企业微信"""
    data = request.get_json(force=True)
    try:
        ok = send_lead_card(data)
        return jsonify({"success": ok})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# =========================================================================
# API: 一键流水线
# =========================================================================

@app.route("/api/pipeline", methods=["POST"])
def api_pipeline():
    """运行完整GTM流水线：发现→调研→评分→消息生成"""
    import time
    from opengtm.message import generate_messages

    data = request.get_json(force=True)
    industry = data.get("industry", "").strip()
    region = data.get("region", "").strip()
    limit = min(int(data.get("limit", 5)), 20)
    language = data.get("language", "zh")
    icp_profile = data.get("icp_profile", "default")

    if not industry or not region:
        return jsonify({"error": "请填写行业和地区"}), 400

    try:
        # Step 1: 发现
        prospects = discover(industry=industry, region=region, limit=limit, validate=True, verbose=False)
        if not prospects:
            return jsonify({"error": "未发现任何公司", "step": "discover"}), 404

        # Step 2: 调研
        researched = []
        for p in prospects:
            audit = research(domain=p["domain"], company=p.get("company", ""), industry=p.get("industry", ""), verbose=False)
            contact = audit.get("contact", {})
            researched.append({
                **p,
                "contact_name": contact.get("name", ""),
                "contact_title": contact.get("title", ""),
                "contact_email": contact.get("email"),
                "linkedin_url": contact.get("linkedin_url"),
                "audit": audit,
            })
            time.sleep(1)

        # Step 3: 评分
        qualified = qualify_batch(researched, icp_profile=icp_profile, verbose=False)

        # Step 4: 消息生成
        for lead in qualified:
            messages = generate_messages(
                domain=lead["domain"],
                company=lead.get("company", ""),
                contact_name=lead.get("contact_name", ""),
                industry=lead.get("industry", ""),
                audit=lead.get("audit"),
                region=region,
                contact_title=lead.get("contact_title", ""),
                language=language,
            )
            lead["messages"] = messages

        hot = sum(1 for r in qualified if r.get("qualification", {}).get("tier") == "hot")
        warm = sum(1 for r in qualified if r.get("qualification", {}).get("tier") == "warm")
        cold = sum(1 for r in qualified if r.get("qualification", {}).get("tier") == "cold")

        return jsonify({
            "results": qualified,
            "summary": {"total": len(qualified), "hot": hot, "warm": warm, "cold": cold}
        })
    except Exception as e:
        return jsonify({"error": f"流水线执行失败：{str(e)}"}), 500


# =========================================================================
# 启动
# =========================================================================

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=True)
