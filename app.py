"""
Floom应用入口。

向Floom运行时暴露两个GTM操作：

  - aeo_health: 对任意URL运行29项AEO/SEO健康检查报告。
                无需API密钥，仅使用httpx抓取+本地评分。
  - score_lead: 对线索字典（调研输出）进行ICP匹配度评分，
                返回等级（热门/温暖/冷淡）和推荐操作。

opengtm提供的功能远不止这些（调研、外展、消息、博客、
AI可见性检测），但这些功能依赖LLM、CRM访问和多步骤流水线。
此包装器保持精简：两个纯函数，独立可用，与Floom无状态运行时兼容。
"""

import json

from floom import app

from opengtm.analytics import run_health_check
from opengtm.qualify import qualify as _qualify


def _coerce_json(value, default=None):
    """解析可能已经是dict/list或JSON编码字符串的值。"""
    if value is None or value == "":
        return default
    if isinstance(value, (dict, list)):
        return value
    if isinstance(value, str):
        try:
            return json.loads(value)
        except json.JSONDecodeError:
            return default
    return default


@app.action
def aeo_health(url: str, timeout: float = 30.0) -> dict:
    """
    对URL运行29项AEO/SEO健康检查报告。

    涵盖技术SEO（16项）、结构化数据（6项）、AI爬虫访问（4项）
    和权威信号（3项）。返回分层评分、字母等级（A+到F）和发现列表。
    """
    if not url or not isinstance(url, str):
        return {"error": "url参数必填"}
    try:
        return run_health_check(url, timeout=timeout)
    except Exception as exc:
        return {"error": f"健康检查失败：{exc}", "url": url}


@app.action
def score_lead(
    lead,
    icp_profile: str = "default",
    custom_profile=None,
) -> dict:
    """
    对线索进行ICP匹配度评分（0-100），返回等级和推荐操作。

    `lead`是一个字典（或JSON编码字符串），至少包含：
      - domain (str)
      - company (str)
      - industry (str, 可选)
      - research_data (dict, 可选) -- opengtm research.py的输出
    `icp_profile`选择内置配置文件（default, saas, agency等）。
    传入`custom_profile`（字典或JSON字符串）可完全覆盖配置文件。
    """
    lead_dict = _coerce_json(lead)
    if not isinstance(lead_dict, dict):
        return {"error": "lead必须是JSON对象"}

    profile_dict = _coerce_json(custom_profile) if custom_profile else None

    try:
        return _qualify(lead_dict, icp_profile=icp_profile, custom_profile=profile_dict)
    except Exception as exc:
        return {"error": f"score_lead失败：{exc}"}
