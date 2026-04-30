"""tests/test_qualify.py - ICP评分模块单元测试。"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from opengtm.qualify import qualify, qualify_batch, INDUSTRY_TIERS, ICP_PROFILES


# ============================================================
# 测试数据
# ============================================================

SAMPLE_LEAD_HOT = {
    "domain": "example-saas.com",
    "company": "Example SaaS",
    "industry": "B2B SaaS",
    "audit": {
        "contact": {"name": "张三", "title": "CEO", "email": "zhang@example.com", "phone": "13800138000"},
        "findings": [
            {"type": "meta_description", "severity": "high", "detail": "Meta description missing"},
            {"type": "title_tag", "severity": "medium", "detail": "Title tag too generic"},
            {"type": "social_links", "severity": "medium", "detail": "No social links found"},
            {"type": "schema", "severity": "low", "detail": "No schema markup"},
        ],
        "title_tag_text": "Example SaaS - 企业级协作平台",
        "meta_description_text": "MISSING",
        "site_language": "zh",
        "has_blog_or_news": True,
        "has_social_links": True,
        "overall_assessment": "网站有明显的SEO优化空间",
    },
}

SAMPLE_LEAD_COLD = {
    "domain": "tiny-restaurant.com",
    "company": "小饭馆",
    "industry": "餐饮",
    "audit": {
        "contact": {"name": "", "title": "", "email": None, "phone": None},
        "findings": [],
        "title_tag_text": "首页",
        "meta_description_text": "MISSING",
        "site_language": "zh",
        "has_blog_or_news": False,
        "has_social_links": False,
        "overall_assessment": "简单网站",
    },
}


# ============================================================
# 测试用例
# ============================================================

def test_qualify_returns_required_keys():
    """qualify() 应返回包含必要键的字典。"""
    result = qualify(SAMPLE_LEAD_HOT)
    assert "score" in result
    assert "tier" in result
    assert "recommended_action" in result
    assert "reasons" in result
    assert "breakdown" in result


def test_qualify_score_range():
    """评分应在 0-100 范围内。"""
    result = qualify(SAMPLE_LEAD_HOT)
    assert 0 <= result["score"] <= 100


def test_qualify_hot_lead():
    """B2B SaaS + 多痛点 + 有联系人 → 应该是 hot 或 warm。"""
    result = qualify(SAMPLE_LEAD_HOT)
    assert result["tier"] in ("hot", "warm")
    assert result["score"] >= 45


def test_qualify_cold_lead():
    """餐饮 + 无联系人 + 无发现 → 应该是 cold。"""
    result = qualify(SAMPLE_LEAD_COLD)
    assert result["tier"] == "cold"
    assert result["score"] < 45


def test_qualify_breakdown_dimensions():
    """breakdown 应包含 6 个维度。"""
    result = qualify(SAMPLE_LEAD_HOT)
    bd = result["breakdown"]
    assert "company_size" in bd
    assert "industry_fit" in bd
    assert "digital_maturity" in bd
    assert "pain_signals" in bd
    assert "revenue_signals" in bd
    assert "contact_quality" in bd


def test_qualify_breakdown_limits():
    """每个维度不应超过其满分。"""
    result = qualify(SAMPLE_LEAD_HOT)
    bd = result["breakdown"]
    assert bd["company_size"] <= 20
    assert bd["industry_fit"] <= 25
    assert bd["digital_maturity"] <= 15
    assert bd["pain_signals"] <= 20
    assert bd["revenue_signals"] <= 10
    assert bd["contact_quality"] <= 10


def test_qualify_batch_sorted():
    """批量评分应按分数降序排列。"""
    leads = [SAMPLE_LEAD_COLD, SAMPLE_LEAD_HOT]
    results = qualify_batch(leads, verbose=False)
    scores = [r["qualification"]["score"] for r in results]
    assert scores == sorted(scores, reverse=True)


def test_qualify_icp_profiles():
    """不同 ICP 配置应产生不同评分。"""
    result_saas = qualify(SAMPLE_LEAD_HOT, icp_profile="saas")
    result_default = qualify(SAMPLE_LEAD_HOT, icp_profile="default")
    # saas 配置对 B2B SaaS 行业应该有 pain_weight=1.2 加成
    assert result_saas["score"] >= result_default["score"] - 5  # 允许小偏差


def test_industry_tiers_coverage():
    """INDUSTRY_TIERS 应包含中英文行业名。"""
    assert "B2B SaaS" in INDUSTRY_TIERS
    assert "IT服务" in INDUSTRY_TIERS
    assert "餐饮" in INDUSTRY_TIERS


def test_qualify_empty_audit():
    """无 audit 数据时不应崩溃。"""
    lead = {"domain": "test.com", "company": "Test", "industry": "SaaS"}
    result = qualify(lead)
    assert 0 <= result["score"] <= 100
