"""
llm.py - 统一LLM客户端，使用OpenAI兼容API。

支持任何OpenAI兼容端点（如腾讯混元、one-api等），
通过配置 OPENAI_API_KEY 和 OPENAI_BASE_URL 环境变量即可使用。
"""

from __future__ import annotations

import json
import logging
import os
import re
from typing import Optional

from openai import OpenAI

from . import DEFAULT_MODEL

logger = logging.getLogger(__name__)

# 模型名称映射（腾讯混元系列）
_MODEL_MAP = {
    "hunyuan-lite": "hunyuan-lite",
    "hunyuan-pro": "hunyuan-pro",
    "hunyuan-standard": "hunyuan-standard",
    "hunyuan-turbo": "hunyuan-turbo",
}


def _get_client(api_key: Optional[str] = None) -> OpenAI:
    """创建指向配置的base URL的OpenAI客户端。"""
    key = (
        api_key
        or os.environ.get("OPENAI_API_KEY")
        or os.environ.get("HUNYUAN_API_KEY")
    )
    if not key:
        raise ValueError(
            "未找到API密钥。请设置 OPENAI_API_KEY 或 HUNYUAN_API_KEY 环境变量。"
        )
    base_url = os.environ.get("OPENAI_BASE_URL", "https://api.deepseek.com/v1")
    return OpenAI(api_key=key, base_url=base_url)


def _get_model() -> str:
    """返回要使用的模型名称。"""
    model = os.environ.get("HUNYUAN_MODEL") or os.environ.get("LLM_MODEL") or DEFAULT_MODEL
    return _MODEL_MAP.get(model, model)


def chat_completion(
    prompt: str,
    *,
    system_instruction: Optional[str] = None,
    temperature: float = 0.3,
    max_tokens: int = 8192,
    api_key: Optional[str] = None,
    model: Optional[str] = None,
) -> str:
    """
    发送聊天补全请求并返回文本响应。

    Args:
        prompt: 用户消息内容
        system_instruction: 可选的系统消息
        temperature: 采样温度
        max_tokens: 最大输出token数
        api_key: API密钥覆盖
        model: 模型名称覆盖

    Returns:
        助手的文本响应
    """
    client = _get_client(api_key)
    used_model = model or _get_model()

    messages = []
    if system_instruction:
        messages.append({"role": "system", "content": system_instruction})
    messages.append({"role": "user", "content": prompt})

    response = client.chat.completions.create(
        model=used_model,
        messages=messages,
        temperature=temperature,
        max_tokens=max_tokens,
    )
    return response.choices[0].message.content or ""


def chat_completion_json(
    prompt: str,
    *,
    system_instruction: Optional[str] = None,
    temperature: float = 0.3,
    max_tokens: int = 8192,
    api_key: Optional[str] = None,
    model: Optional[str] = None,
) -> dict:
    """
    发送聊天补全请求并解析JSON响应。

    Args:
        prompt: 用户消息内容（应要求JSON输出）
        system_instruction: 可选的系统消息
        temperature: 采样温度
        max_tokens: 最大输出token数
        api_key: API密钥覆盖
        model: 模型名称覆盖

    Returns:
        从响应中解析的JSON字典
    """
    text = chat_completion(
        prompt,
        system_instruction=system_instruction,
        temperature=temperature,
        max_tokens=max_tokens,
        api_key=api_key,
        model=model,
    )

    # 去除markdown代码块标记
    text = text.strip()
    if text.startswith("```json"):
        text = text[7:]
    if text.startswith("```"):
        text = text[3:]
    if text.endswith("```"):
        text = text[:-3]
    text = text.strip()

    try:
        return json.loads(text)
    except json.JSONDecodeError:
        # 尝试从文本中提取JSON对象或数组
        match = re.search(r"[\{\[].*[\}\]]", text, re.DOTALL)
        if match:
            return json.loads(match.group(0))
        raise ValueError(f"无法从LLM响应中解析JSON: {text[:200]}")
