"""
qualify.py - ICP评分与线索资质评估。

对线索进行0-100分的ICP匹配度评分。
返回等级（热门/温暖/冷淡）和推荐操作。

评分维度：
  - 公司规模信号       (0-20分)
  - 行业匹配度         (0-25分)
  - 数字化成熟度       (0-15分)
  - 痛点信号           (0-20分)
  - 营收/预算信号      (0-10分)
  - 联系人质量         (0-10分)
"""

from __future__ import annotations

from typing import Optional


# 行业匹配度分层。可通过icp_profile字典添加或覆盖。
INDUSTRY_TIERS: dict[str, int] = {
    # 第1层：强ICP匹配 (25分) - 高数字化意识，B2B买家
    "B2B SaaS": 25,
    "SaaS": 25,
    "IT服务": 25,
    "IT Services": 25,
    "网络安全": 25,
    "Cybersecurity": 25,
    "系统集成": 25,
    "云计算": 25,
    "人工智能": 25,
    # 第2层：良好ICP匹配 (20分) - 有数字化预算，理解价值
    "人力资源": 20,
    "Recruiting": 20,
    "市场营销": 20,
    "Marketing & Advertising": 20,
    "设计": 20,
    "Design": 20,
    "管理咨询": 20,
    "Management Consulting": 20,
    # 第3层：中等ICP匹配 (15分) - 可转化，需要更多教育
    "电子商务": 15,
    "E-Commerce": 15,
    "金融服务": 15,
    "Financial Services": 15,
    "会计": 15,
    "Accounting": 15,
    "法律服务": 15,
    "Legal Services": 15,
    # 第4层：较低ICP匹配 (8分) - 可能但销售周期更长
    "房地产": 8,
    "Real Estate": 8,
    "医疗": 8,
    "Medical": 8,
    "工业制造": 8,
    "Industrial": 8,
    "物流": 8,
    "建筑设计": 8,
    # 第5层：弱ICP匹配 (3分) - 很少是好的匹配
    "餐饮": 3,
    "健身": 3,
    "手工业": 3,
    "教育": 3,
}

# ICP配置文件：命名预设配置
ICP_PROFILES: dict[str, dict] = {
    "saas": {
        "name": "B2B SaaS / 科技",
        "top_industries": ["B2B SaaS", "SaaS", "IT服务", "IT Services", "网络安全", "Cybersecurity", "云计算", "人工智能"],
        "ideal_size_range": (10, 200),
        "require_blog": False,
        "pain_weight": 1.2,
    },
    "agency": {
        "name": "市场营销 / 设计机构",
        "top_industries": ["市场营销", "Marketing & Advertising", "设计", "Design", "IT服务", "IT Services"],
        "ideal_size_range": (5, 100),
        "require_blog": True,
        "pain_weight": 1.1,
    },
    "professional_services": {
        "name": "专业服务（法律、金融、咨询）",
        "top_industries": ["法律服务", "Legal Services", "金融服务", "Financial Services", "会计", "Accounting", "管理咨询", "Management Consulting"],
        "ideal_size_range": (5, 150),
        "require_blog": False,
        "pain_weight": 1.0,
    },
    "default": {
        "name": "通用B2B",
        "top_industries": list(INDUSTRY_TIERS.keys()),
        "ideal_size_range": (5, 200),
        "require_blog": False,
        "pain_weight": 1.0,
    },
}


def _score_company_size(research_data: dict) -> tuple[int, list[str]]:
    """
    评分0-20，基于推断的公司规模。
    信号：团队页面存在、发现数量（网站复杂度代理）、博客/新闻存在、社交链接多样性。
    """
    score = 0
    reasons = []

    findings = research_data.get("findings", [])
    has_blog = research_data.get("has_blog_or_news", False)
    has_social = research_data.get("has_social_links", False)
    title_text = research_data.get("title_tag_text", "")

    if has_blog:
        score += 6
        reasons.append("有博客/新闻（具备内容生产能力）")
    if has_social:
        score += 4
        reasons.append("有社交媒体存在")

    n_findings = len(findings)
    if n_findings >= 4:
        score += 6
        reasons.append(f"复杂网站（{n_findings}项审计信号 = 较大组织）")
    elif n_findings >= 2:
        score += 3
        reasons.append(f"中等网站复杂度（{n_findings}项审计信号）")
    else:
        score += 1

    if title_text and len(title_text) > 10:
        score += 4
        reasons.append("有具体的标题标签（有定位的公司）")

    return min(score, 20), reasons


