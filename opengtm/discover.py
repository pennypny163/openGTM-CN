"""
discover.py - 通过LLM进行线索发现。

输入：行业、地区、数量限制
输出：{company, domain, industry, region} 列表
"""

from __future__ import annotations

import time
import urllib.request
from typing import Optional

from .llm import chat_completion_json


DISCOVER_PROMPT = """查找{region}地区的{limit}家{industry}公司，要求这些公司拥有自己的网站。

要求：
- 仅包含真实的、目前正在运营的公司
- 必须拥有可访问的网站（自有域名，不仅仅是社交媒体主页）
- 包含中小型企业（1-200名员工）
- 不要包含大型跨国公司或超大型企业
- 不要包含目录网站、门户网站或聚合平台
{exclusion_clause}

仅返回JSON数组，不要包含其他文本：
[{{"company": "公司全称", "domain": "example.com"}}]"""


def _validate_url(domain: str, timeout: int = 6) -> bool:
    """通过HEAD请求验证域名是否可达。"""
    url = f"https://{domain}" if not domain.startswith("http") else domain
    req = urllib.request.Request(url, method="HEAD")
    req.add_header("User-Agent", "Mozilla/5.0 (compatible; opengtm/0.2)")
    try:
        resp = urllib.request.urlopen(req, timeout=timeout)
        return resp.status in (200, 301, 302, 403)
    except Exception:
        try:
            url2 = url.replace("https://", "http://")
            req2 = urllib.request.Request(url2, method="HEAD")
            req2.add_header("User-Agent", "Mozilla/5.0 (compatible; opengtm/0.2)")
            resp2 = urllib.request.urlopen(req2, timeout=timeout)
            return resp2.status in (200, 301, 302, 403)
        except Exception:
            return False


def _normalize_domain(domain: str) -> str:
    d = domain.strip().lower()
    if d.startswith("www."):
        d = d[4:]
    return d


def discover(
    industry: str,
    region: str,
    limit: int = 20,
    existing_domains: Optional[set] = None,
    validate: bool = True,
    verbose: bool = True,
) -> list[dict]:
    """
    通过LLM发现目标公司。

    Args:
        industry:  行业垂直领域（如"B2B SaaS"、"IT服务"、"人力资源"）
        region:    城市或地区（如"北京"、"上海"、"深圳"）
        limit:     返回的最大验证公司数量
        existing_domains: 已知域名集合，用于去重
        validate:  是否验证每个域名的可达性
        verbose:   是否输出进度到标准输出

    Returns:
        字典列表：{company, domain, industry, region}
    """
    known = set(existing_domains or [])
    exclusion = (
        f"- 不要包含以下域名（已知）：{', '.join(list(known)[:50])}"
        if known else ""
    )

    prompt = DISCOVER_PROMPT.format(
        limit=limit + 5,
        industry=industry,
        region=region,
        exclusion_clause=exclusion,
    )

    if verbose:
        print(f"[发现] 正在搜索{region}的{industry}公司...", flush=True)

    companies = None
    for attempt in range(3):
        try:
            companies = chat_completion_json(prompt, temperature=0.1)
            if isinstance(companies, dict):
                # LLM 可能返回 {"companies": [...]}，提取列表
                for key in ("companies", "results", "data"):
                    if key in companies and isinstance(companies[key], list):
                        companies = companies[key]
                        break
            if not isinstance(companies, list):
                companies = None
                raise ValueError(f"Expected list, got {type(companies)}")
            break
        except Exception as e:
            if verbose:
                print(f"  第{attempt + 1}/3次尝试失败：{e}", flush=True)
            if attempt < 2:
                time.sleep(5 * (attempt + 1))

    if not companies:
        if verbose:
            print("  错误：3次尝试后发现失败", flush=True)
        return []

    validated = []
    for c in companies:
        domain = _normalize_domain(c.get("domain", ""))
        if not domain:
            continue
        c["domain"] = domain

        if domain in known:
            if verbose:
                print(f"  跳过（重复）：{domain}", flush=True)
            continue

        if validate:
            if _validate_url(domain):
                validated.append({
                    "company": c["company"],
                    "domain": domain,
                    "industry": industry,
                    "region": region,
                })
                known.add(domain)
                if verbose:
                    print(f"  通过：{c['company']}（{domain}）", flush=True)
            else:
                if verbose:
                    print(f"  丢弃（不可达）：{domain}", flush=True)
        else:
            validated.append({
                "company": c["company"],
                "domain": domain,
                "industry": industry,
                "region": region,
            })
            known.add(domain)

        if len(validated) >= limit:
            break

    if verbose and len(validated) < limit:
        print(
            f"  警告：仅找到 {len(validated)}/{limit} 家有效公司",
            flush=True,
        )

    return validated
