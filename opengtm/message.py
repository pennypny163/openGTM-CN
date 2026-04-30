"""
message.py - 基于审计发现生成外展消息。

生成个性化的LinkedIn连接请求 + 私信序列，
基于具体的网站审计发现。

支持中文、英文和德文输出。
语言由 DEFAULT_LANGUAGE 环境变量或 language 参数控制。

消息模式框架：
  A - 具体技术发现（标题、meta、损坏元素等）
  B - 竞争对手差距（需手动填入竞争对手名称）
  C - 博客/内容未被索引
  D - 免费工具/资源提供
  E - AI可见性角度（同行对比）
"""

from __future__ import annotations

import hashlib
import os
from typing import Optional

DEFAULT_LANGUAGE = os.environ.get("DEFAULT_LANGUAGE", "zh")


# ---------------------------------------------------------------------------
# 语言字符串（ZH + EN + DE）
# ---------------------------------------------------------------------------

_STRINGS = {
    "zh": {
        "connection_micro": {
            "no_meta": "我注意到{domain}没有meta描述。",
            "meta_issue": "我查看了{domain}，发现meta描述有一些快速优化空间。",
            "content": "{domain}上的博客有未开发的SEO潜力。",
            "generic": "我查看了{domain}，注意到一些问题。",
        },
        "connection_variants": {
            "micro": [
                "{micro} 正在研究{region}的{industry_nom}。建立连接？",
                "正在研究{industry_nom}和AI可见性。{micro} 建立连接？",
                "{micro} 很乐意分享。建立连接？",
            ],
            "no_micro": [
                "正在研究{industry_nom}在AI搜索（ChatGPT、豆包）中的表现。有{domain}的数据。建立连接？",
                "正在对比{industry_nom}在AI搜索引擎中的表现。{company}在我的研究列表中。建立连接？",
                "正在研究{region}{industry_nom}的AI可见性。有{domain}的结果。建立连接？",
            ],
        },
        "pat_d": "{addr}你知道你们的AI可见性吗？可以在60秒内查看{domain}在ChatGPT和豆包中的排名。值得一看？",
        "pat_e": "{addr}我测试了{domain}是否出现在ChatGPT和豆包中。{region}大多数{industry_nom}还没有。我有{company}的结果。感兴趣吗？",
        "pat_b": "{addr}[竞争对手]在ChatGPT的{industry_nom}搜索中出现了，{company}还没有。我分析了原因。感兴趣吗？",
        "blog_pat_c": "{addr}我注意到{domain}上的博客没有被搜索引擎很好地收录。内容是有的，但在搜索中没有展现。通常只需1-2个技术修复。你们注意到了吗？",
        "meta_missing": "{addr}我注意到{domain}没有meta描述。搜索引擎会在搜索结果中显示随机文本片段。这是个快速修复，5分钟的工作。{extra}",
        "meta_short": "{addr}{domain}的meta描述比较短{char_info}。用120-160个字符可以从搜索结果中获得明显更多的点击。{extra}",
        "meta_long": "{addr}{domain}的meta描述在搜索结果中被截断了。你们的核心信息没有完整展现。{extra}",
        "title_generic": "{addr}{domain}的标题标签写的是\"{title_preview}\"。一个更具体的标题会提高相关搜索的排名。{extra}",
        "title_long": "{addr}{domain}的标题标签有{title_len}个字符，但搜索引擎只显示60个。你们的主要信息被截断了。{extra}",
        "title_stuffed": "{addr}{domain}的标题标签写的是\"{title_preview}\"。搜索引擎现在更偏好清晰、聚焦的标题，而不是关键词堆砌。{extra}",
        "broken_placeholder": "{addr}{domain}上有一段占位符文本可能不应该出现在那里。搜索引擎和访客都会注意到。快速修复即可。{extra}",
        "broken_links": "{addr}我注意到{domain}上有些链接指向空处（href=\"#\"）。快速修复就能改善用户体验。{extra}",
        "broken_generic": "{addr}{domain}上有一些损坏的元素，访客可能会注意到。通常都是快速修复。{extra}",
        "language_mismatch": "{addr}我注意到{domain}的部分内容是一种语言，其余是另一种。搜索引擎无法为网站分配明确的语言。快速修复即可。{extra}",
        "social_links": "{addr}{domain}上没有链接到{company}的社交媒体主页。访客和搜索引擎缺少信任信号。{extra}",
        "schema": "{addr}{domain}还没有使用Schema标记。有了它，你们可以在搜索引擎中通过富摘要（评分、价格、FAQ）脱颖而出。{extra}",
        "generic_findings": "{addr}我查看了{domain}，发现了{n_str}可以提升你们可见性的问题。我可以发送详细信息吗？",
        "extra_one": "这是有意为之还是疏忽？",
        "extra_multi": "你们注意到了吗？",
        "fu1_base": "又看了一下{domain}。{bestfix}。{rest}很乐意分享概览。",
        "fu2_base": "一个数据点：在{region}20多家{industry_nom}中，约60%有和{domain}相同的问题。似乎是行业通病。想知道你们的排名吗？",
        "fu3_base": "关于{domain}的最后一条消息。如果现在不是合适的时机，没关系。如果情况有变，我们的发现随时可以分享。",
        "fu1_no_findings": "做了一个对比：{domain}与{region}其他{industry_nom}的AI可见性。我可以发送结果吗？",
        "fu2_no_findings": "一个数据：{region}的{industry_nom}中只有约20%被AI搜索引擎推荐。我有{company}的数据，很乐意分享。",
        "fu1_clean": "又看了一下{domain}：技术上很干净，但在ChatGPT和豆包中不可见。这比你想象的更常见。我可以告诉你原因吗？",
        "fu2_clean": "一个数据：即使像{domain}这样技术上干净的网站，在AI搜索引擎中也经常不可见。我有与{region}其他{industry_nom}的对比，很乐意分享。",
        "bestfix": {
            "meta_description_missing": "meta描述完全缺失，5分钟即可添加",
            "meta_description": "优化meta描述可以直接提高搜索引擎的点击率",
            "title_tag": "调整标题标签是提升搜索排名最快的方法",
            "content_indexing": "博客内容未被索引，通常是1-2个技术设置的问题",
            "social_links": "添加社交媒体链接可以增强网站的信任信号",
            "broken_element": "首页上的损坏元素可以快速修复",
            "schema": "缺少Schema标记，富摘要可以帮助你们在搜索中脱颖而出",
            "language_mismatch": "语言不一致会混淆搜索引擎，可以快速统一",
            "default": "一个快速优化可以立即实施",
        },
    },
    "en": {
        "connection_micro": {
            "no_meta": "I noticed {domain} doesn't have a meta description.",
            "meta_issue": "I checked {domain} and noticed some quick wins on the meta description.",
            "content": "Your blog on {domain} has untapped SEO potential.",
            "generic": "I had a look at {domain} and noticed a few things.",
        },
        "connection_variants": {
            "micro": [
                "{micro} Exploring {industry_nom} in {region}. Connect?",
                "Exploring {industry_nom} and AI visibility. {micro} Connect?",
                "{micro} Happy to share. Connect?",
            ],
            "no_micro": [
                "Looking at how {industry_nom} rank in AI search (ChatGPT, Perplexity). Have data on {domain}. Connect?",
                "Comparing {industry_nom} in AI search engines. {company} is on my list. Connect?",
                "Researching AI visibility of {industry_nom} in {region}. Have results for {domain}. Connect?",
            ],
        },
        "pat_d": "{addr}do you know your AI visibility? You can check how {domain} ranks in ChatGPT and Perplexity in 60 seconds. Worth a look?",
        "pat_e": "{addr}I tested whether {domain} shows up in ChatGPT and Perplexity. Most {industry_nom} in {region} don't yet. I have the results for {company}. Relevant?",
        "pat_b": "{addr}[COMPETITOR] shows up in ChatGPT for {industry_nom}, {company} doesn't yet. I looked at why. Relevant?",
        "blog_pat_c": "{addr}I noticed your blog on {domain} isn't being picked up well by search engines. The content is there, but it's not surfacing in searches. Usually 1-2 technical fixes. On your radar?",
        "meta_missing": "{addr}I noticed {domain} has no meta description. Google shows random text snippets in search results instead. Quick win, 5 minutes of work. {extra}",
        "meta_short": "{addr}the meta description on {domain} is quite short{char_info}. With 120-160 characters you'd get significantly more clicks from search results. {extra}",
        "meta_long": "{addr}the meta description on {domain} gets cut off in search results. Your core message doesn't come through fully. {extra}",
        "title_generic": "{addr}the title tag on {domain} says \"{title_preview}\". A more specific title would improve rankings for relevant searches. {extra}",
        "title_long": "{addr}the title tag on {domain} is {title_len} characters, but Google only shows 60. Your main message gets cut off. {extra}",
        "title_stuffed": "{addr}the title tag on {domain} says \"{title_preview}\". Google prefers clear, focused titles over keyword lists today. {extra}",
        "broken_placeholder": "{addr}there's placeholder text visible on {domain} that probably shouldn't be there. Search engines and visitors notice this. Quick fix. {extra}",
        "broken_links": "{addr}I noticed some links on {domain} go nowhere (href=\"#\"). Quick fix that improves user experience. {extra}",
        "broken_generic": "{addr}there are a few broken elements on {domain} that visitors might notice. Usually quick fixes. {extra}",
        "language_mismatch": "{addr}I noticed parts of {domain} are in one language while the rest is in another. Search engines can't assign a clear language to the site. Quick fix. {extra}",
        "social_links": "{addr}there are no links to {company}'s social media profiles on {domain}. Visitors and search engines miss trust signals. {extra}",
        "schema": "{addr}{domain} doesn't use schema markup yet. With it you could stand out in Google with rich snippets (ratings, prices, FAQ). {extra}",
        "generic_findings": "{addr}I had a look at {domain} and found {n_str} that could improve your visibility. Can I send you the details?",
        "extra_one": "Intentional, or an oversight?",
        "extra_multi": "On your radar?",
        "fu1_base": "Had another look at {domain}. {bestfix}. {rest} Happy to share the overview.",
        "fu2_base": "Quick data point: of 20+ {industry_nom} in {region}, about 60% have the same issues as {domain}. Seems industry-typical. Want to know where you stand?",
        "fu3_base": "Last message on {domain}. If this isn't the right time, no problem. The findings stay with us if that changes.",
        "fu1_no_findings": "Made a comparison: AI visibility of {domain} vs other {industry_nom} in {region}. Can I send you the results?",
        "fu2_no_findings": "Quick stat: only about 20% of {industry_nom} in {region} get recommended by AI search engines. I have the data for {company}, happy to share.",
        "fu1_clean": "Had another look at {domain}: technically clean, but not visible in ChatGPT and Perplexity. More common than you'd think. Can I show you why?",
        "fu2_clean": "Quick stat: even technically clean sites like {domain} are often invisible to AI search engines. I have the comparison with other {industry_nom} in {region}, happy to share.",
        "bestfix": {
            "meta_description_missing": "meta description is missing entirely, can be added in 5 minutes",
            "meta_description": "optimizing the meta description directly improves click-through from Google",
            "title_tag": "adjusting the title tag is the fastest lever for better search rankings",
            "content_indexing": "blog content isn't being indexed, usually 1-2 technical settings",
            "social_links": "adding social media links builds trust signals on the website",
            "broken_element": "a broken element on the homepage can be fixed quickly",
            "schema": "schema markup is missing, rich snippets would help you stand out in search",
            "language_mismatch": "language inconsistency confuses search engines, quick to unify",
            "default": "a quick win can be implemented right away",
        },
    },
    "de": {
        "connection_micro": {
            "no_meta": "Mir ist aufgefallen, dass {domain} keine Meta-Description hat.",
            "meta_issue": "Habe mir {domain} angeschaut, bei der Meta-Description gibt es Quick Wins.",
            "content": "Euer Blog auf {domain} hat ungenutztes SEO-Potenzial.",
            "generic": "Habe mir {domain} angeschaut, ein paar Sachen aufgefallen.",
        },
        "connection_variants": {
            "micro": [
                "{micro} Schaue mir gerade {industry_nom} in {region} an. Vernetzen?",
                "Schaue mir gerade {industry_nom} und KI-Sichtbarkeit an. {micro} Vernetzen?",
                "{micro} Kann ich gern teilen. Vernetzen?",
            ],
            "no_micro": [
                "Schaue mir gerade an, wie {industry_nom} bei ChatGPT und Perplexity abschneiden. Habe Daten zu {domain}. Vernetzen?",
                "Vergleiche gerade {industry_nom} bei KI-Suchmaschinen. {company} ist dabei. Vernetzen?",
                "Recherchiere KI-Sichtbarkeit von {industry_nom} in {region}. Habe Ergebnisse für {domain}. Vernetzen?",
            ],
        },
        "pat_d": "{addr}kennt ihr eure KI-Sichtbarkeit? Auf einem Check-Tool kann man in 60 Sekunden sehen wie {domain} bei ChatGPT und Perplexity abschneidet. Spannend?",
        "pat_e": "{addr}habe getestet, ob {domain} bei ChatGPT und Perplexity auftaucht. Bei den meisten {industry_nom} in {region} ist das noch nicht der Fall. Habe die Ergebnisse für {company}. Relevant?",
        "pat_b": "{addr}[WETTBEWERBER] taucht bei ChatGPT für {industry_nom} auf, {company} noch nicht. Habe mir angeschaut woran das liegt. Relevant?",
        "blog_pat_c": "{addr}mir ist aufgefallen, dass euer Blog auf {domain} von Suchmaschinen kaum erfasst wird. Die Inhalte sind da, kommen aber bei Suchanfragen nicht an. Liegt meistens an 1-2 technischen Kleinigkeiten. Habt ihr das auf dem Schirm?",
        "meta_missing": "{addr}mir ist aufgefallen, dass {domain} keine Meta-Description hat. Google zeigt dann zufällige Textfragmente in den Suchergebnissen. Ist ein Quick Win, 5 Minuten Arbeit. {extra}",
        "meta_short": "{addr}die Meta-Description von {domain} ist recht kurz{char_info}. Mit 120-160 Zeichen holt ihr deutlich mehr Klicks aus den Suchergebnissen raus. {extra}",
        "meta_long": "{addr}die Meta-Description von {domain} wird in den Suchergebnissen abgeschnitten. Eure Kernaussage kommt dadurch nicht komplett an. {extra}",
        "title_generic": "{addr}im Title-Tag von {domain} steht \"{title_preview}\". Mit einem spezifischeren Title würde {company_first} bei relevanten Suchen besser ankommen. {extra}",
        "title_long": "{addr}der Title-Tag von {domain} hat {title_len} Zeichen, Google zeigt aber nur 60. Eure Kernaussage wird abgeschnitten. {extra}",
        "title_stuffed": "{addr}im Title-Tag von {domain} steht \"{title_preview}\". Google bevorzugt heute klare, fokussierte Titles statt Keyword-Listen. {extra}",
        "broken_placeholder": "{addr}auf {domain} ist ein Platzhaltertext sichtbar, der vermutlich nicht da sein sollte. Fällt Besuchern und Suchmaschinen auf. Schnell behebbar. {extra}",
        "broken_links": "{addr}mir ist aufgefallen, dass auf {domain} einige Links ins Leere führen (href=\"#\"). Lässt sich schnell fixen und verbessert die Nutzererfahrung. {extra}",
        "broken_generic": "{addr}auf {domain} gibt es ein paar defekte Elemente, die Besuchern auffallen könnten. Meistens schnell behebbar. {extra}",
        "language_mismatch": "{addr}mir ist aufgefallen, dass auf {domain} Teile in einer Sprache sind, der Rest in einer anderen. Suchmaschinen können die Seite dadurch keiner Sprache klar zuordnen. Schnell behebbar. {extra}",
        "social_links": "{addr}auf {domain} verweist nichts auf eure Social-Media-Profile. Besucher und Suchmaschinen finden dadurch keine weiteren Vertrauenssignale. {extra}",
        "schema": "{addr}{domain} nutzt noch kein Schema Markup. Damit könntet ihr bei Google mit Rich Snippets auffallen, z.B. Bewertungen, Preise, FAQ. {extra}",
        "generic_findings": "{addr}habe mir {domain} angeschaut und {n_str} gefunden, die eure KI-Sichtbarkeit verbessern könnten. Kann ich euch die Details schicken?",
        "extra_one": "Ist das bewusst so oder ein Versehen?",
        "extra_multi": "Habt ihr das auf dem Schirm?",
        "fu1_base": "Habe mir {domain} nochmal angeschaut. {bestfix}. {rest} Übersicht kann ich gern schicken.",
        "fu2_base": "Kurzer Datenpunkt: von 20+ {industry_nom} in {region} haben ca. 60% dieselben Themen wie {domain}. Scheint branchentypisch. Wollt ihr wissen wo ihr im Vergleich steht?",
        "fu3_base": "Letzte Nachricht zu {domain}. Falls gerade kein Thema, völlig ok. Die Ergebnisse bleiben bei uns, falls sich das ändert.",
        "fu1_no_findings": "Habe einen Vergleich gemacht: KI-Sichtbarkeit von {domain} vs. andere {industry_nom} in {region}. Kann ich euch die Ergebnisse schicken?",
        "fu2_no_findings": "Kurzer Datenpunkt: von den {industry_nom} in {region} werden nur ca. 20% von KI-Suchmaschinen empfohlen. Habe die Daten für {company}, kann ich gern teilen.",
        "fu1_clean": "Habe mir {domain} nochmal angeschaut: technisch sauber, aber bei ChatGPT und Perplexity nicht sichtbar. Kommt häufiger vor als man denkt. Kann ich euch zeigen woran das liegt?",
        "fu2_clean": "Kurzer Datenpunkt: auch technisch saubere Seiten wie {domain} sind oft bei KI-Suchmaschinen unsichtbar. Habe den Vergleich mit anderen {industry_nom} in {region}, kann ich gern teilen.",
        "bestfix": {
            "meta_description_missing": "Meta-Description fehlt komplett, lässt sich in 5 Minuten ergänzen",
            "meta_description": "Meta-Description optimieren bringt direkt mehr Klicks aus Google",
            "title_tag": "Title-Tag anpassen ist der schnellste Hebel für bessere Suchergebnisse",
            "content_indexing": "Blog-Inhalte werden nicht indexiert, meistens liegt es an 1-2 technischen Einstellungen",
            "social_links": "Social-Media-Links auf der Website einbinden stärkt die Vertrauenssignale",
            "broken_element": "ein defektes Element auf der Startseite lässt sich schnell beheben",
            "schema": "Schema Markup fehlt, mit Rich Snippets hebt ihr euch in den Suchergebnissen ab",
            "language_mismatch": "Sprachmix verwirrt Suchmaschinen, lässt sich schnell vereinheitlichen",
            "default": "ein Quick Win lässt sich direkt umsetzen",
        },
    },
}