def _score_industry_fit(industry: str, icp_profile: dict) -> tuple[int, list[str]]:
    """评分0-25，基于行业层级和ICP配置文件匹配。"""
    if not industry:
        return 5, ["无行业数据（匹配度未知）"]

    base = INDUSTRY_TIERS.get(industry, 5)

    top_industries = icp_profile.get("top_industries", [])
    if industry in top_industries:
        return 25, [f"{industry}是该配置文件的顶级ICP行业"]

    if base >= 20:
        return base, [f"{industry}是强ICP行业（第1层）"]
    elif base >= 15:
        return base, [f"{industry}是良好ICP行业（第2层）"]
    elif base >= 8:
        return base, [f"{industry}是中等ICP匹配（第3层）"]
    else:
        return base, [f"{industry}是弱ICP匹配（第4-5层）"]


def _score_digital_maturity(research_data: dict) -> tuple[int, list[str]]:
    """
    评分0-15，基于数字化成熟度。
    成熟度越高 = 越理解数字化存在的价值。
    """
    score = 0
    reasons = []

    has_blog = research_data.get("has_blog_or_news", False)
    has_social = research_data.get("has_social_links", False)
    findings = research_data.get("findings", [])
    has_schema = any(f.get("type") == "schema" for f in findings)

    if has_blog:
        score += 5
        reasons.append("有内容/博客（投资数字化存在）")
    if has_social:
        score += 4
        reasons.append("活跃于社交媒体（数字化优先思维）")
    if has_schema:
        score += 3
        reasons.append("使用Schema标记（技术成熟度高）")

    lang = research_data.get("site_language", "")
    if lang in ("zh", "en", "de"):
        score += 3
        reasons.append("网站语言一致（实现规范）")
    elif lang == "mixed":
        reasons.append("网站语言混用（数字化不成熟信号）")

    return min(score, 15), reasons


def _score_pain_signals(research_data: dict, pain_weight: float = 1.0) -> tuple[int, list[str]]:
    """
    评分0-20，基于痛点信号强度。
    痛点越多 = 机会越好（他们需要这项工作）。
    """
    findings = research_data.get("findings", [])
    if not findings:
        return 5, ["无审计发现（网站干净或审计失败）"]

    score = 0
    reasons = []

    sev_points = {"high": 5, "medium": 3, "low": 1}
    seen_types: set[str] = set()

    for f in findings:
        ftype = f.get("type", "other")
        severity = f.get("severity", "low")
        pts = sev_points.get(severity, 1)

        if ftype not in seen_types:
            score += pts
            seen_types.add(ftype)
            detail = f.get("detail", "")[:60]
            reasons.append(f"{severity.upper()} {ftype}: {detail}")

    score = min(int(score * pain_weight), 20)
    return score, reasons


def _score_revenue_signals(research_data: dict) -> tuple[int, list[str]]:
    """
    评分0-10，基于营收/预算代理信号。
    有定价页、案例研究、客户评价 = 有销售和预算。
    """
    score = 0
    reasons = []

    findings = research_data.get("findings", [])

    if research_data.get("has_blog_or_news", False):
        score += 3
        reasons.append("有内容/博客（有营销预算）")

    if research_data.get("has_social_links", False):
        score += 3
        reasons.append("活跃社交存在（有营销投入）")

    high_sev = [f for f in findings if f.get("severity") == "high"]
    if len(high_sev) >= 2:
        score += 4
        reasons.append(f"{len(high_sev)}个高严重度问题（网站有投入但需要改进）")
    elif len(high_sev) == 1:
        score += 2

    return min(score, 10), reasons


