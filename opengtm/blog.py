"""
blog.py - AI博客文章生成流水线。

基于hyperniche/python-backend/services/blog/（5阶段流水线）移植。

函数：
  generate_article(domain: str, keyword: str, context: dict = None) -> dict

阶段：
  1. 上下文 + 站点地图：提取公司上下文，爬取站点地图获取内部链接
  2. 写作：使用LLM生成文章
  3. 相似度：通过字符分片检测内容蚕食
  4. URL验证：检查文章中所有链接，移除死链
  5. 最终：返回结构化输出

返回：
  {title, meta_title, meta_description, content_html, content_markdown,
   word_count, sources, similarity_score, urls_verified, keyword, domain}
"""

from __future__ import annotations

import asyncio
import logging
import re
from datetime import datetime, timezone
from typing import Optional, Set

from .llm import chat_completion_json

logger = logging.getLogger(__name__)

# 相似度阈值（来源于原始代码）
CHAR_SIMILARITY_THRESHOLD = 0.65
SHINGLE_SIZE = 5

# 文章生成系统指令（回退）
_SYSTEM_INSTRUCTION = '''你是一位专业的内容写作专家。像熟练的人类写手一样写作，而不是AI。

硬性规则：
- 搜索验证所有统计数据/事实 - 绝不编造
- 只使用搜索结果中的确切URL - 绝不猜测URL
- 绝不提及竞争对手名称
- 不使用破折号（—）、不使用"以下是"、"要点："等机械化短语

最新数据：
- 今天是 {current_date}
- 使用当年数据。说"2025年报告"而不是"最近的报告"

语调：
- 精确匹配公司的语调和品牌人格

内容质量：
- 直接切入主题 - 不要用"在当今快速发展的..."等填充语
- 段落长度要有变化（有些长500+字，有些短）
- 包含2个以上：决策框架、具体场景、常见错误、鲜明观点
- 自然地引用统计数据："根据[来源]的报告..."而不是无聊的列表

格式：
- HTML: <p>, <ul>, <li>, <ol>, <strong>
- 鼓励使用列表 - 任何3个以上相关要点都用列表'''

_USER_PROMPT = '''撰写一篇全面、引人入胜的博客文章。

主题：{keyword}

公司上下文：
{company_context}

本地化：
- 语言：{language}
- 国家/地区：{country}

参数：
- 字数：{word_count}
- 章节：4-6个内容章节
- PAA：4个"大家还在问"问题及答案
- FAQ：5-6个常见问题及答案
- 要点：3个关键要点

返回有效的JSON，包含以下字段：
Headline, Teaser, Direct_Answer, Intro, Meta_Title, Meta_Description,
section_01_title, section_01_content, section_02_title, section_02_content,
section_03_title, section_03_content, section_04_title, section_04_content,
section_05_title, section_05_content (可选), section_06_title, section_06_content (可选),
key_takeaway_01, key_takeaway_02, key_takeaway_03,
paa_01_question, paa_01_answer, paa_02_question, paa_02_answer,
paa_03_question, paa_03_answer, paa_04_question, paa_04_answer,
faq_01_question, faq_01_answer, faq_02_question, faq_02_answer,
faq_03_question, faq_03_answer, faq_04_question, faq_04_answer,
faq_05_question, faq_05_answer,
Sources ({"title": "...", "url": "...", "description": "..."} 列表 - 必填, 3-5个来源),
Search_Queries.
'''


# =============================================================================
# 公司上下文格式化器（来源于blog_writer.py）
# =============================================================================

