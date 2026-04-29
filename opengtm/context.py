"""
context.py - 公司上下文提取。

通过LLM分析公司网站，提取公司名称、行业、产品、服务、目标受众、
竞争对手、品牌调性、痛点、价值主张、用例、内容主题等信息。

函数：
  extract_context(url: str) -> dict
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
from typing import Optional
from urllib.parse import urlparse

from . import DEFAULT_MODEL
from .llm import chat_completion, chat_completion_json

logger = logging.getLogger(__name__)


def _build_prompt(url: str, user_context: Optional[dict] = None) -> str:
    prompt = f"""分析公司网站 {url}，提取公司上下文信息。

搜索该公司的全面信息，返回包含以下字段的JSON对象：

- company_name: 公司官方名称（字符串）
- company_url: 公司网站URL（字符串）
- industry: 主要行业类别（字符串）
- description: 2-3句公司描述（字符串）
- products: 提供的产品（字符串数组）
- services: 提供的服务（字符串数组）
- target_audience: 理想客户画像（字符串）
- target_audiences: 目标受众细分（字符串数组）
- competitors: 主要竞争对手（字符串数组）
- competitor_categories: 竞争解决方案类别（字符串数组）
- primary_region: 主要地理市场（字符串）
- primary_country: 主要国家ISO代码（字符串）
- primary_language: 主要语言ISO代码（字符串）
- tone: 品牌语调（字符串）
- pain_points: 客户痛点（字符串数组）
- value_propositions: 核心价值主张（字符串数组）
- use_cases: 常见用例（字符串数组）
- content_themes: 内容主题和话题（字符串数组）
- gtm_playbook: GTM策略分类（字符串）
- product_type: 产品类型，如SaaS、API、平台等（字符串）