# 行业显示名称（用于消息中的主格形式）
INDUSTRY_DISPLAY: dict[str, dict[str, str]] = {
    "zh": {
        "IT Services": "IT服务商",
        "IT服务": "IT服务商",
        "Marketing & Advertising": "营销机构",
        "市场营销": "营销机构",
        "Financial Services": "金融服务公司",
        "金融服务": "金融服务公司",
        "Accounting": "会计事务所",
        "会计": "会计事务所",
        "Legal Services": "律师事务所",
        "法律服务": "律师事务所",
        "Management Consulting": "咨询公司",
        "管理咨询": "咨询公司",
        "Design": "设计机构",
        "设计": "设计机构",
        "Recruiting": "人力资源公司",
        "人力资源": "人力资源公司",
        "E-Commerce": "电商公司",
        "电子商务": "电商公司",
        "Cybersecurity": "网络安全公司",
        "网络安全": "网络安全公司",
        "SaaS": "SaaS公司",
        "B2B SaaS": "B2B SaaS公司",
        "Medical": "医疗机构",
        "医疗": "医疗机构",
        "Real Estate": "房地产公司",
        "房地产": "房地产公司",
        "Industrial": "工业企业",
        "工业制造": "工业企业",
        "云计算": "云计算公司",
        "人工智能": "AI公司",
    },
    "en": {
        "IT Services": "IT service providers",
        "Marketing & Advertising": "marketing agencies",
        "Financial Services": "financial service firms",
        "Accounting": "accounting firms",
        "Legal Services": "law firms",
        "Management Consulting": "consulting firms",
        "Design": "design agencies",
        "Recruiting": "recruiting firms",
        "E-Commerce": "e-commerce companies",
        "Cybersecurity": "cybersecurity firms",
        "SaaS": "SaaS companies",
        "B2B SaaS": "B2B SaaS companies",
        "Medical": "medical practices",
        "Real Estate": "real estate companies",
        "Industrial": "industrial companies",
    },
    "de": {
        "IT Services": "IT-Dienstleistern",
        "Marketing & Advertising": "Agenturen",
        "Financial Services": "Steuerberatungen und Finanzdienstleistern",
        "Accounting": "Wirtschaftsprüfern und Kanzleien",
        "Legal Services": "Kanzleien",
        "Management Consulting": "Beratungen",
        "Design": "Designbüros und Agenturen",
        "Recruiting": "Personalberatungen",
        "E-Commerce": "E-Commerce-Unternehmen",
        "Cybersecurity": "Cybersecurity-Unternehmen",
        "SaaS": "SaaS-Unternehmen",
        "B2B SaaS": "B2B SaaS-Unternehmen",
        "Medical": "Privatkliniken und Praxen",
        "Real Estate": "Immobilienunternehmen",
        "Industrial": "Industrieunternehmen",
    },
}