def _format_company_context(context: dict) -> str:
    """将公司上下文字典格式化为LLM提示词可读字符串。"""
    lines = [
        f"公司：{context.get('company_name', '未知')}",
        f"行业：{context.get('industry', '')}",
        f"目标受众：{context.get('target_audience', '')}",
        f"语调：{context.get('tone', '专业')}",
    ]

    description = context.get("description", "")
    if description:
        lines.append(f"简介：{description}")

    products = context.get("products", [])
    if products:
        if isinstance(products, list):
            lines.append(f"产品/服务：{', '.join(str(p) for p in products)}")
        else:
            lines.append(f"产品/服务：{products}")

    pain_points = context.get("pain_points", [])
    if pain_points:
        if isinstance(pain_points, list):
            lines.append(f"客户痛点：{'；'.join(str(p) for p in pain_points)}")
        else:
            lines.append(f"客户痛点：{pain_points}")

    value_props = context.get("value_propositions", [])
    if value_props:
        if isinstance(value_props, list):
            lines.append(f"价值主张：{'；'.join(str(v) for v in value_props)}")
        else:
            lines.append(f"价值主张：{value_props}")

    competitors = context.get("competitors", [])
    if competitors:
        if isinstance(competitors, list):
            lines.append(f"竞争对手（绝不提及）：{', '.join(str(c) for c in competitors)}")
        else:
            lines.append(f"竞争对手（绝不提及）：{competitors}")

    use_cases = context.get("use_cases", [])
    if use_cases:
        if isinstance(use_cases, list):
            lines.append(f"常见用例：{'；'.join(str(u) for u in use_cases)}")
        else:
            lines.append(f"常见用例：{use_cases}")

    return "\n".join(lines)


# =============================================================================
# 相似度检查（来源于similarity_check.py）
# =============================================================================

def _generate_shingles(text: str, size: int = SHINGLE_SIZE) -> Set[str]:
    """从文本生成字符分片（shingles）。"""
    shingles = set()
    normalized = " ".join(text.lower().split())
    for i in range(len(normalized) - size + 1):
        shingles.add(normalized[i:i + size])
    return shingles


def _jaccard_similarity(set1: Set[str], set2: Set[str]) -> float:
    """计算两个集合之间的Jaccard相似度。"""
    if len(set1) == 0 and len(set2) == 0:
        return 1.0
    if len(set1) == 0 or len(set2) == 0:
        return 0.0
    intersection = set1 & set2
    union = set1 | set2
    return len(intersection) / len(union)


# 会话级批量记忆，用于相似度检查
_batch_memory: dict = {}


def _check_similarity(keyword: str, content_text: str) -> float:
    """检查内容与批量记忆的相似度。返回最大相似度分数。"""
    current_shingles = _generate_shingles(content_text)
    max_sim = 0.0

    for other_kw, other_text in _batch_memory.items():
        if other_kw == keyword:
            continue
        other_shingles = _generate_shingles(other_text)
        sim = _jaccard_similarity(current_shingles, other_shingles)
        max_sim = max(max_sim, sim)

    _batch_memory[keyword] = content_text
    return round(max_sim, 3)


# =============================================================================
# URL验证（阶段4逻辑）
# =============================================================================

async def _verify_urls_in_html(html: str) -> tuple[str, int]:
    """
    查找HTML中的所有URL，通过HEAD请求验证。
    移除死链（4xx/5xx）。返回 (清理后的HTML, 已验证数量)。
    """
    try:
        import httpx
    except ImportError:
        return html, 0

    url_pattern = re.compile(r'href=["\']([^"\']+)["\']')
    found_urls = url_pattern.findall(html)

    if not found_urls:
        return html, 0

    # 仅检查http/https链接
    to_check = [u for u in found_urls if u.startswith("http")]
    verified = 0
    dead = set()

    semaphore = asyncio.Semaphore(5)

    async def check(url: str) -> tuple[str, bool]:
        async with semaphore:
            try:
                async with httpx.AsyncClient(
                    timeout=httpx.Timeout(connect=3.0, read=5.0, write=3.0, pool=3.0),
                    follow_redirects=True,
                ) as client:
                    r = await client.head(url)
                    return url, r.status_code < 400
            except Exception:
                return url, False

    results = await asyncio.gather(*[check(u) for u in to_check[:30]])

    for url, is_alive in results:
        if is_alive:
            verified += 1
        else:
            dead.add(url)
            logger.debug(f"[blog] Dead link removed: {url}")

    # 从HTML中移除死链（将href替换为#并添加标记）
    cleaned = html
    for url in dead:
        cleaned = cleaned.replace(f'href="{url}"', 'href="#"')
        cleaned = cleaned.replace(f"href='{url}'", "href='#'")

    return cleaned, verified


# =============================================================================
# LLM文章生成（阶段2逻辑）
# =============================================================================

