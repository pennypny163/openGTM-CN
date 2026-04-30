"""tests/test_message.py - 消息生成模块单元测试。"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from opengtm.message import generate_messages, INDUSTRY_DISPLAY


# ============================================================
# 测试数据
# ============================================================

AUDIT_WITH_FINDINGS = {
    "contact": {"name": "张三", "title": "CEO", "email": "zhang@example.com"},
    "findings": [
        {"type": "meta_description", "severity": "high", "detail": "Meta description is completely missing"},
        {"type": "title_tag", "severity": "medium", "detail": "Title tag is generic: 首页"},
    ],
    "title_tag_text": "首页",
    "meta_description_text": "MISSING",
    "site_language": "zh",
    "has_blog_or_news": False,
    "has_social_links": False,
    "overall_assessment": "网站缺少基本的SEO优化",
}

AUDIT_CLEAN = {
    "contact": {"name": "李四", "title": "CTO"},
    "findings": [],
    "title_tag_text": "示例公司 - 领先的SaaS平台",
    "meta_description_text": "示例公司提供企业级SaaS解决方案，帮助企业提升效率。",
    "site_language": "zh",
    "has_blog_or_news": True,
    "has_social_links": True,
    "overall_assessment": "网站状态良好",
}


# ============================================================
# 测试用例
# ============================================================

def test_generate_messages_returns_required_keys():
    """generate_messages() 应返回所有必要键。"""
    result = generate_messages(
        domain="example.com",
        company="示例公司",
        contact_name="张三",
        industry="B2B SaaS",
        audit=AUDIT_WITH_FINDINGS,
        region="北京",
        language="zh",
    )
    assert "pattern" in result
    assert "pattern_reason" in result
    assert "connection_note" in result
    assert "first_dm" in result
    assert "followup" in result
    assert "followup_2" in result
    assert "followup_3" in result
    assert "alternatives" in result


def test_pattern_a_on_meta_missing():
    """Meta 描述缺失应触发 Pattern A。"""
    result = generate_messages(
        domain="example.com",
        company="示例公司",
        audit=AUDIT_WITH_FINDINGS,
        language="zh",
    )
    assert result["pattern"] == "A"


def test_pattern_e_on_clean_site():
    """干净网站应触发 Pattern E。"""
    result = generate_messages(
        domain="example.com",
        company="示例公司",
        audit=AUDIT_CLEAN,
        language="zh",
    )
    assert result["pattern"] == "E"


def test_pattern_e_without_audit():
    """无 audit 数据应触发 Pattern E。"""
    result = generate_messages(
        domain="example.com",
        company="示例公司",
        audit=None,
        language="zh",
    )
    assert result["pattern"] == "E"


def test_message_contains_domain():
    """生成的消息应包含域名。"""
    result = generate_messages(
        domain="example.com",
        company="示例公司",
        audit=AUDIT_WITH_FINDINGS,
        language="zh",
    )
    assert "example.com" in result["first_dm"]


def test_message_personalization():
    """有联系人时消息应包含个性化称呼。"""
    result = generate_messages(
        domain="example.com",
        company="示例公司",
        contact_name="张三",
        audit=AUDIT_WITH_FINDINGS,
        language="zh",
    )
    assert "张三" in result["first_dm"]


def test_message_no_contact():
    """无联系人时不应崩溃。"""
    result = generate_messages(
        domain="example.com",
        company="示例公司",
        contact_name="",
        audit=AUDIT_WITH_FINDINGS,
        language="zh",
    )
    assert result["pattern"] in ("A", "B", "C", "D", "E")


def test_english_output():
    """英文模式应输出英文。"""
    result = generate_messages(
        domain="example.com",
        company="Example Co",
        contact_name="John",
        audit=AUDIT_WITH_FINDINGS,
        language="en",
    )
    # 英文消息不应包含中文标点
    assert "，" not in result["first_dm"]


def test_alternatives_always_present():
    """alternatives 应始终包含可选模式。"""
    result = generate_messages(
        domain="example.com",
        company="示例公司",
        audit=AUDIT_WITH_FINDINGS,
        language="zh",
    )
    assert len(result["alternatives"]) >= 2
    patterns = [a["pattern"] for a in result["alternatives"]]
    assert "D" in patterns or "E" in patterns


def test_industry_display_coverage():
    """INDUSTRY_DISPLAY 应支持中/英/德三语。"""
    assert "zh" in INDUSTRY_DISPLAY
    assert "en" in INDUSTRY_DISPLAY
    assert "de" in INDUSTRY_DISPLAY
    assert "B2B SaaS" in INDUSTRY_DISPLAY["zh"]


def test_connection_note_length():
    """连接请求不应超过 300 字符（LinkedIn 限制 280）。"""
    result = generate_messages(
        domain="example.com",
        company="示例公司",
        contact_name="张三",
        industry="B2B SaaS",
        audit=AUDIT_WITH_FINDINGS,
        region="北京",
        language="zh",
    )
    assert len(result["connection_note"]) <= 300
