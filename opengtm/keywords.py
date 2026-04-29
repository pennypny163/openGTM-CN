"""
keywords.py - AI关键词研究流水线。

基于hyperniche/python-backend/services/keywords/（7阶段流水线）移植。

函数：
  research_keywords(domain: str, context: dict = None, limit: int = 50) -> list

阶段：
  1. 公司分析：LLM + 搜索
  2. 深度研究：Reddit + Quora/论坛搜索
  3. AI生成：多样化关键词意图
  4. 评分 + 去重：0-100公司匹配度评分
  5. 聚类：语义聚类
  6. （SERP/搜索量跳过 - 需要付费API密钥）
  7. 内容简报：角度、问题、差距、痛点、字数

返回按评分排序的关键词字典列表（最高分优先）。
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import re
from datetime import datetime
from typing import Dict, List, Optional, Tuple, Any

from . import DEFAULT_MODEL
from .llm import chat_completion_json

logger = logging.getLogger(__name__)


# =============================================================================
# LLM客户端辅助函数（内联，无hyperniche核心依赖）
# =============================================================================

async def _llm_generate(
    prompt: str,
    response_schema: Optional[dict] = None,
    use_web_search: bool = False,
    temperature: float = 0.3,
    api_key: Optional[str] = None,
) -> dict:
    """调用LLM并返回解析后的JSON字典。"""
    return chat_completion_json(
        prompt,
        temperature=temperature,
        api_key=api_key,
    )


# =============================================================================
# 阶段1：公司分析
# =============================================================================

COMPANY_ANALYSIS_SCHEMA = {
    "type": "object",
    "properties": {
        "company_name": {"type": "string"},
        "description": {"type": "string"},
        "industry": {"type": "string"},
        "target_audience": {"type": "array", "items": {"type": "string"}},
        "products": {"type": "array", "items": {"type": "string"}},
        "services": {"type": "array", "items": {"type": "string"}},
        "pain_points": {"type": "array", "items": {"type": "string"}},
        "customer_problems": {"type": "array", "items": {"type": "string"}},
        "use_cases": {"type": "array", "items": {"type": "string"}},
        "value_propositions": {"type": "array", "items": {"type": "string"}},
        "differentiators": {"type": "array", "items": {"type": "string"}},
        "key_features": {"type": "array", "items": {"type": "string"}},
        "solution_keywords": {"type": "array", "items": {"type": "string"}},
        "competitors": {"type": "array", "items": {"type": "string"}},
        "brand_voice": {"type": "string"},
        "product_category": {"type": "string"},
        "primary_region": {"type": "string"},
    },
    "required": ["company_name", "description", "industry", "products"],
}


async def _stage1_company_analysis(
    domain: str,
    context: Optional[dict],
    api_key: Optional[str],
) -> dict:
    """阶段1：通过LLM + 搜索分析公司。"""
    if context and context.get("company_name"):
        logger.info("[keywords] Stage 1: using provided context")
        return context

    logger.info(f"[keywords] Stage 1: analyzing {domain}")
    current_date = datetime.now().strftime("%B %Y")

    prompt = f"""Today's date: {current_date}

Analyze the company at {domain}

Search Google for comprehensive information about this company:
- Search: "{domain} products services"
- Search: "{domain} customers reviews"
- Search: "{domain} vs competitors"

Extract SPECIFIC information:

1. COMPANY BASICS
   - Company name (official name)
   - Description (2-3 sentences about what they do)
   - Industry (be specific: EdTech, FinTech, B2B SaaS, etc.)

2. PRODUCTS & SERVICES
   - What do they SELL? (use actual product/service names)
   - What services do they offer?

3. CUSTOMER INSIGHTS
   - Who are their customers? (include company sizes: startups, SMEs, enterprise)
   - What pain points do customers have?
   - What problems does their solution solve?
   - Real use cases where the product is used

4. VALUE & DIFFERENTIATION
   - Key value propositions
   - What makes them unique vs competitors?
   - Key features and capabilities
   - Terms describing their approach/solution

5. MARKET
   - Who are their main competitors? (3-5 names)
   - Primary geographic region (US, Europe, Global, etc.)

