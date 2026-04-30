"""
research.py - 线索调研与网站分析。

结合：
- 决策者联系人提取（姓名、职位、邮箱、LinkedIn）
- 7维度网站技术审计
- 结构化输出，供下游评分/消息生成使用

输入：域名（+ 可选的公司名、行业）
输出：包含联系人信息和审计发现的结构化字典
"""

from __future__ import annotations

import json
import time
import urllib.request
from typing import Optional

from .llm import chat_completion_json


RESEARCH_PROMPT = """分析公司"{company}"的网站 {domain}（行业：{industry}）。

任务1 - 查找决策者/主要联系人（适配中国商业场景）：
- 检查"关于我们"、"团队介绍"、"联系我们"等页面
- 查找创始人、CEO、总经理、负责人等决策者的姓名和职位
- 查找公司联系方式（优先级从高到低）：
  1. 商务邮箱（非noreply类）
  2. 联系电话/手机号
  3. 微信公众号名称（如网站上有展示）
  4. 企业微信联系方式
  5. LinkedIn（如有）
- 重要：只返回网站上实际找到的信息，不要猜测或编造

任务2 - 网站技术审计（7个维度）：
1. 标题标签：是否通用（"首页"、"欢迎"）？是否过长（>60字符）？过短？缺失？
2. Meta描述：是否完全缺失？过短（<120字符）？过长（>160字符）？
3. 内容索引：博客/新闻页面是否可访问？是否有noindex问题？内容是否在登录墙后？
4. 损坏元素：死链接（href="#"）、占位符文本、损坏的插件输出？
5. 社交媒体链接：是否存在（微信公众号、微博、抖音、LinkedIn等）或完全缺失？
6. 语言一致性：meta标签与内容之间是否存在语言混用？
7. Schema标记：是否有结构化数据（JSON-LD、微数据）？

重要：仅报告你能从实际网站上验证的发现。要具体。

仅返回有效JSON：
{{
  "contact": {{
    "name": "决策者全名，未找到则为空字符串",
    "title": "职位/头衔，未找到则为空字符串",
    "email": "商务邮箱或null",
    "phone": "联系电话或null",
    "wechat": "微信公众号名称或企业微信号或null",
    "linkedin_url": "linkedin.com/in/ URL或null"
  }},
  "findings": [
    {{
      "type": "title_tag|meta_description|content_indexing|broken_element|social_links|language_mismatch|schema|other",
      "severity": "high|medium|low",
      "detail": "具体发现描述",
      "evidence": "网站上的确切文本/元素"
    }}
  ],
  "title_tag_text": "确切的标题标签文本",
  "meta_description_text": "确切的meta描述或MISSING",
  "site_language": "zh|en|mixed|other",
  "has_blog_or_news": true,
  "has_social_links": true,
  "overall_assessment": "最重要发现的一句话总结"
}}"""


def _verify_linkedin(url: str) -> bool:
    """验证LinkedIn个人主页URL是否真实存在（非幻觉）。"""
    if not url:
        return False
    if "linkedin.com/in/" not in url:
        return False
    if "linkedin.com/company/" in url:
        return False
    full_url = url if url.startswith("http") else f"https://{url}"
    try:
        req = urllib.request.Request(full_url, method="HEAD")
        req.add_header("User-Agent", "Mozilla/5.0 (compatible; opengtm/0.2)")
        resp = urllib.request.urlopen(req, timeout=8)
        return resp.status in (200, 301, 302)
    except Exception:
        return False


def research(
    domain: str,
    company: str = "",
    industry: str = "",
    verify_linkedin: bool = True,
    verbose: bool = True,
) -> dict:
    """
    调研公司：提取决策者联系人 + 运行网站审计。

    Args:
        domain:          公司网站域名（如"example.com"）
        company:         公司名称（提高LLM准确性）
        industry:        行业垂直领域（提高审计相关性）
        verify_linkedin: 是否验证提取的LinkedIn URL是否真实
        verbose:         是否输出进度到标准输出

    Returns:
        包含以下键的字典：contact, findings, title_tag_text, meta_description_text,
        site_language, has_blog_or_news, has_social_links, overall_assessment
    """
    # 规范化域名
    if domain.startswith("www."):
        domain = domain[4:]

    comp = company or domain
    prompt = RESEARCH_PROMPT.format(
        domain=domain,
        company=comp,
        industry=industry or "通用",
    )

    if verbose:
        print(f"[调研] 正在分析 {domain}...", flush=True)

    for attempt in range(3):
        try:
            data = chat_completion_json(prompt, temperature=0.1)

            # 验证联系人信息
            contact = data.get("contact", {})
            linkedin = contact.get("linkedin_url")
            if linkedin:
                if verify_linkedin:
                    if not _verify_linkedin(linkedin):
                        if verbose:
                            print(f"  LinkedIn URL未验证，已丢弃：{linkedin}", flush=True)
                        contact["linkedin_url"] = None
                else:
                    if "linkedin.com/in/" not in linkedin or "linkedin.com/company/" in linkedin:
                        contact["linkedin_url"] = None

            if verbose:
                n = len(data.get("findings", []))
                name = contact.get("name", "未找到")
                phone = contact.get("phone", "")
                wechat = contact.get("wechat", "")
                contact_info = f"联系人：{name}"
                if phone:
                    contact_info += f" | 电话：{phone}"
                if wechat:
                    contact_info += f" | 微信：{wechat}"
                print(f"  {contact_info} | {n}项发现 | {data.get('overall_assessment', '')[:60]}", flush=True)

            return data

        except json.JSONDecodeError as e:
            if verbose:
                print(f"  第{attempt + 1}/3次尝试JSON解析错误：{e}", flush=True)
            if attempt < 2:
                time.sleep(5 * (attempt + 1))
        except Exception as e:
            if verbose:
                print(f"  第{attempt + 1}/3次尝试错误：{e}", flush=True)
            if attempt < 2:
                time.sleep(4 * (attempt + 1))

    # 完全失败时返回空但有效的结构
    return {
        "contact": {"name": "", "title": "", "email": None, "phone": None, "wechat": None, "linkedin_url": None},
        "findings": [],
        "title_tag_text": "",
        "meta_description_text": "MISSING",
        "site_language": "unknown",
        "has_blog_or_news": False,
        "has_social_links": False,
        "overall_assessment": "3次尝试后调研失败",
    }