async def _generate_with_llm(
    keyword: str,
    company_context: dict,
    word_count: int = 2000,
    language: str = "zh",
    country: str = "中国",
    api_key: Optional[str] = None,
) -> dict:
    """调用LLM生成博客文章。返回原始字典。"""
    current_date = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    system_instruction = _SYSTEM_INSTRUCTION.format(current_date=current_date)

    company_str = _format_company_context(company_context)
    prompt = _USER_PROMPT.format(
        keyword=keyword,
        company_context=company_str,
        word_count=word_count,
        language=language,
        country=country,
    )

    return chat_completion_json(
        prompt,
        system_instruction=system_instruction,
        temperature=0.3,
        max_tokens=16384,
        api_key=api_key,
    )


# =============================================================================
# 从文章字典组装HTML
# =============================================================================

def _assemble_html(article: dict) -> str:
    """将文章字典组装为HTML字符串。"""
    parts = []

    headline = article.get("Headline", "")
    if headline:
        parts.append(f"<h1>{headline}</h1>")

    teaser = article.get("Teaser", "")
    if teaser:
        parts.append(f"<p class='teaser'>{teaser}</p>")

    direct_answer = article.get("Direct_Answer", "")
    if direct_answer:
        parts.append(f"<div class='direct-answer'><p>{direct_answer}</p></div>")

    intro = article.get("Intro", "")
    if intro:
        parts.append(f"<div class='intro'>{intro}</div>")

    # 内容章节
    for i in range(1, 10):
        key = str(i).zfill(2)
        title = article.get(f"section_{key}_title", "")
        content = article.get(f"section_{key}_content", "")
        if title or content:
            parts.append("<section>")
            if title:
                parts.append(f"<h2>{title}</h2>")
            if content:
                parts.append(content)
            parts.append("</section>")

    # Key takeaways
    takeaways = []
    for i in range(1, 4):
        t = article.get(f"key_takeaway_{str(i).zfill(2)}", "")
        if t:
            takeaways.append(f"<li>{t}</li>")
    if takeaways:
        parts.append(f"<section class='takeaways'><h2>关键要点</h2><ul>{''.join(takeaways)}</ul></section>")

    # PAA
    paa_items = []
    for i in range(1, 5):
        q = article.get(f"paa_{str(i).zfill(2)}_question", "")
        a = article.get(f"paa_{str(i).zfill(2)}_answer", "")
        if q and a:
            paa_items.append(f"<div class='paa-item'><strong>{q}</strong><p>{a}</p></div>")
    if paa_items:
        parts.append(f"<section class='paa'><h2>大家还在问</h2>{''.join(paa_items)}</section>")

    # FAQ
    faq_items = []
    for i in range(1, 7):
        q = article.get(f"faq_{str(i).zfill(2)}_question", "")
        a = article.get(f"faq_{str(i).zfill(2)}_answer", "")
        if q and a:
            faq_items.append(f"<div class='faq-item'><strong>{q}</strong><p>{a}</p></div>")
    if faq_items:
        parts.append(f"<section class='faq'><h2>常见问题</h2>{''.join(faq_items)}</section>")

    return "\n".join(parts)


def _article_to_text(article: dict) -> str:
    """从文章字典中提取所有文本内容，用于相似度检查。"""
    fields = ["Headline", "Teaser", "Direct_Answer", "Intro"]
    parts = [str(article.get(f, "")) for f in fields if article.get(f)]

    for i in range(1, 10):
        key = str(i).zfill(2)
        if t := article.get(f"section_{key}_title"):
            parts.append(str(t))
        if c := article.get(f"section_{key}_content"):
            parts.append(str(c))

    return " ".join(parts)


# =============================================================================
# 公共API
# =============================================================================

