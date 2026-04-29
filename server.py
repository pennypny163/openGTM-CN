"""
server.py - OpenGTM Web API 服务。

基于Python标准库http.server，无需额外依赖。
为前端提供REST API接口，封装所有opengtm后端模块。
启动方式: python server.py
"""

from __future__ import annotations

import json
import os
import sys
import traceback
from http.server import HTTPServer, SimpleHTTPRequestHandler
from pathlib import Path
from urllib.parse import urlparse, parse_qs

# 将项目根目录添加到路径
PROJECT_ROOT = Path(__file__).parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

# 加载.env文件
env_file = PROJECT_ROOT / ".env"
if env_file.exists():
    with open(env_file) as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, _, val = line.partition("=")
                if key.strip() not in os.environ:
                    os.environ[key.strip()] = val.strip().strip('"').strip("'")


# =========================================================================
# API 路由处理
# =========================================================================

def handle_status():
    """返回系统状态和配置信息。"""
    from opengtm import __version__, DEFAULT_MODEL
    has_key = bool(os.environ.get("OPENAI_API_KEY") or os.environ.get("HUNYUAN_API_KEY"))
    has_webhook = bool(os.environ.get("CRM_WEBHOOK_URL"))
    return {
        "status": "ok",
        "version": __version__,
        "model": os.environ.get("HUNYUAN_MODEL") or os.environ.get("LLM_MODEL") or DEFAULT_MODEL,
        "base_url": os.environ.get("OPENAI_BASE_URL", ""),
        "api_key_configured": has_key,
        "webhook_configured": has_webhook,
        "language": os.environ.get("DEFAULT_LANGUAGE", "zh"),
    }


def handle_discover(data):
    """发现目标公司。"""
    from opengtm.discover import discover
    industry = data.get("industry", "")
    region = data.get("region", "")
    limit = int(data.get("limit", 10))
    validate = data.get("validate", True)
    if not industry or not region:
        return {"error": "industry 和 region 为必填参数"}, 400
    results = discover(industry=industry, region=region, limit=limit, validate=validate, verbose=False)
    return {"results": results, "count": len(results)}, 200


def handle_research(data):
    """调研单个域名。"""
    from opengtm.research import research
    domain = data.get("domain", "")
    if not domain:
        return {"error": "domain 为必填参数"}, 400
    result = research(
        domain=domain,
        company=data.get("company", "") or domain,
        industry=data.get("industry", ""),
        verbose=False,
    )
    return {"result": result}, 200


def handle_qualify(data):
    """对线索进行ICP评分。"""
    from opengtm.qualify import qualify, qualify_batch
    if "leads" in data:
        leads = data["leads"]
        icp_profile = data.get("icp_profile", "default")
        results = qualify_batch(leads, icp_profile=icp_profile, verbose=False)
        return {"results": results, "count": len(results)}, 200
    else:
        lead = data.get("lead", data)
        icp_profile = data.get("icp_profile", "default")
        result = qualify(lead, icp_profile=icp_profile)
        return {"result": result}, 200


def handle_message(data):
    """生成外展消息。"""
    from opengtm.message import generate_messages
    domain = data.get("domain", "")
    if not domain:
        return {"error": "domain 为必填参数"}, 400
    result = generate_messages(
        domain=domain,
        company=data.get("company", ""),
        contact_name=data.get("contact_name", ""),
        industry=data.get("industry", ""),
        audit=data.get("audit"),
        region=data.get("region", ""),
        contact_title=data.get("contact_title", ""),
        language=data.get("language", "zh"),
    )
    return {"result": result}, 200


def handle_context(data):
    """提取公司上下文。"""
    from opengtm.context import extract_context
    url = data.get("url", "")
    if not url:
        return {"error": "url 为必填参数"}, 400
    user_context = {}
    if data.get("country"):
        user_context["country"] = data["country"]
    if data.get("language"):
        user_context["language"] = data["language"]
    result = extract_context(url=url, user_context=user_context if user_context else None)
    return {"result": result}, 200