6. BRAND
   - Brand voice (formal/casual, technical/simple)
   - Product category

Be thorough and specific. Use real information from search results.

Return JSON matching this schema:
{json.dumps(COMPANY_ANALYSIS_SCHEMA, indent=2)}"""

    data = await _llm_generate(
        prompt=prompt,
        response_schema=COMPANY_ANALYSIS_SCHEMA,
        use_web_search=True,
        temperature=0.2,
        api_key=api_key,
    )
    return data


# =============================================================================
# 阶段2：深度研究（Reddit + Quora）
# =============================================================================

RESEARCH_KEYWORD_SCHEMA = {
    "type": "object",
    "properties": {
        "keywords": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "keyword": {"type": "string"},
                    "intent": {
                        "type": "string",
                        "enum": ["question", "commercial", "informational", "transactional", "comparison"],
                    },
                    "source": {"type": "string"},
                },
                "required": ["keyword", "intent", "source"],
            },
        }
    },
    "required": ["keywords"],
}


async def _stage2_research(
    company: dict,
    language: str,
    target_count: int,
    api_key: Optional[str],
) -> List[dict]:
    """阶段2：通过搜索Reddit + Quora发现关键词。"""
    industry = company.get("industry", "technology")
    services = company.get("services", [])
    services_str = ", ".join(services[:3]) if services else industry
    current_date = datetime.now().strftime("%B %Y")

    lang_code = (language or "en").strip().lower().split("-")[0][:2]
    lang_note = ""
    if lang_code not in ("", "en"):
        lang_note = f"\nTARGET LANGUAGE: {lang_code}. Return each keyword in that language.\n"

    # Reddit research
    reddit_prompt = f"""Today's date: {current_date}