async def _run_pipeline(
    domain: str,
    keyword: str,
    context: Optional[dict],
    word_count: int,
    language: str,
    country: str,
    api_key: Optional[str],
    verify_urls: bool,
) -> dict:
    """完整的异步文章生成流水线。"""

    # 阶段1：获取上下文（如未提供）
    if not context:
        logger.info(f"[blog] Stage 1: extracting context for {domain}")
        from opengtm.context import extract_context
        context = extract_context(domain, api_key=api_key)
    else:
        logger.info("[blog] Stage 1: using provided context")

    # 阶段1b：爬取站点地图获取博客URL参考
    logger.info("[blog] Stage 1b: crawling sitemap")
    try:
        from opengtm.sitemap import crawl_sitemap
        sitemap = crawl_sitemap(domain)
        blog_urls = sitemap.get("blog_urls", [])
        logger.info(f"[blog] Found {len(blog_urls)} blog URLs for internal link reference")
    except Exception as e:
        logger.warning(f"[blog] Sitemap crawl failed: {e}")
        blog_urls = []

    # 阶段2：使用LLM生成文章
    logger.info(f"[blog] Stage 2: generating article for keyword '{keyword}'")
    article = await _generate_with_llm(
        keyword=keyword,
        company_context=context,
        word_count=word_count,
        language=language,
        country=country,
        api_key=api_key,
    )

    # 阶段3：相似度检查
    logger.info("[blog] Stage 3: similarity check")
    article_text = _article_to_text(article)
    similarity_score = _check_similarity(keyword, article_text)
    if similarity_score >= CHAR_SIMILARITY_THRESHOLD:
        logger.warning(f"[blog] High similarity detected: {similarity_score:.1%} (threshold: {CHAR_SIMILARITY_THRESHOLD:.1%})")

    # 阶段4：组装HTML并验证URL
    logger.info("[blog] Stage 4: assembling HTML")
    content_html = _assemble_html(article)
    urls_verified = 0

    if verify_urls:
        logger.info("[blog] Stage 4b: verifying URLs")
        content_html, urls_verified = await _verify_urls_in_html(content_html)

    # 阶段5：构建最终输出
    sources = article.get("Sources", [])
    if not isinstance(sources, list):
        sources = []

    word_count_actual = len(re.sub(r"<[^>]+>", " ", content_html).split())

    result = {
        "keyword": keyword,
        "domain": domain,
        "title": article.get("Headline", ""),
        "meta_title": article.get("Meta_Title", article.get("Headline", "")),
        "meta_description": article.get("Meta_Description", article.get("Teaser", "")),
        "teaser": article.get("Teaser", ""),
        "intro": article.get("Intro", ""),
        "content_html": content_html,
        "word_count": word_count_actual,
        "sources": sources,
        "similarity_score": similarity_score,
        "is_too_similar": similarity_score >= CHAR_SIMILARITY_THRESHOLD,
        "urls_verified": urls_verified,
        "blog_urls_available": len(blog_urls),
        "language": language,
        "country": country,
    }

    logger.info(
        f"[blog] Done: '{result['title'][:60]}' | "
        f"{result['word_count']} words | "
        f"similarity: {similarity_score:.1%}"
    )

    return result


def generate_article(
    domain: str,
    keyword: str,
    context: Optional[dict] = None,
    word_count: int = 2000,
    language: str = "zh",
    country: str = "中国",
    api_key: Optional[str] = None,
    verify_urls: bool = False,
) -> dict:
    """
    使用LLM生成博客文章。

    5阶段流水线：上下文 -> 站点地图 -> 写作 -> 相似度 -> 验证

    Args:
        domain: 公司网站域名或URL（如"example.com"）
        keyword: 主要SEO关键词
        context: 可选的公司上下文字典（来自extract_context）。
                 如未提供，将自动从域名提取上下文。
        word_count: 目标字数（默认2000）
        language: 语言代码（默认"zh"）
        country: 目标国家/地区（默认"中国"）
        api_key: API密钥。回退到OPENAI_API_KEY环境变量。
        verify_urls: 如果为True，验证文章中所有链接（较慢）

    Returns:
        包含以下键的字典：keyword, domain, title, meta_title, meta_description,
        teaser, intro, content_html, word_count, sources, similarity_score,
        is_too_similar, urls_verified, blog_urls_available, language, country
    """
    if not domain.startswith("http"):
        domain = f"https://{domain}"

    logger.info(f"[blog] generate_article: keyword='{keyword}' domain={domain}")

    try:
        return asyncio.run(_run_pipeline(
            domain=domain,
            keyword=keyword,
            context=context,
            word_count=word_count,
            language=language,
            country=country,
            api_key=api_key,
            verify_urls=verify_urls,
        ))
    except RuntimeError:
        import concurrent.futures
        with concurrent.futures.ThreadPoolExecutor() as pool:
            future = pool.submit(
                asyncio.run,
                _run_pipeline(
                    domain=domain,
                    keyword=keyword,
                    context=context,
                    word_count=word_count,
                    language=language,
                    country=country,
                    api_key=api_key,
                    verify_urls=verify_urls,
                ),
            )
            return future.result(timeout=300)