def handle_health_check(data):
    """运行AEO健康检查。"""
    from opengtm.analytics import run_health_check
    url = data.get("url", "")
    if not url:
        return {"error": "url 为必填参数"}, 400
    timeout = float(data.get("timeout", 30))
    result = run_health_check(url, timeout=timeout)
    return {"result": result}, 200


def handle_mentions(data):
    """运行AI可见性检测。"""
    from opengtm.analytics import run_mentions
    company = data.get("company", "")
    if not company:
        return {"error": "company 为必填参数"}, 400
    result = run_mentions(
        domain=data.get("domain", ""),
        company_name=company,
        industry=data.get("industry", ""),
    )
    return {"result": result}, 200


def handle_blog(data):
    """生成博客文章。"""
    from opengtm.blog import generate_article
    domain = data.get("domain", "")
    keyword = data.get("keyword", "")
    if not domain or not keyword:
        return {"error": "domain 和 keyword 为必填参数"}, 400
    result = generate_article(
        domain=domain,
        keyword=keyword,
        context=data.get("context"),
        word_count=int(data.get("word_count", 2000)),
        language=data.get("language", "zh"),
        country=data.get("country", "中国"),
        verify_urls=data.get("verify_urls", False),
    )
    return {"result": result}, 200


def handle_keywords(data):
    """研究SEO关键词。"""
    from opengtm.keywords import research_keywords
    domain = data.get("domain", "")
    if not domain:
        return {"error": "domain 为必填参数"}, 400
    results = research_keywords(
        domain=domain,
        context=data.get("context"),
        limit=int(data.get("limit", 30)),
        language=data.get("language", "zh"),
        region=data.get("region", "CN"),
        min_score=int(data.get("min_score", 20)),
        cluster_count=int(data.get("clusters", 5)),
        generate_briefs=data.get("generate_briefs", False),
    )
    return {"results": results, "count": len(results)}, 200


def handle_sitemap(data):
    """爬取站点地图。"""
    from opengtm.sitemap import crawl_sitemap
    url = data.get("url", "")
    if not url:
        return {"error": "url 为必填参数"}, 400
    result = crawl_sitemap(
        url=url,
        validate=data.get("validate", False),
        max_urls=int(data.get("max_urls", 200)),
    )
    return {"result": result}, 200


def handle_sync(data):
    """同步线索到企业微信CRM。"""
    from opengtm.sync import sync_leads, build_sync_payload
    leads = data.get("leads", [])
    dry_run = data.get("dry_run", True)
    if not leads:
        return {"error": "leads 为必填参数"}, 400
    sync_data = [build_sync_payload(lead) for lead in leads]
    result = sync_leads(sync_data, dry_run=dry_run, verbose=False)
    return {"result": result}, 200


def handle_pipeline(data):
    """运行完整GTM流水线。"""
    import time
    from opengtm.discover import discover as _discover
    from opengtm.research import research as _research
    from opengtm.qualify import qualify_batch
    from opengtm.message import generate_messages

    industry = data.get("industry", "")
    region = data.get("region", "")
    limit = int(data.get("limit", 5))
    language = data.get("language", "zh")
    icp_profile = data.get("icp_profile", "default")

    if not industry or not region:
        return {"error": "industry 和 region 为必填参数"}, 400

    prospects = _discover(industry=industry, region=region, limit=limit, verbose=False)
    if not prospects:
        return {"error": "未发现任何公司", "step": "discover"}, 404

    researched = []
    for p in prospects:
        audit = _research(domain=p["domain"], company=p["company"], industry=p["industry"], verbose=False)
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

    qualified = qualify_batch(researched, icp_profile=icp_profile, verbose=False)

    for lead in qualified:
        messages = generate_messages(
            domain=lead["domain"], company=lead["company"],
            contact_name=lead.get("contact_name", ""),
            industry=lead.get("industry", ""),
            audit=lead.get("audit"),
            region=region,
            contact_title=lead.get("contact_title", ""),
            language=language,
        )
        lead["messages"] = messages

    hot = sum(1 for r in qualified if r["qualification"]["tier"] == "hot")
    warm = sum(1 for r in qualified if r["qualification"]["tier"] == "warm")
    cold = sum(1 for r in qualified if r["qualification"]["tier"] == "cold")

    return {
        "results": qualified,
        "summary": {"total": len(qualified), "hot": hot, "warm": warm, "cold": cold}
    }, 200