def _hash_variant(key: str, domain: str, n: int) -> int:
    """确定性变体选择器（相同域名始终获得相同变体）。"""
    return int(hashlib.md5((key + domain).encode()).hexdigest(), 16) % n


def _get_address(contact_name: str, contact_title: str = "", industry: str = "", language: str = "zh") -> str:
    """构建个性化的消息称呼前缀。"""
    if not contact_name:
        return ""
    parts = contact_name.strip().split()
    if language == "zh":
        return f"{contact_name}，"
    elif language == "de":
        formal_industries = {
            "Financial Services", "Accounting", "Legal Services",
            "Management Consulting", "Medical", "Real Estate",
            "金融服务", "会计", "法律服务", "管理咨询", "医疗", "房地产",
        }
        if industry in formal_industries:
            female_indicators = [
                "geschäftsführerin", "inhaberin", "gründerin", "partnerin",
                "direktorin", "leiterin", "managerin", "beraterin",
                "rechtsanwältin", "steuerberaterin",
            ]
            is_female = any(t in contact_title.lower() for t in female_indicators)
            prefix = "Frau" if is_female else "Herr"
            return f"{prefix} {parts[-1]}, "
        else:
            return f"{parts[0]}, "
    else:
        return f"{parts[0]}, "


def generate_messages(
    domain: str,
    company: str,
    contact_name: str = "",
    industry: str = "",
    audit: Optional[dict] = None,
    region: str = "",
    contact_title: str = "",
    language: str = "",
) -> dict:
    """
    根据审计发现生成完整的外展消息集。

    Args:
        domain:        公司网站域名
        company:       公司名称
        contact_name:  决策者姓名（用于个性化）
        industry:      行业垂直领域
        audit:         来自research.py的字典（findings, title_tag_text等）
        region:        城市/地区（用于同行对比消息）
        contact_title: 联系人职位（用于正式/非正式称呼）
        language:      "zh"、"en"或"de"（默认使用DEFAULT_LANGUAGE环境变量或"zh"）

    Returns:
        包含以下键的字典：pattern (A/B/C/D/E), pattern_reason, best_finding,
                   connection_note, first_dm, followup, followup_2, followup_3,
                   alternatives (其他模式选项列表)
    """
    lang = language or DEFAULT_LANGUAGE
    if lang not in _STRINGS:
        lang = "zh"
    s = _STRINGS[lang]

    if domain.startswith("www."):
        domain = domain[4:]

    industry_nom = INDUSTRY_DISPLAY.get(lang, {}).get(industry) or (
        INDUSTRY_DISPLAY.get("zh", {}).get(industry) or
        INDUSTRY_DISPLAY.get("en", {}).get(industry, industry or ("企业" if lang == "zh" else "companies" if lang == "en" else "Unternehmen"))
    )
    addr = _get_address(contact_name, contact_title, industry, lang)
    company_first = company.split()[0] if company else domain
    reg = region or ("该地区" if lang == "zh" else "the region" if lang == "en" else "der Region")

    fu1_fail = s["fu1_no_findings"].format(
        domain=domain, industry_nom=industry_nom, region=reg, company=company
    )
    fu2_fail = s["fu2_no_findings"].format(
        domain=domain, industry_nom=industry_nom, region=reg, company=company
    )
    fu3 = s["fu3_base"].format(domain=domain)

    pat_d = s["pat_d"].format(addr=addr, domain=domain)
    pat_e = s["pat_e"].format(addr=addr, domain=domain, industry_nom=industry_nom, region=reg, company=company)
    pat_b = s["pat_b"].format(addr=addr, domain=domain, industry_nom=industry_nom, company=company)

    alternatives = [
        {"pattern": "D", "reason": "免费工具/资源提供" if lang == "zh" else "Free tool offer", "dm": pat_d},
        {"pattern": "E", "reason": "AI可见性角度" if lang == "zh" else "AI visibility angle", "dm": pat_e},
        {"pattern": "B", "reason": "竞争对手差距" if lang == "zh" else "Competitor gap", "dm": pat_b},
    ]

    _micro = ""
    if audit and audit.get("findings"):
        meta_text = audit.get("meta_description_text", "")
        ffindings = audit["findings"]
        if meta_text and "MISSING" in str(meta_text).upper():
            _micro = s["connection_micro"]["no_meta"].format(domain=domain)
        elif any(f.get("type") == "meta_description" for f in ffindings):
            _micro = s["connection_micro"]["meta_issue"].format(domain=domain)
        elif any(f.get("type") == "content_indexing" for f in ffindings):
            _micro = s["connection_micro"]["content"].format(domain=domain)
        elif ffindings:
            _micro = s["connection_micro"]["generic"].format(domain=domain)

    if _micro:
        variants = s["connection_variants"]["micro"]
        cn = variants[_hash_variant("sd1", domain, len(variants))].format(
            micro=_micro, industry_nom=industry_nom, region=reg
        )
    else:
        variants = s["connection_variants"]["no_micro"]
        cn = variants[_hash_variant("sd1", domain, len(variants))].format(
            industry_nom=industry_nom, region=reg, domain=domain, company=company
        )

    def _fu(bestfix_key: str, n_rest: int) -> tuple[str, str, str]:
        bestfix = s["bestfix"].get(bestfix_key, s["bestfix"]["default"])
        if n_rest == 0:
            rest = ""
        elif n_rest == 1:
            rest = "另外还有1个问题。" if lang == "zh" else ("Plus 1 more." if lang == "en" else "Dazu noch 1 weiterer Punkt.")
        else:
            rest = f"另外还有{n_rest}个问题。" if lang == "zh" else (f"Plus {n_rest} more." if lang == "en" else f"Dazu noch {n_rest} weitere Punkte.")
        fu1 = s["fu1_base"].format(domain=domain, bestfix=bestfix, rest=rest).strip()
        fu2_v = s["fu2_base"].format(domain=domain, industry_nom=industry_nom, region=reg)
        return fu1, fu2_v, fu3

    def _clean_fu() -> tuple[str, str, str]:
        return (
            s["fu1_clean"].format(domain=domain, industry_nom=industry_nom, region=reg),
            s["fu2_clean"].format(domain=domain, industry_nom=industry_nom, region=reg),
            fu3,
        )

    def _failed_fu() -> tuple[str, str, str]:
        return fu1_fail, fu2_fail, fu3

    if not audit:
        return {
            "pattern": "E", "pattern_reason": "无审计数据" if lang == "zh" else "No audit data",
            "best_finding": "",
            "connection_note": cn, "first_dm": pat_e,
            "followup": fu1_fail, "followup_2": fu2_fail, "followup_3": fu3,
            "alternatives": alternatives,
        }

    assessment = audit.get("overall_assessment", "")
    audit_failed = any(w in assessment.lower() for w in ["failed", "error", "unable", "could not", "失败", "错误"])
    findings = audit.get("findings", [])

    if not findings and audit_failed:
        fu1, fu2, _ = _failed_fu()
        return {
            "pattern": "E", "pattern_reason": "审计失败" if lang == "zh" else "Audit failed",
            "best_finding": "",
            "connection_note": cn, "first_dm": pat_e,
            "followup": fu1, "followup_2": fu2, "followup_3": fu3,
            "alternatives": alternatives,
        }

    if not findings:
        fu1, fu2, _ = _clean_fu()
        return {
            "pattern": "E", "pattern_reason": "网站干净" if lang == "zh" else "Clean site",
            "best_finding": "",
            "connection_note": cn, "first_dm": pat_e,
            "followup": fu1, "followup_2": fu2, "followup_3": fu3,
            "alternatives": alternatives,
        }

    positive_words = [
        "present", "optimally", "well within", "well-optimized", "well optimized",
        "active and", "actively provided", "no immediately visible",
        "strong foundational", "clear call-to-action", "gut aufgestellt",
        "良好", "正常", "完善", "优秀",
    ]
    problem_findings = [
        f for f in findings
        if not any(w in f.get("detail", "").lower() for w in positive_words)
    ]

    if not problem_findings:
        fu1, fu2, _ = _clean_fu()
        return {
            "pattern": "E", "pattern_reason": "所有发现均为正面" if lang == "zh" else "All positive findings",
            "best_finding": assessment,
            "connection_note": cn, "first_dm": pat_e,
            "followup": fu1, "followup_2": fu2, "followup_3": fu3,
            "alternatives": alternatives,
        }

    sev_order = {"high": 0, "medium": 1, "low": 2}
    sorted_findings = sorted(problem_findings, key=lambda f: sev_order.get(f.get("severity", "low"), 2))
    best = sorted_findings[0]
    ftype = best.get("type", "")
    detail = best.get("detail", "")
    evidence = best.get("evidence", "")
    extra_count = len(problem_findings) - 1
    extra = (s["extra_one"] if extra_count <= 0 else s["extra_multi"])

    title_text = audit.get("title_tag_text", "")
    meta_text = audit.get("meta_description_text", "")
    has_blog = audit.get("has_blog_or_news", False)

    def _ret(pattern: str, reason: str, dm: str, bestfix_key: str) -> dict:
        fu1, fu2_v, _ = _fu(bestfix_key, extra_count)
        return {
            "pattern": pattern, "pattern_reason": reason,
            "best_finding": detail,
            "connection_note": cn, "first_dm": dm,
            "followup": fu1, "followup_2": fu2_v, "followup_3": fu3,
            "alternatives": [a for a in alternatives],
        }

    negative_signals = [
        "not indexed", "not being indexed", "noindex", "blocked from",
        "not crawlable", "not accessible to search", "404", "not discoverable",
        "poor indexing", "indexing issue", "hidden from search",
        "nicht indexiert", "nicht erfasst", "noindex tag",
        "未索引", "未被收录", "无法抓取",
    ]
    content_findings = [f for f in findings if f.get("type") == "content_indexing"]
    problem_content = [
        f for f in content_findings
        if any(n in f.get("detail", "").lower() for n in negative_signals)
    ]
    if has_blog and problem_content:
        dm = s["blog_pat_c"].format(addr=addr, domain=domain)
        alternatives.insert(0, {"pattern": "C", "reason": "博客未被索引" if lang == "zh" else "Blog not indexed", "dm": dm})
        fu1, fu2_v, _ = _fu("content_indexing", extra_count)
        return {
            "pattern": "C", "pattern_reason": "博客/内容未被索引" if lang == "zh" else "Blog not indexed",
            "best_finding": problem_content[0]["detail"],
            "connection_note": cn, "first_dm": dm,
            "followup": fu1, "followup_2": fu2_v, "followup_3": fu3,
            "alternatives": alternatives,
        }

    if ftype == "content_indexing" and not has_blog and len(sorted_findings) > 1:
        best = sorted_findings[1]
        ftype = best.get("type", "")
        detail = best.get("detail", "")
        evidence = best.get("evidence", "")

    if ftype == "meta_description":
        if "MISSING" in str(meta_text).upper() or "missing" in detail.lower() or "缺失" in detail:
            dm = s["meta_missing"].format(addr=addr, domain=domain, extra=extra)
            return _ret("A", "Meta描述缺失", dm, "meta_description_missing")
        import re
        meta_len = len(meta_text) if meta_text and meta_text != "MISSING" else 0
        detail_l = detail.lower()
        is_short = meta_len < 120 or any(w in detail_l for w in ["too short", "zu kurz", "extremely short", "过短"])
        if is_short:
            char_match = re.search(r"(\d+)\s*(?:characters|chars|zeichen|字符)", detail_l)
            char_info = f"（{char_match.group(1)}字符）" if char_match else ""
            dm = s["meta_short"].format(addr=addr, domain=domain, char_info=char_info, extra=extra)
        else:
            dm = s["meta_long"].format(addr=addr, domain=domain, extra=extra)
        return _ret("A", "Meta描述问题", dm, "meta_description")

    if ftype == "title_tag":
        generic_words = ["homepage", "willkommen", "home", "startseite", "welcome", "首页", "欢迎"]
        is_generic = any(w in title_text.lower() for w in generic_words)
        is_long = len(title_text) > 60
        is_stuffed = title_text.count(",") > 2 or title_text.count("|") > 2 or title_text.count("，") > 2
        title_preview = title_text[:50]
        title_len = len(title_text)

        if is_generic:
            dm = s["title_generic"].format(addr=addr, domain=domain, title_preview=title_preview, company_first=company_first, extra=extra)
        elif is_long:
            dm = s["title_long"].format(addr=addr, domain=domain, title_len=title_len, extra=extra)
        elif is_stuffed:
            dm = s["title_stuffed"].format(addr=addr, domain=domain, title_preview=title_preview, extra=extra)
        else:
            dm = s["title_generic"].format(addr=addr, domain=domain, title_preview=title_preview, company_first=company_first, extra=extra)
        return _ret("A", f"标题标签：{detail[:50]}", dm, "title_tag")

    if ftype == "broken_element":
        detail_l = detail.lower()
        if any(w in detail_l for w in ["placeholder", "platzhalter", "占位符"]) and any(w in detail_l for w in ["visible", "plain text", "sichtbar", "shortcode", "可见"]):
            dm = s["broken_placeholder"].format(addr=addr, domain=domain, extra=extra)
        elif "#" in evidence or "anchor" in detail_l:
            dm = s["broken_links"].format(addr=addr, domain=domain, extra=extra)
        else:
            dm = s["broken_generic"].format(addr=addr, domain=domain, extra=extra)
        return _ret("A", "损坏元素", dm, "broken_element")

    if ftype == "language_mismatch":
        dm = s["language_mismatch"].format(addr=addr, domain=domain, extra=extra)
        return _ret("A", "语言不一致", dm, "language_mismatch")

    if ftype == "social_links":
        dm = s["social_links"].format(addr=addr, domain=domain, company=company, extra=extra)
        return _ret("A", "缺少社交媒体链接", dm, "social_links")

    if ftype == "schema":
        dm = s["schema"].format(addr=addr, domain=domain, extra=extra)
        return _ret("A", "缺少Schema标记", dm, "schema")

    n = len(problem_findings)
    if lang == "zh":
        n_str = f"{n}个问题"
    elif lang == "en":
        n_str = f"{n} thing{'s' if n > 1 else ''}"
    else:
        n_str = "eine Sache" if n == 1 else "ein paar Sachen"
    dm = s["generic_findings"].format(addr=addr, domain=domain, n_str=n_str)
    return _ret("A", "多个技术问题" if lang == "zh" else "Multiple technical issues", dm, "default")