Search Reddit for discussions about: {industry}
Related services: {services_str}
{lang_note}
Find {target_count // 2} unique long-tail keywords and questions.

Search queries to use:
- site:reddit.com "{industry} help"
- site:reddit.com "{industry} recommendation"
- site:reddit.com "{industry} vs"
- site:reddit.com "{services_str} question"

Extract:
1. Real questions people ask
2. Problem descriptions (pain points)
3. Specific terminology used
4. Comparison phrases
5. "How to" queries

Return JSON with array of keywords, each with keyword, intent, source fields."""

    # Quora/forums research
    quora_prompt = f"""Today's date: {current_date}

Search for questions about: {industry}
Related services: {services_str}
{lang_note}
Find {target_count // 2} unique questions and long-tail keywords.

Search queries:
- site:quora.com "{industry}"
- "{industry}" people also ask
- "{services_str}" how to
- "{industry}" forum discussion

Extract:
1. Actual questions people ask
2. "How to" queries
3. "Best way to" phrases
4. Comparison questions
5. Specific pain points

Return JSON with array of keywords, each with keyword, intent, source fields."""

    tasks = [
        _llm_generate(reddit_prompt, use_web_search=True, temperature=0.2, api_key=api_key),
        _llm_generate(quora_prompt, use_web_search=True, temperature=0.2, api_key=api_key),
    ]

    results = await asyncio.gather(*tasks, return_exceptions=True)

    all_keywords = []
    for result in results:
        if isinstance(result, Exception):
            logger.warning(f"[keywords] Stage 2 research task failed: {result}")
            continue
        for kw in result.get("keywords", []):
            if kw.get("keyword"):
                all_keywords.append({
                    "keyword": kw["keyword"],
                    "intent": kw.get("intent", "informational"),
                    "source": kw.get("source", "research"),
                    "is_question": "?" in kw["keyword"] or kw.get("intent") == "question",
                    "score": 0,
                })

    return all_keywords


# =============================================================================
# 阶段3：AI关键词生成
# =============================================================================

KEYWORD_SCHEMA = {
    "type": "object",
    "properties": {
        "keywords": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "keyword": {"type": "string"},
                    "intent": {
                        "type": "string",
                        "enum": ["transactional", "commercial", "informational", "question", "comparison"],
                    },
                    "is_question": {"type": "boolean"},
                },
                "required": ["keyword", "intent"],
            },
        }
    },
    "required": ["keywords"],
}


async def _stage3_ai_keywords(
    company: dict,
    existing_count: int,
    target_count: int,
    language: str,
    api_key: Optional[str],
) -> List[dict]:
    """阶段3：使用AI生成关键词。"""
    ai_target = max(target_count - existing_count, target_count // 3)
    if ai_target <= 0:
        return []

    lang_code = (language or "en").strip().lower().split("-")[0][:2]
    lang_instruction = (
        "CRITICAL: Generate EVERY keyword in the target language. "
        "All keyword text MUST be written in the language specified below. "
        "Do not mix English with the target language. "
    )
    if lang_code == "hi":
        lang_instruction += "TARGET LANGUAGE: Hindi. Write every keyword in Hindi using Devanagari script. "
    elif lang_code == "bn":
        lang_instruction += "TARGET LANGUAGE: Bengali. Write every keyword in Bengali/Bangla script. "
    elif lang_code != "en":
        lang_instruction += f"TARGET LANGUAGE: {lang_code}. Write every keyword in that language only. "

    products_str = ", ".join(company.get("products", [])[:5]) or "N/A"
    services_str = ", ".join(company.get("services", [])[:5]) or "N/A"
    pain_points_str = ", ".join(company.get("pain_points", [])[:5]) or "N/A"
    differentiators_str = ", ".join(company.get("differentiators", [])[:3]) or "N/A"

    prompt = f"""Generate {ai_target} SEO keywords for this company:

COMPANY: {company.get('company_name', 'Unknown')}
INDUSTRY: {company.get('industry', 'N/A')}
PRODUCTS: {products_str}
SERVICES: {services_str}
PAIN POINTS: {pain_points_str}
DIFFERENTIATORS: {differentiators_str}
LANGUAGE: {language}

{lang_instruction}

REQUIREMENTS:
1. Generate DIVERSE keywords across these intents:
   - transactional (buy, pricing, demo)
   - commercial (comparison, alternatives, vs)
   - informational (how to, what is, guide)
   - question (actual questions users ask)

2. Include:
   - Long-tail keywords (3-5 words)
   - Question keywords ("how to...", "what is...")
   - Comparison keywords ("X vs Y", "alternatives to")
   - Product-specific keywords
   - Problem-solving keywords

3. AVOID:
   - Generic industry terms
   - Single-word keywords
   - Duplicate variations
   - Writing keyword text in English when LANGUAGE is not en

Return JSON with array of keywords, each with keyword, intent, is_question fields."""

    try:
        data = await _llm_generate(
            prompt=prompt,
            response_schema=KEYWORD_SCHEMA,
            use_web_search=False,
            temperature=0.7,
            api_key=api_key,
        )
        return [
            {
                "keyword": kw.get("keyword", ""),
                "intent": kw.get("intent", "informational"),
                "source": "ai_generated",
                "is_question": kw.get("is_question", False),
                "score": 0,
            }
            for kw in data.get("keywords", [])
            if kw.get("keyword")
        ]
    except Exception as e:
        logger.warning(f"[keywords] Stage 3 AI generation failed: {e}")
        return []


# =============================================================================
# 阶段4：评分 + 去重
# =============================================================================

SCORING_SCHEMA = {
    "type": "object",
    "properties": {
        "keywords": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "keyword": {"type": "string"},
                    "score": {"type": "integer", "minimum": 0, "maximum": 100},
                },
                "required": ["keyword", "score"],
            },
        }
    },
    "required": ["keywords"],
}


def _deduplicate(keywords: List[dict]) -> Tuple[List[dict], int]:
    """使用精确匹配 + 词元签名进行快速去重。"""
    seen_exact: set = set()
    seen_tokens: set = set()
    unique = []
    dup_count = 0

    for kw in keywords:
        text = kw.get("keyword", "").lower().strip()
        if not text:
            continue
        if text in seen_exact:
            dup_count += 1
            continue
        tokens = tuple(sorted(text.split()))
        if tokens in seen_tokens:
            dup_count += 1
            continue
        seen_exact.add(text)
        seen_tokens.add(tokens)
        unique.append(kw)

    return unique, dup_count


async def _stage4_score(
    keywords: List[dict],
    company: dict,
    min_score: int = 20,
    api_key: Optional[str] = None,
) -> List[dict]:
    """阶段4：对关键词进行公司匹配度评分并去重。"""
    keywords, dup_count = _deduplicate(keywords)
    logger.info(f"[keywords] Stage 4: {len(keywords)} after dedup ({dup_count} removed)")

    if not keywords:
        return []

    products = ", ".join(company.get("products", [])[:5]) or "N/A"
    services = ", ".join(company.get("services", [])[:5]) or "N/A"
    pain_points = ", ".join(company.get("pain_points", [])[:3]) or "N/A"

    batch_size = 50
    scored = []

    for i in range(0, len(keywords), batch_size):
        batch = keywords[i:i + batch_size]
        keyword_list = [kw.get("keyword", "") for kw in batch]

        prompt = f"""Score these keywords for company-fit (0-100):

COMPANY: {company.get('company_name', 'Unknown')}
INDUSTRY: {company.get('industry', 'N/A')}
PRODUCTS: {products}
SERVICES: {services}
PAIN POINTS: {pain_points}

SCORING CRITERIA:
- 80-100: Directly mentions company products/services/solutions
- 60-79: Highly relevant to company's pain points and value props
- 40-59: Generally relevant to industry/niche
- 20-39: Loosely related, might attract some relevant traffic
- 0-19: Not relevant, too generic, or wrong audience

KEYWORDS TO SCORE:
{json.dumps(keyword_list, indent=2)}

Return JSON with array of {{keyword, score}} for each."""

        try:
            data = await _llm_generate(
                prompt=prompt,
                response_schema=SCORING_SCHEMA,
                use_web_search=False,
                temperature=0.2,
                api_key=api_key,
            )
            scores = {s["keyword"]: s["score"] for s in data.get("keywords", [])}
            for kw in batch:
                kw["score"] = scores.get(kw.get("keyword", ""), 50)
                scored.append(kw)
        except Exception as e:
            logger.warning(f"[keywords] Scoring batch failed: {e}")
            for kw in batch:
                kw["score"] = 50
                scored.append(kw)

    # 按最低分过滤
    filtered = [kw for kw in scored if kw.get("score", 0) >= min_score]
    logger.info(f"[keywords] Stage 4: {len(filtered)} after score filter (>= {min_score})")
    return filtered


# =============================================================================
# 阶段5：聚类
# =============================================================================

CLUSTERING_SCHEMA = {
    "type": "object",
    "properties": {
        "clusters": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "name": {"type": "string"},
                    "keywords": {"type": "array", "items": {"type": "string"}},
                },
                "required": ["name", "keywords"],
            },
        }
    },
    "required": ["clusters"],
}


async def _stage5_cluster(
    keywords: List[dict],
    company: dict,
    cluster_count: int = 5,
    api_key: Optional[str] = None,
) -> List[dict]:
    """阶段5：使用LLM进行语义聚类。"""
    if not keywords:
        return keywords

    keyword_list = [kw["keyword"] for kw in keywords]

    prompt = f"""Group these keywords into {cluster_count} semantic clusters for {company.get('company_name', 'the company')}:

INDUSTRY: {company.get('industry', 'N/A')}

KEYWORDS:
{json.dumps(keyword_list, indent=2)}

CLUSTERING RULES:
1. Create exactly {cluster_count} clusters
2. Each cluster should have a short, descriptive name (2-4 words)
3. Group by semantic similarity and topic
4. Every keyword must belong to exactly one cluster
5. Balance cluster sizes (avoid putting everything in one cluster)

Example cluster names:
- "Pricing & Plans"
- "How-To Guides"
- "Competitor Comparisons"
- "Product Features"
- "Industry Solutions"

Return JSON with clusters array, each containing name and keywords array."""

    try:
        data = await _llm_generate(
            prompt=prompt,
            response_schema=CLUSTERING_SCHEMA,
            use_web_search=False,
            temperature=0.2,
            api_key=api_key,
        )

        # 构建关键词到聚类的映射
        kw_to_cluster: Dict[str, str] = {}
        for cluster in data.get("clusters", []):
            cluster_name = cluster.get("name", "Uncategorized")
            for kw in cluster.get("keywords", []):
                kw_to_cluster[kw.lower()] = cluster_name

        # 应用聚类
        for kw in keywords:
            kw["cluster"] = kw_to_cluster.get(kw.get("keyword", "").lower(), "Uncategorized")

        logger.info(f"[keywords] Stage 5: clustered into {len(data.get('clusters', []))} groups")

    except Exception as e:
        logger.warning(f"[keywords] Stage 5 clustering failed: {e}")
        for kw in keywords:
            kw["cluster"] = "Uncategorized"

    return keywords


# =============================================================================
# 阶段7：内容简报
# =============================================================================

CONTENT_BRIEF_SCHEMA = {
    "type": "object",
    "properties": {
        "content_angle": {"type": "string"},
        "target_questions": {"type": "array", "items": {"type": "string"}},
        "content_gap": {"type": "string"},
        "audience_pain_point": {"type": "string"},
        "recommended_word_count": {"type": "integer"},
    },
    "required": ["content_angle", "target_questions", "content_gap", "audience_pain_point", "recommended_word_count"],
}


async def _generate_brief(
    keyword: dict,
    company_name: str,
    industry: str,
    language: str,
    api_key: Optional[str],
) -> Optional[dict]:
    """为单个关键词生成内容简报。"""
    prompt = f"""Generate a content brief for the keyword: "{keyword['keyword']}"

Company: {company_name}
Industry: {industry or "General"}
Search Intent: {keyword.get('intent', 'informational')}
Is Question: {"Yes" if keyword.get('is_question') else "No"}

Generate a content brief with these fields:
1. content_angle: A unique angle or perspective to differentiate from competitors (1-2 sentences)
2. target_questions: 3-5 key questions the content should answer
3. content_gap: What's missing from existing content that we can fill (1 sentence)
4. audience_pain_point: The main pain point to address (1 sentence)
5. recommended_word_count: Recommended word count based on topic complexity (number between 800-3000)"""

    try:
        data = await _llm_generate(
            prompt=prompt,
            response_schema=CONTENT_BRIEF_SCHEMA,
            use_web_search=False,
            temperature=0.7,
            api_key=api_key,
        )
        return {
            "content_angle": str(data.get("content_angle", ""))[:500],
            "target_questions": [str(q)[:200] for q in data.get("target_questions", [])[:5]],
            "content_gap": str(data.get("content_gap", ""))[:300],
            "audience_pain_point": str(data.get("audience_pain_point", ""))[:300],
            "recommended_word_count": min(max(int(data.get("recommended_word_count", 1500)), 500), 5000),
        }
    except Exception as e:
        logger.warning(f"[keywords] Brief generation failed for '{keyword['keyword']}': {e}")
        return None


async def _stage7_briefs(
    keywords: List[dict],
    company: dict,
    language: str,
    brief_sample_size: int,
    api_key: Optional[str],
) -> List[dict]:
    """阶段7：为顶级关键词生成内容简报。"""
    sorted_kws = sorted(keywords, key=lambda k: k.get("score", 0), reverse=True)
    sample = sorted_kws[:brief_sample_size]

    company_name = company.get("company_name", "Unknown")
    industry = company.get("industry", "")

    # 每批处理5个（来源于原始代码）
    batch_size = 5
    briefs_generated = 0

    for i in range(0, len(sample), batch_size):
        batch = sample[i:i + batch_size]
        tasks = [
            _generate_brief(kw, company_name, industry, language, api_key)
            for kw in batch
        ]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        for kw, result in zip(batch, results):
            if isinstance(result, dict):
                kw["content_brief"] = result
                briefs_generated += 1
            else:
                kw["content_brief"] = None

        if i + batch_size < len(sample):
            await asyncio.sleep(0.3)

    logger.info(f"[keywords] Stage 7: generated {briefs_generated} content briefs")
    return keywords


# =============================================================================
# 公共API
# =============================================================================

async def _run_pipeline(
    domain: str,
    context: Optional[dict],
    limit: int,
    language: str,
    region: str,
    min_score: int,
    cluster_count: int,
    brief_sample_size: int,
    generate_briefs: bool,
    api_key: Optional[str],
) -> List[dict]:
    """完整的异步关键词研究流水线。"""

    # 阶段1：公司分析
    company = await _stage1_company_analysis(domain, context, api_key)
    logger.info(f"[keywords] Company: {company.get('company_name', 'Unknown')}")

    # 阶段2：深度研究（Reddit + Quora）
    logger.info("[keywords] Stage 2: deep research")
    research_keywords = await _stage2_research(company, language, limit, api_key)
    logger.info(f"[keywords] Stage 2: {len(research_keywords)} research keywords")

    # 阶段3：AI关键词生成
    logger.info("[keywords] Stage 3: AI generation")
    ai_keywords = await _stage3_ai_keywords(
        company, len(research_keywords), limit, language, api_key
    )
    logger.info(f"[keywords] Stage 3: {len(ai_keywords)} AI keywords")

    # 合并
    all_keywords = research_keywords + ai_keywords

    # 阶段4：评分 + 去重
    logger.info("[keywords] Stage 4: scoring + deduplication")
    scored = await _stage4_score(all_keywords, company, min_score=min_score, api_key=api_key)

    # 按评分排序，取前N个
    scored.sort(key=lambda k: k.get("score", 0), reverse=True)
    scored = scored[:limit]

    # 阶段5：聚类
    logger.info("[keywords] Stage 5: clustering")
    clustered = await _stage5_cluster(scored, company, cluster_count=cluster_count, api_key=api_key)

    # 阶段6：SERP/搜索量跳过（需要付费Serper/DataForSEO API密钥）
    # 阶段7：内容简报（仅前N个）
    if generate_briefs and clustered:
        logger.info("[keywords] Stage 7: content briefs")
        clustered = await _stage7_briefs(clustered, company, language, brief_sample_size, api_key)

    logger.info(f"[keywords] Pipeline complete: {len(clustered)} keywords")
    return clustered


def research_keywords(
    domain: str,
    context: Optional[dict] = None,
    limit: int = 50,
    language: str = "zh",
    region: str = "CN",
    min_score: int = 20,
    cluster_count: int = 5,
    brief_sample_size: int = 10,
    generate_briefs: bool = True,
    api_key: Optional[str] = None,
) -> List[dict]:
    """
    使用AI研究公司的SEO关键词。

    7阶段流水线：分析 -> 研究 -> 生成 -> 评分 -> 聚类 -> 简报

    Args:
        domain: 公司网站域名或URL（如"example.com"）
        context: 可选的公司上下文字典（来自extract_context）。
                 如未提供，将通过LLM自动提取。
        limit: 返回的最大关键词数量（默认50）
        language: 语言代码（默认"zh"）
        region: 目标地区代码（默认"CN"）
        min_score: 最低公司匹配度评分0-100（默认20）
        cluster_count: 语义聚类数量（默认5）
        brief_sample_size: 生成内容简报的顶级关键词数量（默认10）
        generate_briefs: 如果为True，为顶级关键词生成内容简报
        api_key: API密钥。回退到OPENAI_API_KEY环境变量。

    Returns:
        按评分排序的关键词字典列表（最高分优先）。每个字典包含：
        keyword, intent, source, is_question, score, cluster, content_brief (可选)
    """
    if not domain.startswith("http"):
        domain = f"https://{domain}"

    logger.info(f"[keywords] research_keywords: domain={domain} limit={limit}")

    try:
        return asyncio.run(_run_pipeline(
            domain=domain,
            context=context,
            limit=limit,
            language=language,
            region=region,
            min_score=min_score,
            cluster_count=cluster_count,
            brief_sample_size=brief_sample_size,
            generate_briefs=generate_briefs,
            api_key=api_key,
        ))
    except RuntimeError:
        import concurrent.futures
        with concurrent.futures.ThreadPoolExecutor() as pool:
            future = pool.submit(
                asyncio.run,
                _run_pipeline(
                    domain=domain,
                    context=context,
                    limit=limit,
                    language=language,
                    region=region,
                    min_score=min_score,
                    cluster_count=cluster_count,
                    brief_sample_size=brief_sample_size,
                    generate_briefs=generate_briefs,
                    api_key=api_key,
                ),
            )
            return future.result(timeout=600)
    except Exception as e:
        logger.error(f"[keywords] Pipeline failed: {e}")
        raise