def _score_contact_quality(research_data: dict) -> tuple[int, list[str]]:
    """评分0-10，基于决策者的可触达程度。"""
    contact = research_data.get("contact", {})
    score = 0
    reasons = []

    name = contact.get("name", "")
    email = contact.get("email")
    linkedin = contact.get("linkedin_url")

    if name:
        score += 3
        reasons.append(f"找到联系人姓名：{name}")
    if linkedin:
        score += 5
        reasons.append("找到LinkedIn主页（可直接触达）")
    if email:
        score += 2
        reasons.append("找到邮箱（可邮件触达）")

    if not name and not email and not linkedin:
        reasons.append("未找到联系人信息（仅可冷触达）")

    return min(score, 10), reasons


def qualify(
    lead: dict,
    icp_profile: str = "default",
    custom_profile: Optional[dict] = None,
) -> dict:
    """
    对线索进行ICP匹配度评分（0-100）并返回资质评估结果。

    Args:
        lead: 包含research_data（来自research.py）的字典，加上：
              - domain (str)
              - company (str)
              - industry (str, 可选)
              - region (str, 可选)
        icp_profile: ICP_PROFILES中的命名配置文件键，或"default"
        custom_profile: 完全覆盖ICP配置文件字典

    Returns:
        包含以下键的字典：score (0-100), tier (hot/warm/cold), reasons (列表),
                   recommended_action (str), breakdown (维度分数字典)
    """
    research_data = lead.get("audit") or lead.get("research_data") or lead
    industry = lead.get("industry", "")
    domain = lead.get("domain", "")
    company = lead.get("company", domain)

    profile = custom_profile or ICP_PROFILES.get(icp_profile, ICP_PROFILES["default"])
    pain_weight = profile.get("pain_weight", 1.0)

    # 各维度评分
    size_score, size_reasons = _score_company_size(research_data)
    industry_score, industry_reasons = _score_industry_fit(industry, profile)
    maturity_score, maturity_reasons = _score_digital_maturity(research_data)
    pain_score, pain_reasons = _score_pain_signals(research_data, pain_weight)
    revenue_score, revenue_reasons = _score_revenue_signals(research_data)
    contact_score, contact_reasons = _score_contact_quality(research_data)

    total = size_score + industry_score + maturity_score + pain_score + revenue_score + contact_score
    total = min(total, 100)

    # 确定等级
    if total >= 70:
        tier = "hot"
        action = "优先跟进：本周内在LinkedIn上建立连接"
    elif total >= 45:
        tier = "warm"
        action = "建立连接：加入标准外展序列"
    else:
        tier = "cold"
        action = "培育：低优先级，加入长期线索池"

    # 构建扁平原因列表（仅顶级信号）
    all_reasons = (
        industry_reasons[:1]
        + pain_reasons[:2]
        + contact_reasons[:1]
        + size_reasons[:1]
        + maturity_reasons[:1]
    )

    return {
        "domain": domain,
        "company": company,
        "score": total,
        "tier": tier,
        "recommended_action": action,
        "reasons": all_reasons,
        "breakdown": {
            "company_size": size_score,
            "industry_fit": industry_score,
            "digital_maturity": maturity_score,
            "pain_signals": pain_score,
            "revenue_signals": revenue_score,
            "contact_quality": contact_score,
        },
    }


def qualify_batch(
    leads: list[dict],
    icp_profile: str = "default",
    custom_profile: Optional[dict] = None,
    verbose: bool = True,
) -> list[dict]:
    """
    批量评估线索列表，按分数降序返回。

    Args:
        leads:        线索字典列表（每个包含audit/research_data）
        icp_profile:  命名配置文件或"default"
        custom_profile: 覆盖配置文件字典
        verbose:      是否输出进度

    Returns:
        按分数降序排列的资质评估结果列表
    """
    results = []
    for lead in leads:
        result = qualify(lead, icp_profile=icp_profile, custom_profile=custom_profile)
        results.append({**lead, "qualification": result})
        if verbose:
            tier_map = {"hot": "热门", "warm": "温暖", "cold": "冷淡"}
            tier_cn = tier_map.get(result["tier"], result["tier"])
            print(
                f"  {result['company']}（{result['domain']}）："
                f"{result['score']}/100 [{tier_cn}] - {result['recommended_action']}",
                flush=True,
            )

    results.sort(key=lambda x: x["qualification"]["score"], reverse=True)
    return results