分析目标：{url}"""

    if user_context and (user_context.get("country") or user_context.get("language")):
        target_country = user_context.get("country", "")
        target_language = user_context.get("language", "")
        market_parts = []
        if target_country:
            market_parts.append(f"国家：{target_country}")
        if target_language:
            market_parts.append(f"语言：{target_language}")
        prompt += (
            f"\n\n## 目标市场上下文\n"
            f"用户目标市场：{', '.join(market_parts)}。\n"
            f"重要：请针对该特定市场定制分析：\n"
            f"- 识别与该市场/地区相关的竞争对手\n"
            f"- 从该市场客户的角度描述痛点和价值主张\n"
            f"- 使用目标语言（{target_language}）上下文进行品牌调性分析\n"
            f"- 在响应中将primary_country设为'{target_country}'，primary_language设为'{target_language}'\n"
            f"- 识别与该地理市场相关的目标受众细分\n"
            f"- 内容主题应与该市场的需求和趋势相关"
        )

    MAX_TOTAL_CONTEXT_LENGTH = 10000
    if user_context:
        additional_context = []
        total_length = 0

        if user_context.get("system_instructions"):
            text = user_context["system_instructions"]
            if total_length + len(text) < MAX_TOTAL_CONTEXT_LENGTH:
                additional_context.append(f"\n\n## 用户指令：\n{text}")
                total_length += len(text)

        if user_context.get("client_knowledge_base"):
            text = user_context["client_knowledge_base"]
            if total_length + len(text) < MAX_TOTAL_CONTEXT_LENGTH:
                additional_context.append(f"\n\n## 已知公司信息：\n{text}")
                total_length += len(text)

        if user_context.get("content_instructions"):
            text = user_context["content_instructions"]
            if total_length + len(text) < MAX_TOTAL_CONTEXT_LENGTH:
                additional_context.append(f"\n\n## 内容指南：\n{text}")
                total_length += len(text)

        if additional_context:
            prompt += "\n\n请使用以下用户提供的额外上下文来增强分析："
            prompt += "".join(additional_context)

    return prompt


def _basic_detection(url: str) -> dict:
    """当AI不可用时，从URL提取最小上下文。"""
    if not url.startswith("http"):
        url = f"https://{url}"
    domain = urlparse(url).netloc.replace("www.", "")
    company_name = domain.split(".")[0].replace("-", " ").title()
    return {
        "company_name": company_name,
        "company_url": url,
        "industry": "",
        "description": "",
        "products": [],
        "services": [],
        "target_audience": "",
        "target_audiences": [],
        "competitors": [],
        "competitor_categories": [],
        "primary_region": "",
        "primary_country": "",
        "primary_language": "zh",
        "tone": "专业",
        "pain_points": [],
        "value_propositions": [],
        "use_cases": [],
        "content_themes": [],
        "gtm_playbook": "",
        "product_type": "",
    }


async def _run_extraction(url: str, api_key: Optional[str] = None,
                          user_context: Optional[dict] = None) -> dict:
    """调用LLM并返回解析后的上下文。"""
    prompt = _build_prompt(url, user_context)

    text = chat_completion(prompt, temperature=0.3, api_key=api_key)

    text = text.strip()
    if text.startswith("```json"):
        text = text[7:]
    if text.startswith("```"):
        text = text[3:]
    if text.endswith("```"):
        text = text[:-3]
    text = text.strip()

    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        import re
        match = re.search(r'\{.*\}', text, re.DOTALL)
        if match:
            data = json.loads(match.group(0))
        else:
            raise ValueError(f"无法从LLM响应中解析JSON：{text[:200]}")

    return data


def extract_context(
    url: str,
    api_key: Optional[str] = None,
    user_context: Optional[dict] = None,
    fallback_on_error: bool = True,
) -> dict:
    """
    从URL提取公司上下文信息。

    Args:
        url: 公司网站URL（如"https://example.com"或"example.com"）
        api_key: API密钥。回退到OPENAI_API_KEY环境变量。
        user_context: 可选字典，包含system_instructions, client_knowledge_base,
                      content_instructions, country, language字段。
        fallback_on_error: 如果为True，错误时返回基于域名的基本上下文。

    Returns:
        包含以下键的字典：company_name, company_url, industry, description,
        products, services, target_audience, competitors, tone, pain_points,
        value_propositions, use_cases, content_themes等。

    Raises:
        ValueError: 如果没有API密钥且fallback_on_error=False
        Exception: 如果LLM调用失败且fallback_on_error=False
    """
    if not url.startswith("http"):
        url = f"https://{url}"

    logger.info(f"[上下文] 正在提取 {url} 的上下文")

    resolved_key = (
        api_key
        or os.environ.get("OPENAI_API_KEY")
        or os.environ.get("HUNYUAN_API_KEY")
    )

    if not resolved_key:
        if fallback_on_error:
            logger.warning("[上下文] 无API密钥，使用基本检测")
            return _basic_detection(url)
        raise ValueError("无API密钥。请设置 OPENAI_API_KEY 环境变量。")

    try:
        result = asyncio.run(_run_extraction(url, resolved_key, user_context))
        result.setdefault("company_url", url)
        result.setdefault("products", [])
        result.setdefault("services", [])
        result.setdefault("target_audiences", [])
        result.setdefault("competitors", [])
        result.setdefault("competitor_categories", [])
        result.setdefault("pain_points", [])
        result.setdefault("value_propositions", [])
        result.setdefault("use_cases", [])
        result.setdefault("content_themes", [])
        result.setdefault("tone", "专业")
        logger.info(f"[上下文] 完成：{result.get('company_name', '未知')}")
        return result
    except RuntimeError:
        import concurrent.futures
        with concurrent.futures.ThreadPoolExecutor() as pool:
            future = pool.submit(asyncio.run, _run_extraction(url, resolved_key, user_context))
            try:
                result = future.result(timeout=120)
                result.setdefault("company_url", url)
                result.setdefault("products", [])
                result.setdefault("services", [])
                result.setdefault("pain_points", [])
                result.setdefault("value_propositions", [])
                result.setdefault("use_cases", [])
                result.setdefault("content_themes", [])
                return result
            except Exception as e:
                if fallback_on_error:
                    logger.warning(f"[上下文] 线程中失败：{e}，使用基本检测")
                    return _basic_detection(url)
                raise
    except Exception as e:
        logger.warning(f"[上下文] 提取失败：{e}")
        if fallback_on_error:
            return _basic_detection(url)
        raise