# =========================================================================
# API路由表
# =========================================================================

API_ROUTES = {
    "/api/discover": handle_discover,
    "/api/research": handle_research,
    "/api/qualify": handle_qualify,
    "/api/message": handle_message,
    "/api/context": handle_context,
    "/api/analytics/health": handle_health_check,
    "/api/analytics/mentions": handle_mentions,
    "/api/blog": handle_blog,
    "/api/keywords": handle_keywords,
    "/api/sitemap": handle_sitemap,
    "/api/sync": handle_sync,
    "/api/pipeline": handle_pipeline,
}


# =========================================================================
# HTTP请求处理器
# =========================================================================

class OpenGTMHandler(SimpleHTTPRequestHandler):
    """自定义HTTP请求处理器，支持API路由和静态文件服务。"""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(PROJECT_ROOT / "static"), **kwargs)

    def do_GET(self):
        parsed = urlparse(self.path)
        path = parsed.path

        # API: 系统状态
        if path == "/api/status":
            try:
                result = handle_status()
                self._send_json(result, 200)
            except Exception as e:
                traceback.print_exc()
                self._send_json({"error": str(e)}, 500)
            return

        # 前端入口：所有非API、非静态文件路径都返回index.html
        if path == "/" or (not path.startswith("/api/") and not os.path.exists(str(PROJECT_ROOT / "static" / path.lstrip("/")))):
            self.path = "/index.html"

        super().do_GET()

    def do_POST(self):
        parsed = urlparse(self.path)
        path = parsed.path

        handler = API_ROUTES.get(path)
        if not handler:
            self._send_json({"error": f"未知API路径: {path}"}, 404)
            return

        try:
            content_length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(content_length) if content_length > 0 else b"{}"
            data = json.loads(body.decode("utf-8"))
        except (json.JSONDecodeError, ValueError) as e:
            self._send_json({"error": f"请求体JSON解析失败: {e}"}, 400)
            return

        try:
            result, status = handler(data)
            self._send_json(result, status)
        except Exception as e:
            traceback.print_exc()
            self._send_json({"error": str(e)}, 500)

    def do_OPTIONS(self):
        """处理CORS预检请求。"""
        self.send_response(200)
        self._set_cors_headers()
        self.end_headers()

    def _send_json(self, data, status=200):
        """发送JSON响应。"""
        body = json.dumps(data, ensure_ascii=False, default=str).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self._set_cors_headers()
        self.end_headers()
        self.wfile.write(body)

    def _set_cors_headers(self):
        """设置CORS头。"""
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")

    def log_message(self, format, *args):
        """自定义日志格式。"""
        msg = format % args
        # 过滤掉静态文件请求的日志
        if "/static/" not in msg and ".js" not in msg and ".css" not in msg and ".ico" not in msg:
            sys.stderr.write(f"[OpenGTM] {msg}\n")


# =========================================================================
# 启动
# =========================================================================

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5200))
    server = HTTPServer(("0.0.0.0", port), OpenGTMHandler)
    print(f"🚀 OpenGTM Web 服务启动于 http://0.0.0.0:{port}")
    print(f"   前端页面: http://0.0.0.0:{port}/")
    print(f"   API状态:  http://0.0.0.0:{port}/api/status")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n⏹️  服务已停止")
        server.server_close()
