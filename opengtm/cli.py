"""
cli.py - OpenGTM统一命令行入口。

命令：
  opengtm discover  - 按行业+地区发现公司
  opengtm research  - 调研域名（联系人+网站审计）
  opengtm qualify   - 对线索列表进行ICP匹配度评分
  opengtm message   - 根据审计数据生成外展消息
  opengtm pipeline  - 运行完整端到端流水线
  opengtm outreach  - 查看/管理外展序列队列
  opengtm sync      - 推送线索到企业微信CRM
  opengtm context   - 从URL提取公司上下文
  opengtm analytics - 运行AEO健康检查（29项）+ AI可见性
  opengtm blog      - 使用AI生成博客文章
  opengtm keywords  - 研究SEO关键词（7阶段流水线）
  opengtm sitemap   - 爬取并分类站点地图URL
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

from .outreach import DEFAULT_DAILY_LIMIT


def _load_dotenv():
    """从当前目录加载.env文件（如存在）。"""
    env_file = Path(".env")
    if env_file.exists():
        with open(env_file) as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    key, _, val = line.partition("=")
                    if key.strip() not in os.environ:
                        os.environ[key.strip()] = val.strip().strip('"').strip("'")


def cmd_discover(args):
    from .discover import discover as _discover
    print(f"[discover] {args.industry} | {args.region} | limit {args.limit}", flush=True)
    results = _discover(
        industry=args.industry,
        region=args.region,
        limit=args.limit,
        validate=not args.no_validate,
        verbose=True,
    )
    with open(args.output, "w") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    print(f"\n{len(results)} companies -> {args.output}", flush=True)


def cmd_research(args):
    import time

    from .research import research as _research

    if args.domain:
        result = _research(
            domain=args.domain,
            company=args.company or args.domain,
            industry=args.industry or "",
            verbose=True,
        )
        output = [{"domain": args.domain, "company": args.company or args.domain, "research": result}]
    elif args.input:
        with open(args.input) as f:
            leads = json.load(f)
        output = []
        for i, lead in enumerate(leads):
            print(f"\n[{i+1}/{len(leads)}] {lead.get('company', lead['domain'])}", flush=True)
            result = _research(
                domain=lead["domain"],
                company=lead.get("company", ""),
                industry=lead.get("industry", ""),
                verbose=True,
            )
            output.append({**lead, "audit": result})
            if i < len(leads) - 1:
                time.sleep(3)
    else:
        print("ERROR: provide --domain or --input", file=sys.stderr)
        sys.exit(1)

    with open(args.output, "w") as f:
        json.dump(output, f, indent=2, ensure_ascii=False)
    print(f"\n{len(output)} researched -> {args.output}", flush=True)


def cmd_qualify(args):
    from .qualify import qualify_batch

    with open(args.input) as f:
        leads = json.load(f)

    print(f"[qualify] Scoring {len(leads)} leads (ICP profile: {args.icp_profile})", flush=True)
    results = qualify_batch(leads, icp_profile=args.icp_profile, verbose=True)

    with open(args.output, "w") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)

    hot = sum(1 for r in results if r["qualification"]["tier"] == "hot")
    warm = sum(1 for r in results if r["qualification"]["tier"] == "warm")
    cold = sum(1 for r in results if r["qualification"]["tier"] == "cold")
    print(f"\nResults: {hot} hot, {warm} warm, {cold} cold -> {args.output}", flush=True)


def cmd_message(args):
    from .message import generate_messages

    with open(args.input) as f:
        leads = json.load(f)

    lang = args.language or os.environ.get("DEFAULT_LANGUAGE", "zh")
    region = args.region or ""

    print(f"[message] Generating for {len(leads)} leads (language: {lang})", flush=True)
    results = []
    patterns = {}
    for lead in leads:
        audit = lead.get("audit") or lead.get("research") or {}
        if isinstance(audit, dict) and "research" in audit:
            audit = audit["research"]
        messages = generate_messages(
            domain=lead.get("domain", ""),
            company=lead.get("company", ""),
            contact_name=lead.get("contact_name", ""),
            industry=lead.get("industry", ""),
            audit=audit,
            region=region,
            contact_title=lead.get("contact_title", ""),
            language=lang,
        )
        results.append({**lead, "messages": messages})
        p = messages["pattern"]
        patterns[p] = patterns.get(p, 0) + 1
        print(f"  {lead.get('company', lead.get('domain', '?'))}: Pattern {p}", flush=True)

    with open(args.output, "w") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    print(f"\nPatterns: {dict(sorted(patterns.items()))}", flush=True)
    print(f"{len(results)} messages -> {args.output}", flush=True)


def cmd_pipeline(args):
    """完整端到端流水线：发现 -> 调研 -> 评分 -> 消息 -> 同步。"""
    import time

    from .discover import discover as _discover
    from .message import generate_messages
    from .qualify import qualify_batch
    from .research import research as _research
    from .sync import build_sync_payload, sync_leads

    lang = args.language or os.environ.get("DEFAULT_LANGUAGE", "zh")
    output_path = args.output or f"/tmp/opengtm-pipeline-{args.industry.replace(' ', '-').lower()}.json"

    print(f"{'='*60}", flush=True)
    print(f"PIPELINE: {args.industry} | {args.region} | limit {args.limit}", flush=True)
    print(f"{'='*60}", flush=True)

    # Step 1: Discover
    print("\nSTEP 1: DISCOVER", flush=True)
    prospects = _discover(
        industry=args.industry,
        region=args.region,
        limit=args.limit,
        verbose=True,
    )
    if not prospects:
        print("No companies discovered. Exiting.", flush=True)
        sys.exit(1)

    # Step 2: Research
    print(f"\nSTEP 2: RESEARCH ({len(prospects)} companies)", flush=True)
    researched = []
    for i, p in enumerate(prospects):
        print(f"\n  [{i+1}/{len(prospects)}] {p['company']} ({p['domain']})", flush=True)
        audit = _research(
            domain=p["domain"],
            company=p["company"],
            industry=p["industry"],
            verbose=True,
        )
        contact = audit.get("contact", {})
        researched.append({
            **p,
            "contact_name": contact.get("name", ""),
            "contact_title": contact.get("title", ""),
            "contact_email": contact.get("email"),
            "linkedin_url": contact.get("linkedin_url"),
            "audit": audit,
        })
        if i < len(prospects) - 1:
            time.sleep(3)

    # Step 3: Qualify
    print("\nSTEP 3: QUALIFY", flush=True)
    qualified = qualify_batch(
        researched,
        icp_profile=args.icp_profile,
        verbose=True,
    )

    # Step 4: Generate messages
    print("\nSTEP 4: GENERATE MESSAGES", flush=True)
    for lead in qualified:
        messages = generate_messages(
            domain=lead["domain"],
            company=lead["company"],
            contact_name=lead.get("contact_name", ""),
            industry=lead.get("industry", ""),
            audit=lead.get("audit"),
            region=args.region,
            contact_title=lead.get("contact_title", ""),
            language=lang,
        )
        lead["messages"] = messages
        print(f"  {lead['company']}: Pattern {messages['pattern']}", flush=True)

    # Save results
    with open(output_path, "w") as f:
        json.dump(qualified, f, indent=2, ensure_ascii=False)
    print(f"\nResults -> {output_path}", flush=True)

    # Step 5: Sync (optional)
    if not args.no_sync and os.environ.get("CRM_WEBHOOK_URL"):
        print("\nSTEP 5: SYNC TO CRM", flush=True)
        sync_data = [build_sync_payload(lead) for lead in qualified]
        sync_leads(sync_data, dry_run=args.dry_run, verbose=True)
    elif args.no_sync:
        print("\nSTEP 5: SYNC SKIPPED (--no-sync)", flush=True)
    else:
        print("\nSTEP 5: SYNC SKIPPED (CRM_WEBHOOK_URL not set)", flush=True)

    # Summary
    hot = sum(1 for r in qualified if r["qualification"]["tier"] == "hot")
    warm = sum(1 for r in qualified if r["qualification"]["tier"] == "warm")
    cold = sum(1 for r in qualified if r["qualification"]["tier"] == "cold")
    print(f"\n{'='*60}", flush=True)
    print("PIPELINE COMPLETE", flush=True)
    print(f"  Discovered:  {len(prospects)}", flush=True)
    print(f"  Researched:  {len(researched)}", flush=True)
    print(f"  Qualified:   {hot} hot, {warm} warm, {cold} cold", flush=True)
    print(f"{'='*60}", flush=True)


def cmd_outreach(args):
    from .outreach import OutreachSequence

    if args.action == "status":
        if not args.state_file or not Path(args.state_file).exists():
            print("ERROR: --state-file required and must exist for status", file=sys.stderr)
            sys.exit(1)
        seq = OutreachSequence.load(args.state_file)
        stats = seq.get_stats()
        print(json.dumps(stats, indent=2))

    elif args.action == "queue":
        if not args.state_file or not Path(args.state_file).exists():
            print("ERROR: --state-file required and must exist for queue", file=sys.stderr)
            sys.exit(1)
        seq = OutreachSequence.load(args.state_file)
        seq.print_queue(touch=args.touch)

    elif args.action == "load":
        if not args.input:
            print("ERROR: --input required for load", file=sys.stderr)
            sys.exit(1)
        with open(args.input) as f:
            leads = json.load(f)
        state_path = args.state_file or "/tmp/opengtm-outreach-state.json"
        if Path(state_path).exists():
            seq = OutreachSequence.load(state_path, daily_limit=args.daily_limit)
        else:
            seq = OutreachSequence(daily_limit=args.daily_limit)
        added = seq.add_leads(leads)
        seq.export(state_path)
        print(f"Added {added} new leads to sequence -> {state_path}", flush=True)
        stats = seq.get_stats()
        print(f"Total: {stats['total_leads']} leads | {stats['due_today']} due today", flush=True)


def cmd_sync(args):
    from .sync import build_sync_payload, sync_leads

    with open(args.input) as f:
        leads = json.load(f)

    # Build sync payload
    sync_data = [build_sync_payload(lead) for lead in leads if lead.get("messages", {}).get("pattern") != "SKIP"]
    skipped = len(leads) - len(sync_data)

    if skipped:
        print(f"[sync] Skipping {skipped} SKIP-pattern leads", flush=True)

    sync_leads(sync_data, dry_run=args.dry_run, verbose=True)


def cmd_context(args):
    """从URL提取公司上下文。"""
    from .context import extract_context

    print(f"[context] Extracting context for {args.url}", flush=True)

    user_context = None
    if args.country or args.language:
        user_context = {}
        if args.country:
            user_context["country"] = args.country
        if args.language:
            user_context["language"] = args.language

    result = extract_context(
        url=args.url,
        user_context=user_context,
        fallback_on_error=not args.strict,
    )

    output_path = args.output or "/tmp/opengtm-context.json"
    with open(output_path, "w") as f:
        json.dump(result, f, indent=2, ensure_ascii=False)

    print(f"Company: {result.get('company_name', 'Unknown')}", flush=True)
    print(f"Industry: {result.get('industry', '')}", flush=True)
    print(f"Products: {', '.join(result.get('products', [])[:3])}", flush=True)
    print(f"\nContext -> {output_path}", flush=True)


def cmd_analytics(args):
    """运行AEO健康检查和/或AI可见度检查。"""
    from .analytics import run_health_check, run_mentions

    if args.health_only or not args.company:
        if not args.url:
            print("ERROR: --url required for health check", file=sys.stderr)
            sys.exit(1)
        print(f"[analytics] Health check: {args.url}", flush=True)
        result = run_health_check(args.url)
        output_path = args.output or "/tmp/opengtm-analytics.json"
        with open(output_path, "w") as f:
            json.dump(result, f, indent=2, ensure_ascii=False)
        print(f"Score: {result.get('score', 0)} | Grade: {result.get('grade', '?')}", flush=True)
        print(f"\nResults -> {output_path}", flush=True)

    elif args.mentions_only or not args.url:
        if not args.company:
            print("ERROR: --company required for mentions check", file=sys.stderr)
            sys.exit(1)
        print(f"[analytics] Mentions check: {args.company}", flush=True)
        result = run_mentions(
            domain=args.url or "",
            company_name=args.company,
            industry=args.industry or "",
        )
        output_path = args.output or "/tmp/opengtm-mentions.json"
        with open(output_path, "w") as f:
            json.dump(result, f, indent=2, ensure_ascii=False)
        print(f"Visibility: {result.get('visibility_score', 0):.1f}% | Queries: {result.get('queries_tested', 0)}", flush=True)
        print(f"\nResults -> {output_path}", flush=True)

    else:
        # Full: both stages
        print(f"[analytics] Full analysis: {args.url} | {args.company}", flush=True)
        health = run_health_check(args.url)
        mentions = run_mentions(
            domain=args.url,
            company_name=args.company,
            industry=args.industry or "",
        )
        result = {
            "url": args.url,
            "company": args.company,
            "health": health,
            "mentions": mentions,
        }
        output_path = args.output or "/tmp/opengtm-analytics.json"
        with open(output_path, "w") as f:
            json.dump(result, f, indent=2, ensure_ascii=False)
        print(f"Health: {health.get('score', 0)} ({health.get('grade', '?')}) | Visibility: {mentions.get('visibility_score', 0):.1f}%", flush=True)
        print(f"\nResults -> {output_path}", flush=True)


def cmd_blog(args):
    """使用AI生成博客文章。"""
    from .blog import generate_article

    print(f"[blog] Generating article: '{args.keyword}' for {args.domain}", flush=True)

    context = None
    if args.context:
        with open(args.context) as f:
            context = json.load(f)

    result = generate_article(
        domain=args.domain,
        keyword=args.keyword,
        context=context,
        word_count=args.word_count,
        language=args.language,
        country=args.country,
        verify_urls=args.verify_urls,
    )

    output_path = args.output or "/tmp/opengtm-blog.json"
    with open(output_path, "w") as f:
        json.dump(result, f, indent=2, ensure_ascii=False)

    print(f"Title: {result.get('title', '')}", flush=True)
    print(f"Words: {result.get('word_count', 0)} | Sources: {len(result.get('sources', []))}", flush=True)
    if result.get("is_too_similar"):
        print(f"WARNING: High similarity {result['similarity_score']:.1%} - possible content cannibalization", flush=True)
    print(f"\nArticle -> {output_path}", flush=True)


def cmd_keywords(args):
    """研究SEO关键词。"""
    from .keywords import research_keywords

    print(f"[keywords] Researching keywords for {args.domain} (limit: {args.limit})", flush=True)

    context = None
    if args.context:
        with open(args.context) as f:
            context = json.load(f)

    results = research_keywords(
        domain=args.domain,
        context=context,
        limit=args.limit,
        language=args.language,
        region=args.region,
        min_score=args.min_score,
        cluster_count=args.clusters,
        generate_briefs=not args.no_briefs,
    )

    output_path = args.output or "/tmp/opengtm-keywords.json"
    with open(output_path, "w") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)

    print(f"\n{len(results)} keywords found", flush=True)
    if results:
        top5 = results[:5]
        print("Top 5:", flush=True)
        for kw in top5:
            brief_flag = " [brief]" if kw.get("content_brief") else ""
            print(f"  [{kw.get('score', 0):3d}] {kw['keyword']} ({kw.get('cluster', '?')}){brief_flag}", flush=True)
    print(f"\nKeywords -> {output_path}", flush=True)


def cmd_sitemap(args):
    """爬取并分类站点地图URL。"""
    from .sitemap import crawl_sitemap

    print(f"[sitemap] Crawling {args.url}", flush=True)

    result = crawl_sitemap(
        url=args.url,
        validate=args.validate,
        max_urls=args.max_urls,
    )

    output_path = args.output or "/tmp/opengtm-sitemap.json"
    with open(output_path, "w") as f:
        json.dump(result, f, indent=2, ensure_ascii=False)

    print(f"Total pages: {result['total_pages']}", flush=True)
    print(f"Blog: {len(result['blog_urls'])} | Product: {len(result['product_urls'])} | Service: {len(result['service_urls'])}", flush=True)
    print(f"Docs: {len(result['docs_urls'])} | Resource: {len(result['resource_urls'])} | Other: {len(result['other_urls'])}", flush=True)
    print(f"\nSitemap -> {output_path}", flush=True)


def main():
    _load_dotenv()

    parser = argparse.ArgumentParser(
        prog="opengtm",
        description="AI驱动的GTM自动化：发现线索、调研、ICP评分、生成外展消息。",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例：
  opengtm discover --industry "B2B SaaS" --region "北京" --limit 20
  opengtm research --domain example.com --company "示例公司" --industry "SaaS"
  opengtm qualify --input discovered.json --icp-profile saas
  opengtm message --input qualified.json --language zh
  opengtm pipeline --industry "IT服务" --region "上海" --limit 10
  opengtm outreach load --input qualified.json --state-file seq.json
  opengtm outreach queue --state-file seq.json
  opengtm sync --input generated.json --dry-run
  opengtm context --url https://example.com
  opengtm analytics --url https://example.com --company "示例公司"
  opengtm blog --domain example.com --keyword "SaaS最佳实践"
  opengtm keywords --domain example.com --limit 50
  opengtm sitemap --url https://example.com
        """,
    )
    sub = parser.add_subparsers(dest="command")

    # discover
    p_disc = sub.add_parser("discover", help="通过AI搜索发现目标公司")
    p_disc.add_argument("--industry", "-i", required=True, help="行业（如'B2B SaaS'、'IT服务'）")
    p_disc.add_argument("--region", "-r", required=True, help="城市或地区（如'北京'、'上海'）")
    p_disc.add_argument("--limit", "-n", type=int, default=20, help="最大返回公司数（默认20）")
    p_disc.add_argument("--output", "-o", default="/tmp/opengtm-discovered.json")
    p_disc.add_argument("--no-validate", action="store_true", help="跳过URL可达性检查")

    # research
    p_res = sub.add_parser("research", help="调研域名：提取联系人+运行网站审计")
    p_res.add_argument("--domain", "-d", help="要调研的单个域名")
    p_res.add_argument("--company", "-c", help="公司名称（配合--domain使用）")
    p_res.add_argument("--industry", help="行业（配合--domain使用）")
    p_res.add_argument("--input", help="包含线索的JSON文件 [{domain, company, industry}]")
    p_res.add_argument("--output", "-o", default="/tmp/opengtm-researched.json")

    # qualify
    p_qual = sub.add_parser("qualify", help="对线索进行ICP匹配度评分（0-100）")
    p_qual.add_argument("--input", required=True, help="包含已调研线索的JSON文件")
    p_qual.add_argument("--icp-profile", default="default",
                        choices=["default", "saas", "agency", "professional_services"],
                        help="ICP配置文件（默认：default）")
    p_qual.add_argument("--output", "-o", default="/tmp/opengtm-qualified.json")

    # message
    p_msg = sub.add_parser("message", help="根据审计发现生成外展消息")
    p_msg.add_argument("--input", required=True, help="包含已评分线索的JSON文件")
    p_msg.add_argument("--language", choices=["zh", "en", "de"], help="消息语言（默认：zh）")
    p_msg.add_argument("--region", help="地区（用于同行对比消息）")
    p_msg.add_argument("--output", "-o", default="/tmp/opengtm-messages.json")

    # pipeline
    p_pipe = sub.add_parser("pipeline", help="完整流水线：发现 -> 调研 -> 评分 -> 消息 -> 同步")
    p_pipe.add_argument("--industry", "-i", required=True)
    p_pipe.add_argument("--region", "-r", required=True)
    p_pipe.add_argument("--limit", "-n", type=int, default=10)
    p_pipe.add_argument("--language", choices=["zh", "en", "de"], help="消息语言（默认：zh）")
    p_pipe.add_argument("--icp-profile", default="default",
                        choices=["default", "saas", "agency", "professional_services"])
    p_pipe.add_argument("--output", "-o", help="输出JSON路径")
    p_pipe.add_argument("--no-sync", action="store_true", help="跳过CRM同步步骤")
    p_pipe.add_argument("--dry-run", action="store_true", help="不实际写入CRM")

    # outreach
    p_out = sub.add_parser("outreach", help="管理多触点外展序列")
    p_out.add_argument("action", choices=["load", "queue", "status"],
                       help="load: 添加线索 | queue: 显示今日待处理 | status: 统计信息")
    p_out.add_argument("--input", help="包含线索的JSON文件（用于load操作）")
    p_out.add_argument("--state-file", help="序列状态JSON文件路径")
    p_out.add_argument("--touch", type=int, choices=[1, 2, 3, 4],
                       help="按触点编号筛选队列")
    p_out.add_argument("--daily-limit", type=int, default=DEFAULT_DAILY_LIMIT,
                       help=f"每日最大连接请求数（默认：{DEFAULT_DAILY_LIMIT}）")

    # sync
    p_sync = sub.add_parser("sync", help="通过企业微信Webhook同步线索到CRM")
    p_sync.add_argument("--input", required=True, help="包含已生成线索的JSON文件")
    p_sync.add_argument("--dry-run", action="store_true", help="仅打印不实际发送")

    # context
    p_ctx = sub.add_parser("context", help="从URL提取公司上下文")
    p_ctx.add_argument("--url", "-u", required=True, help="公司网站URL")
    p_ctx.add_argument("--output", "-o", help="输出JSON路径（默认：/tmp/opengtm-context.json）")
    p_ctx.add_argument("--country", help="目标市场国家（如'CN'、'US'）")
    p_ctx.add_argument("--language", help="目标市场语言（如'zh'、'en'）")
    p_ctx.add_argument("--strict", action="store_true", help="API失败时抛出错误而非回退")

    # analytics
    p_anl = sub.add_parser("analytics", help="AEO健康检查（29项）+ AI可见性检测")
    p_anl.add_argument("--url", "-u", help="公司网站URL")
    p_anl.add_argument("--company", "-c", help="公司名称（用于提及检查）")
    p_anl.add_argument("--industry", help="行业（用于提及检查）")
    p_anl.add_argument("--health-only", action="store_true", help="仅运行健康检查")
    p_anl.add_argument("--mentions-only", action="store_true", help="仅运行提及检查")
    p_anl.add_argument("--output", "-o", help="输出JSON路径（默认：/tmp/opengtm-analytics.json）")

    # blog
    p_blog = sub.add_parser("blog", help="使用AI生成博客文章")
    p_blog.add_argument("--domain", "-d", required=True, help="公司网站域名或URL")
    p_blog.add_argument("--keyword", "-k", required=True, help="主要SEO关键词")
    p_blog.add_argument("--context", help="公司上下文JSON文件（来自opengtm context）")
    p_blog.add_argument("--word-count", type=int, default=2000, help="目标字数（默认2000）")
    p_blog.add_argument("--language", default="zh", help="语言代码（默认：zh）")
    p_blog.add_argument("--country", default="中国", help="目标国家/地区")
    p_blog.add_argument("--verify-urls", action="store_true", help="验证文章中所有链接")
    p_blog.add_argument("--output", "-o", help="输出JSON路径（默认：/tmp/opengtm-blog.json）")

    # keywords
    p_kw = sub.add_parser("keywords", help="研究SEO关键词（7阶段AI流水线）")
    p_kw.add_argument("--domain", "-d", required=True, help="公司网站域名或URL")
    p_kw.add_argument("--context", help="公司上下文JSON文件（来自opengtm context）")
    p_kw.add_argument("--limit", "-n", type=int, default=50, help="最大返回关键词数（默认50）")
    p_kw.add_argument("--language", default="zh", help="语言代码（默认：zh）")
    p_kw.add_argument("--region", default="CN", help="目标地区代码（默认：CN）")
    p_kw.add_argument("--min-score", type=int, default=20, help="最低公司匹配度评分0-100（默认20）")
    p_kw.add_argument("--clusters", type=int, default=5, help="语义聚类数量（默认5）")
    p_kw.add_argument("--no-briefs", action="store_true", help="跳过内容简报生成")
    p_kw.add_argument("--output", "-o", help="输出JSON路径（默认：/tmp/opengtm-keywords.json）")

    # sitemap
    p_sm = sub.add_parser("sitemap", help="爬取并分类站点地图URL")
    p_sm.add_argument("--url", "-u", required=True, help="公司网站URL")
    p_sm.add_argument("--validate", action="store_true", help="使用HEAD请求验证每个URL")
    p_sm.add_argument("--max-urls", type=int, default=500, help="最大返回URL数（默认500）")
    p_sm.add_argument("--output", "-o", help="输出JSON路径（默认：/tmp/opengtm-sitemap.json）")

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(0)

    dispatch = {
        "discover": cmd_discover,
        "research": cmd_research,
        "qualify": cmd_qualify,
        "message": cmd_message,
        "pipeline": cmd_pipeline,
        "outreach": cmd_outreach,
        "sync": cmd_sync,
        "context": cmd_context,
        "analytics": cmd_analytics,
        "blog": cmd_blog,
        "keywords": cmd_keywords,
        "sitemap": cmd_sitemap,
    }
    dispatch[args.command](args)


# 允许通过以下方式运行: python -m opengtm
if __name__ == "__main__":
    main()
