"""
dashboard.py - OpenGTM Streamlit可视化仪表盘。

运行方式: streamlit run dashboard.py

功能：
  - 加载并可视化所有openGTM命令的JSON输出文件
  - 交互式流水线运行器（发现 -> 调研 -> 评分 -> 消息）
  - ICP评分分布图表
  - AEO健康检查雷达图
  - 博客文章预览
  - SEO关键词探索器
  - 外展序列管理器
  - 腾讯企业微信集成面板
"""

from __future__ import annotations

import json
import os
import sys
from datetime import datetime
from pathlib import Path

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

# 将项目根目录添加到路径
PROJECT_ROOT = Path(__file__).parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

# 加载.env文件
env_file = PROJECT_ROOT / ".env"
if env_file.exists():
    with open(env_file) as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, _, val = line.partition("=")
                if key.strip() not in os.environ:
                    os.environ[key.strip()] = val.strip().strip('"').strip("'")

# =========================================================================
# 页面配置
# =========================================================================

st.set_page_config(
    page_title="OpenGTM 控制台",
    page_icon="🚀",
    layout="wide",
    initial_sidebar_state="expanded",
)

# =========================================================================
# 自定义CSS — 专业设计系统
# =========================================================================

st.markdown("""
<style>
    /* ===== Global ===== */
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');

    .stApp {
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
    }

    /* ===== Sidebar ===== */
    div[data-testid="stSidebar"] {
        background: linear-gradient(180deg, #0f172a 0%, #1e293b 50%, #0f172a 100%);
        border-right: 1px solid rgba(99, 102, 241, 0.15);
    }
    div[data-testid="stSidebar"] .stMarkdown {
        color: #cbd5e1;
    }
    div[data-testid="stSidebar"] .stRadio label {
        color: #e2e8f0 !important;
        font-size: 0.92rem;
        transition: all 0.2s ease;
    }
    div[data-testid="stSidebar"] .stRadio label:hover {
        color: #818cf8 !important;
    }
    div[data-testid="stSidebar"] hr {
        border-color: rgba(99, 102, 241, 0.2);
    }

    /* ===== Metric Cards ===== */
    .stMetric > div {
        background: linear-gradient(135deg, #6366f1 0%, #8b5cf6 100%);
        padding: 20px 18px;
        border-radius: 16px;
        color: white;
        box-shadow: 0 4px 20px rgba(99, 102, 241, 0.25);
        border: 1px solid rgba(255,255,255,0.08);
        transition: transform 0.2s ease, box-shadow 0.2s ease;
    }
    .stMetric > div:hover {
        transform: translateY(-2px);
        box-shadow: 0 8px 30px rgba(99, 102, 241, 0.35);
    }
    .stMetric label {
        color: rgba(255,255,255,0.75) !important;
        font-weight: 500 !important;
        font-size: 0.82rem !important;
        text-transform: uppercase;
        letter-spacing: 0.05em;
    }
    .stMetric [data-testid="stMetricValue"] {
        color: white !important;
        font-weight: 700 !important;
        font-size: 1.8rem !important;
    }

    /* ===== Badges ===== */
    .hot-badge {
        background: linear-gradient(135deg, #ef4444, #dc2626);
        color: white;
        padding: 4px 12px;
        border-radius: 20px;
        font-weight: 600;
        font-size: 0.8em;
        letter-spacing: 0.03em;
        box-shadow: 0 2px 8px rgba(239, 68, 68, 0.3);
    }
    .warm-badge {
        background: linear-gradient(135deg, #f59e0b, #d97706);
        color: white;
        padding: 4px 12px;
        border-radius: 20px;
        font-weight: 600;
        font-size: 0.8em;
        letter-spacing: 0.03em;
        box-shadow: 0 2px 8px rgba(245, 158, 11, 0.3);
    }
    .cold-badge {
        background: linear-gradient(135deg, #3b82f6, #2563eb);
        color: white;
        padding: 4px 12px;
        border-radius: 20px;
        font-weight: 600;
        font-size: 0.8em;
        letter-spacing: 0.03em;
        box-shadow: 0 2px 8px rgba(59, 130, 246, 0.3);
    }

    /* ===== Cards ===== */
    .gtm-card {
        background: rgba(255, 255, 255, 0.03);
        border: 1px solid rgba(99, 102, 241, 0.12);
        border-radius: 16px;
        padding: 24px;
        margin-bottom: 16px;
        backdrop-filter: blur(10px);
        transition: border-color 0.2s ease;
    }
    .gtm-card:hover {
        border-color: rgba(99, 102, 241, 0.3);
    }

    /* ===== Hero Banner ===== */
    .hero-banner {
        background: linear-gradient(135deg, #1e1b4b 0%, #312e81 40%, #4338ca 100%);
        border-radius: 20px;
        padding: 40px 36px;
        margin-bottom: 28px;
        border: 1px solid rgba(99, 102, 241, 0.2);
        box-shadow: 0 8px 40px rgba(67, 56, 202, 0.15);
        position: relative;
        overflow: hidden;
    }
    .hero-banner::before {
        content: '';
        position: absolute;
        top: -50%;
        right: -20%;
        width: 400px;
        height: 400px;
        background: radial-gradient(circle, rgba(139, 92, 246, 0.15) 0%, transparent 70%);
        border-radius: 50%;
    }
    .hero-banner h1 {
        color: white;
        font-size: 2.2rem;
        font-weight: 700;
        margin: 0 0 8px 0;
        position: relative;
    }
    .hero-banner p {
        color: rgba(199, 210, 254, 0.85);
        font-size: 1.05rem;
        margin: 0;
        position: relative;
        line-height: 1.6;
    }

    /* ===== Section Headers ===== */
    .section-header {
        display: flex;
        align-items: center;
        gap: 10px;
        margin: 32px 0 16px 0;
        padding-bottom: 12px;
        border-bottom: 2px solid rgba(99, 102, 241, 0.15);
    }
    .section-header h3 {
        margin: 0;
        font-weight: 600;
        color: #e2e8f0;
    }

    /* ===== Buttons ===== */
    .stButton > button {
        background: linear-gradient(135deg, #6366f1 0%, #8b5cf6 100%) !important;
        color: white !important;
        border: none !important;
        border-radius: 12px !important;
        padding: 10px 24px !important;
        font-weight: 600 !important;
        font-size: 0.9rem !important;
        letter-spacing: 0.02em;
        transition: all 0.2s ease !important;
        box-shadow: 0 4px 15px rgba(99, 102, 241, 0.3) !important;
    }
    .stButton > button:hover {
        transform: translateY(-1px) !important;
        box-shadow: 0 6px 25px rgba(99, 102, 241, 0.45) !important;
    }
    .stButton > button:active {
        transform: translateY(0) !important;
    }

    /* ===== Download Buttons ===== */
    .stDownloadButton > button {
        background: transparent !important;
        color: #818cf8 !important;
        border: 1.5px solid rgba(99, 102, 241, 0.4) !important;
        border-radius: 12px !important;
        font-weight: 500 !important;
        transition: all 0.2s ease !important;
    }
    .stDownloadButton > button:hover {
        background: rgba(99, 102, 241, 0.1) !important;
        border-color: #818cf8 !important;
    }

    /* ===== Tabs ===== */
    .stTabs [data-baseweb="tab-list"] {
        gap: 4px;
        background: rgba(15, 23, 42, 0.5);
        border-radius: 14px;
        padding: 4px;
        border: 1px solid rgba(99, 102, 241, 0.1);
    }
    .stTabs [data-baseweb="tab"] {
        border-radius: 10px;
        padding: 10px 20px;
        font-weight: 500;
        transition: all 0.2s ease;
    }
    .stTabs [aria-selected="true"] {
        background: linear-gradient(135deg, #6366f1, #8b5cf6) !important;
        color: white !important;
        box-shadow: 0 2px 10px rgba(99, 102, 241, 0.3);
    }

    /* ===== Expanders ===== */
    .streamlit-expanderHeader {
        background: rgba(30, 41, 59, 0.5) !important;
        border-radius: 12px !important;
        border: 1px solid rgba(99, 102, 241, 0.1) !important;
        font-weight: 500;
        transition: all 0.2s ease;
    }
    .streamlit-expanderHeader:hover {
        border-color: rgba(99, 102, 241, 0.3) !important;
    }

    /* ===== DataFrames ===== */
    .stDataFrame {
        border-radius: 12px;
        overflow: hidden;
        border: 1px solid rgba(99, 102, 241, 0.1);
    }

    /* ===== Text Inputs ===== */
    .stTextInput > div > div > input {
        border-radius: 10px !important;
        border: 1.5px solid rgba(99, 102, 241, 0.2) !important;
        transition: border-color 0.2s ease !important;
    }
    .stTextInput > div > div > input:focus {
        border-color: #6366f1 !important;
        box-shadow: 0 0 0 3px rgba(99, 102, 241, 0.15) !important;
    }

    /* ===== Select Boxes ===== */
    .stSelectbox > div > div {
        border-radius: 10px !important;
    }

    /* ===== File Uploader ===== */
    .stFileUploader > div {
        border-radius: 12px !important;
        border: 2px dashed rgba(99, 102, 241, 0.25) !important;
        transition: border-color 0.2s ease;
    }
    .stFileUploader > div:hover {
        border-color: rgba(99, 102, 241, 0.5) !important;
    }

    /* ===== Alerts ===== */
    .stAlert {
        border-radius: 12px !important;
    }

    /* ===== Score Ring ===== */
    .score-ring {
        text-align: center;
        padding: 32px;
        border-radius: 20px;
        color: white;
        position: relative;
        overflow: hidden;
    }
    .score-ring::before {
        content: '';
        position: absolute;
        top: 0; left: 0; right: 0; bottom: 0;
        background: radial-gradient(circle at 30% 30%, rgba(255,255,255,0.1) 0%, transparent 60%);
    }
    .score-ring h1 {
        margin: 0;
        font-size: 4.5rem;
        font-weight: 800;
        position: relative;
        text-shadow: 0 4px 20px rgba(0,0,0,0.2);
    }
    .score-ring p {
        margin: 4px 0 0;
        font-size: 1.3rem;
        font-weight: 500;
        opacity: 0.9;
        position: relative;
    }

    /* ===== Status Pill ===== */
    .status-pill {
        display: inline-flex;
        align-items: center;
        gap: 6px;
        padding: 6px 14px;
        border-radius: 20px;
        font-size: 0.85rem;
        font-weight: 500;
    }
    .status-ok { background: rgba(34, 197, 94, 0.15); color: #4ade80; border: 1px solid rgba(34, 197, 94, 0.2); }
    .status-warn { background: rgba(245, 158, 11, 0.15); color: #fbbf24; border: 1px solid rgba(245, 158, 11, 0.2); }
    .status-err { background: rgba(239, 68, 68, 0.15); color: #f87171; border: 1px solid rgba(239, 68, 68, 0.2); }

    /* ===== Sidebar Brand ===== */
    .sidebar-brand {
        text-align: center;
        padding: 8px 0 4px;
    }
    .sidebar-brand h2 {
        background: linear-gradient(135deg, #818cf8, #c084fc);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        font-size: 1.6rem;
        font-weight: 800;
        margin: 0;
        letter-spacing: -0.02em;
    }
    .sidebar-brand p {
        color: #64748b;
        font-size: 0.75rem;
        margin: 2px 0 0;
        letter-spacing: 0.1em;
        text-transform: uppercase;
    }

    /* ===== Plotly Charts ===== */
    .js-plotly-plot .plotly .main-svg {
        border-radius: 12px;
    }

    /* ===== Workflow Steps ===== */
    .workflow-steps {
        display: flex;
        gap: 0;
        margin: 0 0 28px 0;
        padding: 0;
    }
    .wf-step {
        flex: 1;
        text-align: center;
        padding: 16px 8px;
        position: relative;
        cursor: default;
        transition: all 0.2s ease;
    }
    .wf-step::after {
        content: '';
        position: absolute;
        top: 50%;
        right: -12px;
        transform: translateY(-50%);
        width: 0; height: 0;
        border-top: 8px solid transparent;
        border-bottom: 8px solid transparent;
        border-left: 12px solid rgba(99,102,241,0.15);
        z-index: 1;
    }
    .wf-step:last-child::after { display: none; }
    .wf-step-done {
        background: rgba(34, 197, 94, 0.08);
        border-bottom: 3px solid #22c55e;
    }
    .wf-step-active {
        background: rgba(99, 102, 241, 0.1);
        border-bottom: 3px solid #6366f1;
    }
    .wf-step-pending {
        background: rgba(100, 116, 139, 0.05);
        border-bottom: 3px solid rgba(100, 116, 139, 0.15);
    }
    .wf-step .wf-icon {
        font-size: 1.5rem;
        margin-bottom: 4px;
    }
    .wf-step .wf-label {
        font-size: 0.78rem;
        font-weight: 500;
        color: #94a3b8;
    }
    .wf-step-done .wf-label { color: #4ade80; }
    .wf-step-active .wf-label { color: #818cf8; font-weight: 600; }

    /* ===== Guide Card ===== */
    .guide-card {
        background: linear-gradient(135deg, rgba(99,102,241,0.06) 0%, rgba(139,92,246,0.06) 100%);
        border: 1px solid rgba(99,102,241,0.15);
        border-radius: 16px;
        padding: 28px;
        margin-bottom: 16px;
        transition: all 0.25s ease;
    }
    .guide-card:hover {
        border-color: rgba(99,102,241,0.35);
        transform: translateY(-2px);
        box-shadow: 0 8px 30px rgba(99,102,241,0.1);
    }
    .guide-card h4 {
        margin: 0 0 8px 0;
        color: #e2e8f0;
        font-size: 1.1rem;
    }
    .guide-card p {
        margin: 0;
        color: #94a3b8;
        font-size: 0.9rem;
        line-height: 1.5;
    }
    .guide-card .guide-step-num {
        display: inline-flex;
        align-items: center;
        justify-content: center;
        width: 28px; height: 28px;
        border-radius: 50%;
        background: linear-gradient(135deg, #6366f1, #8b5cf6);
        color: white;
        font-weight: 700;
        font-size: 0.85rem;
        margin-right: 10px;
        flex-shrink: 0;
    }

    /* ===== Next Step Banner ===== */
    .next-step-banner {
        background: linear-gradient(135deg, rgba(99,102,241,0.08), rgba(139,92,246,0.08));
        border: 1px solid rgba(99,102,241,0.2);
        border-left: 4px solid #6366f1;
        border-radius: 0 12px 12px 0;
        padding: 16px 20px;
        margin: 24px 0 8px 0;
        display: flex;
        align-items: center;
        gap: 12px;
    }
    .next-step-banner .nst-icon { font-size: 1.3rem; }
    .next-step-banner .nst-text {
        color: #c7d2fe;
        font-size: 0.92rem;
        line-height: 1.5;
    }
    .next-step-banner .nst-text strong { color: #818cf8; }

    /* ===== Sidebar Progress ===== */
    .sidebar-progress {
        padding: 12px 16px;
        background: rgba(99,102,241,0.06);
        border-radius: 12px;
        margin: 8px 0;
    }
    .sidebar-progress .sp-title {
        font-size: 0.75rem;
        color: #64748b;
        text-transform: uppercase;
        letter-spacing: 0.08em;
        margin-bottom: 8px;
    }
    .sidebar-progress .sp-bar {
        height: 6px;
        background: rgba(100,116,139,0.2);
        border-radius: 3px;
        overflow: hidden;
        margin-bottom: 6px;
    }
    .sidebar-progress .sp-fill {
        height: 100%;
        border-radius: 3px;
        background: linear-gradient(90deg, #6366f1, #8b5cf6);
        transition: width 0.4s ease;
    }
    .sidebar-progress .sp-label {
        font-size: 0.72rem;
        color: #94a3b8;
    }
</style>
""", unsafe_allow_html=True)

# =========================================================================
# Plotly图表主题默认值
# =========================================================================

PLOTLY_LAYOUT = dict(
    paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor="rgba(0,0,0,0)",
    font=dict(family="Inter, sans-serif", color="#cbd5e1"),
    margin=dict(l=40, r=20, t=50, b=40),
    colorway=["#6366f1", "#8b5cf6", "#a78bfa", "#c084fc", "#e879f9",
              "#f472b6", "#fb7185", "#f87171", "#fbbf24", "#34d399"],
    xaxis=dict(gridcolor="rgba(99,102,241,0.08)"),
    yaxis=dict(gridcolor="rgba(99,102,241,0.08)"),
)


# =========================================================================
# 辅助函数
# =========================================================================

def load_json_file(path: str) -> dict | list | None:
    """加载JSON文件，出错时返回None。"""
    try:
        with open(path) as f:
            return json.load(f)
    except Exception as e:
        st.error(f"加载失败 {path}: {e}")
        return None


def tier_badge(tier: str) -> str:
    """返回等级对应的HTML徽章。"""
    css_class = {"hot": "hot-badge", "warm": "warm-badge", "cold": "cold-badge"}.get(tier, "cold-badge")
    return f'<span class="{css_class}">{tier.upper()}</span>'


def find_output_files() -> dict:
    """扫描/tmp和当前目录查找opengtm输出文件。"""
    files = {}
    patterns = {
        "discovered": "opengtm-discovered",
        "researched": "opengtm-researched",
        "qualified": "opengtm-qualified",
        "messages": "opengtm-messages",
        "pipeline": "opengtm-pipeline",
        "analytics": "opengtm-analytics",
        "mentions": "opengtm-mentions",
        "blog": "opengtm-blog",
        "keywords": "opengtm-keywords",
        "sitemap": "opengtm-sitemap",
        "context": "opengtm-context",
        "outreach": "opengtm-outreach",
    }

    search_dirs = [Path("/tmp"), PROJECT_ROOT, Path.cwd()]
    for d in search_dirs:
        if not d.exists():
            continue
        for f in d.glob("*.json"):
            for key, pattern in patterns.items():
                if pattern in f.name:
                    files[key] = str(f)

    return files


# =========================================================================
# 侧边栏
# =========================================================================

st.sidebar.markdown(
    '<div class="sidebar-brand"><h2>🚀 OpenGTM</h2><p>AI-Powered GTM Engine</p></div>',
    unsafe_allow_html=True,
)
st.sidebar.markdown("---")

# ---- 侧边栏：流程进度 ----
def _detect_progress():
    """检测已完成的流水线步骤。"""
    files = find_output_files()
    steps = {
        "discovered": bool(files.get("discovered") or st.session_state.get("discovered")),
        "researched": bool(files.get("researched") or st.session_state.get("researched_leads")),
        "qualified": bool(files.get("qualified") or files.get("pipeline") or st.session_state.get("qualified")),
        "messaged": bool(files.get("messages") or files.get("pipeline") or st.session_state.get("messaged")),
        "outreach": bool(files.get("outreach")),
    }
    return steps

_progress = _detect_progress()
_done_count = sum(_progress.values())
_total_steps = len(_progress)
_pct = int(_done_count / _total_steps * 100)

_step_labels = {
    "discovered": "发现公司",
    "researched": "调研域名",
    "qualified": "评分筛选",
    "messaged": "生成消息",
    "outreach": "触达序列",
}

st.sidebar.markdown(
    f'<div class="sidebar-progress">'
    f'<div class="sp-title">📍 流程进度</div>'
    f'<div class="sp-bar"><div class="sp-fill" style="width:{_pct}%"></div></div>'
    f'<div class="sp-label">{_done_count}/{_total_steps} 步已完成 · {_pct}%</div>'
    f'</div>',
    unsafe_allow_html=True,
)

# 显示步骤清单
_checklist_html = ""
for key, label in _step_labels.items():
    icon = "✅" if _progress[key] else "⬜"
    color = "#4ade80" if _progress[key] else "#475569"
    _checklist_html += f'<div style="font-size:0.82rem; color:{color}; padding:2px 0;">{icon} {label}</div>'
st.sidebar.markdown(_checklist_html, unsafe_allow_html=True)
st.sidebar.markdown("---")

page = st.sidebar.radio(
    "导航菜单",
    [
        "📊 总览面板",
        "🔍 发现与调研",
        "🎯 评分与筛选",
        "💬 消息与触达",
        "📝 博客生成",
        "🔑 SEO 关键词",
        "🏥 AEO 健康检查",
        "🗺️ 站点地图",
        "🔗 腾讯集成",
        "⚙️ 设置",
    ],
)

st.sidebar.markdown("---")
st.sidebar.markdown("### 📁 快速加载")
uploaded = st.sidebar.file_uploader("上传 JSON 输出文件", type=["json"])
st.sidebar.markdown("---")
st.sidebar.markdown(
    '<div style="text-align:center; padding: 8px 0;">'
    '<span style="color:#475569; font-size:0.72rem; letter-spacing:0.05em;">'
    'OpenGTM v1.0 · ✨ AI-Powered GTM</span></div>',
    unsafe_allow_html=True,
)
if uploaded:
    try:
        st.session_state["uploaded_data"] = json.load(uploaded)
        st.sidebar.success(f"已加载: {uploaded.name}")
    except Exception as e:
        st.sidebar.error(f"解析错误: {e}")


# =========================================================================
# 页面：总览面板
# =========================================================================

if page == "📊 总览面板":
    st.markdown(
        '<div class="hero-banner">'
        '<h1>📊 OpenGTM 总览面板</h1>'
        '<p>AI 驱动的 GTM 自动化引擎 — 一站式发现、调研、评分、触达潜在客户</p>'
        '</div>',
        unsafe_allow_html=True,
    )

    # 自动检测输出文件
    files = find_output_files()

    # ---- 流程进度条 ----
    def _render_workflow_bar(progress_dict):
        labels = [
            ("discovered", "🔍", "发现"),
            ("researched", "🔬", "调研"),
            ("qualified", "🎯", "评分"),
            ("messaged", "💬", "消息"),
            ("outreach", "📅", "触达"),
        ]
        # 找到第一个未完成的步骤
        first_pending = None
        for key, _, _ in labels:
            if not progress_dict.get(key):
                first_pending = key
                break

        html = '<div class="workflow-steps">'
        for key, icon, label in labels:
            if progress_dict.get(key):
                cls = "wf-step wf-step-done"
                display_icon = "✅"
            elif key == first_pending:
                cls = "wf-step wf-step-active"
                display_icon = icon
            else:
                cls = "wf-step wf-step-pending"
                display_icon = icon
            html += f'<div class="{cls}"><div class="wf-icon">{display_icon}</div><div class="wf-label">{label}</div></div>'
        html += '</div>'
        return html

    st.markdown(_render_workflow_bar(_progress), unsafe_allow_html=True)

    if not files and not any(st.session_state.get(k) for k in ["discovered", "researched", "qualified"]):
        # ---- 欢迎 / 快速入门指南 ----
        st.markdown(
            '<div style="text-align:center; padding: 20px 0 10px;">'
            '<span style="font-size:3rem;">👋</span>'
            '<h2 style="margin:8px 0 4px; color:#e2e8f0;">欢迎使用 OpenGTM</h2>'
            '<p style="color:#94a3b8; font-size:1rem; max-width:600px; margin:0 auto;">'
            'AI 驱动的 GTM 自动化引擎，帮你从零开始发现、调研、评分并触达潜在客户。<br>'
            '按照下方步骤开始你的第一次 GTM 流程。</p></div>',
            unsafe_allow_html=True,
        )

        st.markdown("")

        col1, col2 = st.columns(2)
        with col1:
            st.markdown(
                '<div class="guide-card">'
                '<h4><span class="guide-step-num">1</span>🔍 发现目标公司</h4>'
                '<p>输入行业和地区，AI 自动搜索并返回匹配的潜在客户列表。'
                '<br><br>👉 前往侧边栏 <strong>「发现与调研」</strong> 页面开始</p>'
                '</div>',
                unsafe_allow_html=True,
            )
            st.markdown(
                '<div class="guide-card">'
                '<h4><span class="guide-step-num">3</span>🎯 ICP 评分筛选</h4>'
                '<p>多维度智能评分（公司规模、行业匹配、数字化成熟度等），自动分为高/中/低意向。'
                '<br><br>👉 前往 <strong>「评分与筛选」</strong> 页面</p>'
                '</div>',
                unsafe_allow_html=True,
            )
            st.markdown(
                '<div class="guide-card">'
                '<h4><span class="guide-step-num">5</span>📅 触达序列管理</h4>'
'<p>管理多步骤触达序列，跟踪每个线索的触达进度，支持企业微信集成。'
                '<br><br>👉 前往 <strong>「消息与触达」</strong> 的序列 Tab</p>'
                '</div>',
                unsafe_allow_html=True,
            )
        with col2:
            st.markdown(
                '<div class="guide-card">'
                '<h4><span class="guide-step-num">2</span>🔬 深度调研</h4>'
                '<p>对每个目标域名进行深度调研：提取联系人、分析网站技术栈、发现痛点信号。'
                '<br><br>👉 在 <strong>「发现与调研」</strong> 的调研 Tab 中操作</p>'
                '</div>',
                unsafe_allow_html=True,
            )
            st.markdown(
                '<div class="guide-card">'
                '<h4><span class="guide-step-num">4</span>💬 生成触达消息</h4>'
                '<p>根据调研结果和评分，AI 自动生成个性化的 LinkedIn 连接请求、私信和跟进消息。'
                '<br><br>👉 前往 <strong>「消息与触达」</strong> 页面</p>'
                '</div>',
                unsafe_allow_html=True,
            )
            st.markdown(
                '<div class="guide-card">'
                '<h4>🛠️ 更多工具</h4>'
                '<p>'
                '• <strong>SEO 关键词</strong> — 7 阶段关键词研究<br>'
                '• <strong>博客生成</strong> — AI 原创文章<br>'
                '• <strong>AEO 健康检查</strong> — 29 项网站审计<br>'
                '• <strong>站点地图</strong> — 网站结构分析'
                '</p>'
                '</div>',
                unsafe_allow_html=True,
            )

        st.markdown("")
        st.markdown(
            '<div class="next-step-banner">'
            '<span class="nst-icon">🚀</span>'
            '<span class="nst-text">'
            '<strong>快速体验：</strong>也可以直接运行一键流水线命令，自动完成全部步骤：<br>'
            '<code>opengtm pipeline --industry "B2B SaaS" --region "Berlin" --limit 5</code>'
            '</span></div>',
            unsafe_allow_html=True,
        )
    else:
        if files:
            st.success(f"✅ 已找到 {len(files)} 个输出文件: {', '.join(files.keys())}")

    # 显示流水线数据（如有）
    pipeline_file = files.get("pipeline") or files.get("qualified") or files.get("messages")
    if pipeline_file:
        data = load_json_file(pipeline_file)
        if data and isinstance(data, list):
            st.markdown('<div class="section-header"><h3>📈 流水线概览</h3></div>', unsafe_allow_html=True)

            # 指标行
            total = len(data)
            hot = sum(1 for d in data if d.get("qualification", {}).get("tier") == "hot")
            warm = sum(1 for d in data if d.get("qualification", {}).get("tier") == "warm")
            cold = sum(1 for d in data if d.get("qualification", {}).get("tier") == "cold")
            avg_score = sum(d.get("qualification", {}).get("score", 0) for d in data) / max(total, 1)

            col1, col2, col3, col4, col5 = st.columns(5)
            col1.metric("线索总数", total)
            col2.metric("🔥 高意向", hot)
            col3.metric("🌤️ 中等", warm)
            col4.metric("❄️ 低意向", cold)
            col5.metric("平均分", f"{avg_score:.0f}")

            # 等级分布饼图
            col_chart1, col_chart2 = st.columns(2)

            with col_chart1:
                tier_data = pd.DataFrame({
                    "Tier": ["高意向 🔥", "中等 🌤️", "低意向 ❄️"],
                    "Count": [hot, warm, cold],
                })
                fig = px.pie(
                    tier_data, values="Count", names="Tier",
                    color="Tier",
                    color_discrete_map={"高意向 🔥": "#ff4b4b", "中等 🌤️": "#ffa726", "低意向 ❄️": "#42a5f5"},
                    title="ICP 分级分布",
                )
                fig.update_layout(height=350, **PLOTLY_LAYOUT)
                st.plotly_chart(fig, use_container_width=True)

            with col_chart2:
                # 评分分布直方图
                scores = [d.get("qualification", {}).get("score", 0) for d in data]
                fig = px.histogram(
                    x=scores, nbins=20,
                    title="ICP 评分分布",
                    labels={"x": "评分", "y": "数量"},
                    color_discrete_sequence=["#667eea"],
                )
                fig.update_layout(height=350, **PLOTLY_LAYOUT)
                st.plotly_chart(fig, use_container_width=True)

            # 线索列表
            st.markdown('<div class="section-header"><h3>📋 线索列表</h3></div>', unsafe_allow_html=True)
            table_data = []
            for d in data:
                qual = d.get("qualification", {})
                msgs = d.get("messages", {})
                table_data.append({
                    "公司": d.get("company", ""),
                    "域名": d.get("domain", ""),
                    "行业": d.get("industry", ""),
                    "评分": qual.get("score", 0),
                    "等级": qual.get("tier", "").upper(),
                    "模式": msgs.get("pattern", ""),
                    "联系人": d.get("contact_name", ""),
                    "建议操作": qual.get("recommended_action", ""),
                })
            df = pd.DataFrame(table_data)
            st.dataframe(
                df.style.apply(
                    lambda row: [
                        "background-color: #ffebee" if row["等级"] == "HOT"
                        else "background-color: #fff3e0" if row["等级"] == "WARM"
                        else "background-color: #e3f2fd"
                    ] * len(row),
                    axis=1,
                ),
                use_container_width=True,
                height=400,
            )

    # 显示分析数据（如有）
    analytics_file = files.get("analytics")
    if analytics_file:
        analytics = load_json_file(analytics_file)
        if analytics:
            st.markdown('<div class="section-header"><h3>🏥 最新健康检查</h3></div>', unsafe_allow_html=True)
            health = analytics.get("health", analytics)
            score = health.get("score", 0)
            grade = health.get("grade", "?")

            col1, col2 = st.columns([1, 3])
            with col1:
                color = "#22c55e" if score >= 80 else "#f59e0b" if score >= 60 else "#ef4444"
                st.markdown(
                    f'<div class="score-ring" style="background: linear-gradient(135deg, {color}, {color}dd);'
                    f' box-shadow: 0 4px 20px {color}30; padding: 20px;">'
                    f'<h1 style="font-size:3rem;">{grade}</h1>'
                    f'<p style="font-size:1.1rem;">{score}/100</p></div>',
                    unsafe_allow_html=True,
                )


# =========================================================================
# 页面：发现与调研
# =========================================================================

elif page == "🔍 发现与调研":
    st.markdown(
        '<div class="hero-banner">'
        '<h1>🔍 发现与调研</h1>'
        '<p>通过 AI 智能发现目标公司，深度调研域名与联系人</p>'
        '</div>',
        unsafe_allow_html=True,
    )

    tab1, tab2 = st.tabs(["🔍 发现公司", "🔬 调研域名"])

    with tab1:
        st.markdown(
            '<div class="next-step-banner">'
            '<span class="nst-icon">💡</span>'
            '<span class="nst-text">'
            '<strong>这一步做什么？</strong>输入目标行业和地区，AI 会自动搜索并返回匹配的潜在客户公司列表（含域名、行业等信息）。'
            '<br>发现完成后可 <strong>一键批量调研</strong> 所有公司，无需手动逐个操作。'
            '</span></div>',
            unsafe_allow_html=True,
        )
        col1, col2, col3 = st.columns(3)
        industry = col1.text_input("行业", "B2B SaaS", key="disc_industry")
        region = col2.text_input("地区", "Berlin", key="disc_region")
        limit = col3.number_input("数量上限", 5, 50, 10, key="disc_limit")

        if st.button("🚀 开始发现", key="btn_discover"):
            with st.spinner("正在发现公司..."):
                try:
                    from opengtm.discover import discover as _discover
                    results = _discover(industry=industry, region=region, limit=limit, verbose=False)
                    st.session_state["discovered"] = results
                    # 重新发现时清除下游数据
                    for k in ["researched_leads", "qualified", "messaged"]:
                        st.session_state.pop(k, None)
                    st.success(f"已找到 {len(results)} 家公司！")
                except Exception as e:
                    st.error(f"发现失败: {e}")

        if "discovered" in st.session_state:
            disc_data = st.session_state["discovered"]
            df = pd.DataFrame(disc_data)
            st.dataframe(df, use_container_width=True)

            # 导出
            json_str = json.dumps(disc_data, indent=2, ensure_ascii=False)
            st.download_button("📥 下载 JSON", json_str, "discovered.json", "application/json")

            st.markdown("---")

            # ---- 一键批量调研 ----
            st.markdown("#### 🔬 一键批量调研")
            st.markdown("对上方发现的所有公司自动进行深度调研（提取联系人、分析网站、发现痛点），结果将自动传递到下一步。")

            if st.button("🔬 批量调研全部公司", key="btn_batch_research"):
                from opengtm.research import research as _research
                researched_leads = []
                progress_bar = st.progress(0)
                status_text = st.empty()
                total = len(disc_data)
                for idx, lead in enumerate(disc_data):
                    status_text.text(f"正在调研 {lead['company']} ({lead['domain']})... ({idx+1}/{total})")
                    try:
                        res = _research(
                            domain=lead["domain"],
                            company=lead.get("company", lead["domain"]),
                            industry=lead.get("industry", ""),
                            verbose=False,
                        )
                        # 将调研结果合并到线索中
                        enriched = {
                            **lead,
                            "contact_name": res.get("contact", {}).get("name", ""),
                            "contact_title": res.get("contact", {}).get("title", ""),
                            "contact_email": res.get("contact", {}).get("email"),
                            "contact_linkedin": res.get("contact", {}).get("linkedin_url"),
                            "audit": res,  # 完整调研数据，用于评分/消息
                        }
                        researched_leads.append(enriched)
                    except Exception as e:
                        st.warning(f"调研 {lead['domain']} 失败: {e}")
                        researched_leads.append({**lead, "audit": {}})
                    progress_bar.progress((idx + 1) / total)
                status_text.empty()
                progress_bar.empty()
                st.session_state["researched_leads"] = researched_leads
                # 清除下游数据
                for k in ["qualified", "messaged"]:
                    st.session_state.pop(k, None)
                st.success(f"✅ 批量调研完成！{len(researched_leads)} 家公司已调研。")
                st.rerun()

            # 显示批量调研结果（如有）
            if "researched_leads" in st.session_state:
                r_leads = st.session_state["researched_leads"]
                st.markdown(f"#### ✅ 已调研 {len(r_leads)} 家公司")
                r_table = []
                for lead in r_leads:
                    r_table.append({
                        "公司": lead.get("company", ""),
                        "域名": lead.get("domain", ""),
                        "联系人": lead.get("contact_name", "无"),
                        "职位": lead.get("contact_title", "无"),
                        "邮箱": lead.get("contact_email") or "无",
                        "LinkedIn": "✅" if lead.get("contact_linkedin") else "❌",
                        "发现数": len(lead.get("audit", {}).get("findings", [])),
                    })
                st.dataframe(pd.DataFrame(r_table), use_container_width=True)

                st.markdown(
                    '<div class="next-step-banner">'
                    '<span class="nst-icon">👉</span>'
                    '<span class="nst-text">'
                    '<strong>下一步：</strong>前往侧边栏 <strong>「🎯 评分与筛选」</strong> 页面，数据已自动传递，一键即可完成 ICP 评分。'
                    '</span></div>',
                    unsafe_allow_html=True,
                )
            else:
                st.markdown(
                    '<div class="next-step-banner">'
                    '<span class="nst-icon">👉</span>'
                    '<span class="nst-text">'
                    '<strong>下一步：</strong>点击上方 <strong>「批量调研全部公司」</strong> 按钮，或切换到 <strong>「🔬 调研域名」</strong> Tab 逐个调研。'
                    '</span></div>',
                    unsafe_allow_html=True,
                )

    with tab2:
        st.markdown(
            '<div class="next-step-banner">'
            '<span class="nst-icon">💡</span>'
            '<span class="nst-text">'
            '<strong>单个域名调研：</strong>输入目标公司域名，AI 会深度调研：提取联系人（姓名/职位/邮箱/LinkedIn）、分析网站技术栈、发现业务痛点。'
            '<br>💡 如果你已在「发现」Tab 中发现了公司，推荐使用 <strong>一键批量调研</strong> 功能更高效。'
            '</span></div>',
            unsafe_allow_html=True,
        )

        # 从已发现公司中预填充（如有）
        disc_domains = []
        if "discovered" in st.session_state:
            disc_domains = [f"{d['company']} ({d['domain']})" for d in st.session_state["discovered"]]

        if disc_domains:
            selected = st.selectbox("从已发现公司中选择（或手动输入）", ["-- 手动输入 --"] + disc_domains, key="res_select")
            if selected != "-- 手动输入 --":
                # 解析选择
                sel_idx = disc_domains.index(selected)
                sel_lead = st.session_state["discovered"][sel_idx]
                default_domain = sel_lead["domain"]
                default_company = sel_lead["company"]
                default_industry = sel_lead.get("industry", "")
            else:
                default_domain = "example.com"
                default_company = ""
                default_industry = ""
        else:
            default_domain = "example.com"
            default_company = ""
            default_industry = ""

        col1, col2, col3 = st.columns(3)
        domain = col1.text_input("域名", default_domain, key="res_domain")
        company = col2.text_input("公司名称", default_company, key="res_company")
        industry_r = col3.text_input("行业", default_industry, key="res_industry")

        if st.button("🔬 开始调研", key="btn_research"):
            with st.spinner(f"正在调研 {domain}..."):
                try:
                    from opengtm.research import research as _research
                    result = _research(domain=domain, company=company or domain, industry=industry_r, verbose=False)
                    st.session_state["researched_single"] = result
                    st.success("调研完成！")
                except Exception as e:
                    st.error(f"调研失败: {e}")

        if "researched_single" in st.session_state:
            res = st.session_state["researched_single"]

            col1, col2 = st.columns(2)
            with col1:
                st.markdown("#### 👤 联系人")
                contact = res.get("contact", {})
                st.write(f"**姓名:** {contact.get('name', '无')}")
                st.write(f"**职位:** {contact.get('title', '无')}")
                st.write(f"**邮箱:** {contact.get('email', '无')}")
                st.write(f"**LinkedIn:** {contact.get('linkedin_url', '无')}")

            with col2:
                st.markdown("#### 📊 网站信息")
                st.write(f"**语言:** {res.get('site_language', '无')}")
                st.write(f"**有博客:** {'✅' if res.get('has_blog_or_news') else '❌'}")
                st.write(f"**社交链接:** {'✅' if res.get('has_social_links') else '❌'}")
                st.write(f"**综合评估:** {res.get('overall_assessment', '无')}")

            st.markdown("#### 🔍 发现")
            findings = res.get("findings", [])
            if findings:
                for f in findings:
                    sev = f.get("severity", "low")
                    icon = "🔴" if sev == "high" else "🟡" if sev == "medium" else "🟢"
                    st.markdown(f"{icon} **[{sev.upper()}]** {f.get('type', '')}: {f.get('detail', '')}")
            else:
                st.info("无发现（网站正常或审计失败）")


# =========================================================================
# 页面：评分与筛选
# =========================================================================

elif page == "🎯 评分与筛选":
    st.markdown(
        '<div class="hero-banner">'
        '<h1>🎯 ICP 资质评分与筛选</h1>'
        '<p>多维度智能评分，精准筛选高价值线索</p>'
        '</div>',
        unsafe_allow_html=True,
    )
    st.markdown(
        '<div class="next-step-banner">'
        '<span class="nst-icon">💡</span>'
        '<span class="nst-text">'
        '<strong>这一步做什么？</strong>上传已调研的线索 JSON，AI 会从 6 个维度（公司规模、行业匹配、数字化成熟度、痛点信号、营收信号、联系人质量）进行评分，自动分为 🔥高意向 / 🌤️中等 / ❄️低意向。'
        '<br>完成后前往 <strong>「💬 消息与触达」</strong> 页面生成个性化触达消息。'
        '</span></div>',
        unsafe_allow_html=True,
    )

    # ---- 从上一步自动加载数据 ----
    data = None

    # 优先级：session_state（来自上一步）> 上传文件 > 文件路径
    if "researched_leads" in st.session_state:
        data = st.session_state["researched_leads"]
        st.success(f"✅ 已自动加载上一步调研的 {len(data)} 条线索（来自「发现与调研」页面）")
    elif "qualified" in st.session_state:
        data = st.session_state["qualified"]
        st.success(f"✅ 已加载 {len(data)} 条已评分线索")
    else:
        # 回退：尝试查找输出文件
        files = find_output_files()
        auto_file = files.get("researched") or files.get("qualified") or files.get("pipeline")
        if auto_file:
            data = load_json_file(auto_file)
            if data:
                st.success(f"✅ 已自动加载文件: {auto_file}")

    if not data:
        st.markdown(
            '<div class="guide-card">'
            '<h4>📋 暂无线索数据</h4>'
            '<p>请先完成以下步骤之一：<br>'
            '• 前往 <strong>「🔍 发现与调研」</strong> 页面发现并调研公司（推荐）<br>'
            '• 通过侧边栏上传已调研的 JSON 文件<br>'
            '• 运行 CLI 命令：<code>opengtm pipeline --industry "B2B SaaS" --region "Berlin" --limit 5</code>'
            '</p></div>',
            unsafe_allow_html=True,
        )
        # 仍允许手动上传作为回退
        up = st.file_uploader("或手动上传线索 JSON", type=["json"], key="qual_upload")
        if up:
            data = json.load(up)

    if data and isinstance(data, list):
        st.success(f"已加载 {len(data)} 条线索")

        # 检查是否已评分
        already_qualified = any("qualification" in d for d in data)

        if not already_qualified:
            profile = st.selectbox("ICP 配置", ["default", "saas", "agency", "professional_services"])
            if st.button("🎯 全部评分"):
                with st.spinner("正在评分线索..."):
                    from opengtm.qualify import qualify_batch
                    data = qualify_batch(data, icp_profile=profile, verbose=False)
                    st.session_state["qualified"] = data
                    st.success("评分完成！")
        else:
            st.session_state["qualified"] = data

        if "qualified" in st.session_state:
            qdata = st.session_state["qualified"]

            # 评分细分雷达图
            st.markdown('<div class="section-header"><h3>📊 评分分析</h3></div>', unsafe_allow_html=True)

            col1, col2 = st.columns(2)
            with col1:
                # 等级分布
                tiers = [d.get("qualification", {}).get("tier", "cold") for d in qdata]
                tier_counts = pd.Series(tiers).value_counts()
                fig = px.pie(
                    values=tier_counts.values,
                    names=[t.upper() for t in tier_counts.index],
                    color=tier_counts.index,
                    color_discrete_map={"hot": "#ff4b4b", "warm": "#ffa726", "cold": "#42a5f5"},
                    title="分级分布",
                )
                fig.update_layout(**PLOTLY_LAYOUT)
                st.plotly_chart(fig, use_container_width=True)

            with col2:
                # 平均评分细分雷达
                dims = ["company_size", "industry_fit", "digital_maturity", "pain_signals", "revenue_signals", "contact_quality"]
                dim_labels = ["公司规模", "行业匹配", "数字化成熟度", "痛点信号", "营收信号", "联系人质量"]
                dim_max = [20, 25, 15, 20, 10, 10]

                avg_vals = []
                for dim, mx in zip(dims, dim_max):
                    vals = [d.get("qualification", {}).get("breakdown", {}).get(dim, 0) for d in qdata]
                    avg = sum(vals) / max(len(vals), 1)
avg_vals.append(avg / mx * 100)  # 归一化为百分比

                fig = go.Figure(data=go.Scatterpolar(
                    r=avg_vals + [avg_vals[0]],
                    theta=dim_labels + [dim_labels[0]],
                    fill="toself",
                    fillcolor="rgba(102, 126, 234, 0.3)",
                    line=dict(color="#667eea"),
                ))
                fig.update_layout(
                    polar=dict(radialaxis=dict(visible=True, range=[0, 100])),
                    title="平均评分细分（占最高分百分比）",
                    height=400,
                    **PLOTLY_LAYOUT,
                )
                st.plotly_chart(fig, use_container_width=True)

            # 详细表格
            st.markdown('<div class="section-header"><h3>📋 已评分线索</h3></div>', unsafe_allow_html=True)
            table = []
            for d in qdata:
                q = d.get("qualification", {})
                table.append({
                    "公司": d.get("company", ""),
                    "域名": d.get("domain", ""),
                    "评分": q.get("score", 0),
                    "等级": q.get("tier", "").upper(),
                    "规模": q.get("breakdown", {}).get("company_size", 0),
                    "行业": q.get("breakdown", {}).get("industry_fit", 0),
                    "成熟度": q.get("breakdown", {}).get("digital_maturity", 0),
                    "痛点": q.get("breakdown", {}).get("pain_signals", 0),
                    "营收": q.get("breakdown", {}).get("revenue_signals", 0),
                    "联系人": q.get("breakdown", {}).get("contact_quality", 0),
                    "建议操作": q.get("recommended_action", ""),
                })
            df = pd.DataFrame(table).sort_values("评分", ascending=False)
            st.dataframe(df, use_container_width=True, height=400)

            # 导出
            json_str = json.dumps(qdata, indent=2, ensure_ascii=False)
            st.download_button("📥 下载评分结果 JSON", json_str, "qualified.json", "application/json")

            st.markdown(
                '<div class="next-step-banner">'
                '<span class="nst-icon">👉</span>'
                '<span class="nst-text">'
                '<strong>下一步：</strong>前往侧边栏 <strong>「💬 消息与触达」</strong> 页面，数据已自动传递，一键即可生成个性化触达消息。'
                '</span></div>',
                unsafe_allow_html=True,
            )


# =========================================================================
# 页面：消息与触达
# =========================================================================

elif page == "💬 消息与触达":
    st.markdown(
        '<div class="hero-banner">'
        '<h1>💬 消息与触达序列</h1>'
        '<p>智能生成个性化触达消息，管理多步骤序列</p>'
        '</div>',
        unsafe_allow_html=True,
    )

    st.markdown(
        '<div class="next-step-banner">'
        '<span class="nst-icon">💡</span>'
        '<span class="nst-text">'
        '<strong>这一步做什么？</strong>基于已评分的线索，AI 自动生成个性化的 LinkedIn 连接请求、首次私信和跟进消息。'
        '<br>数据从上一步自动传递，无需手动上传。生成后可在 <strong>「触达序列」</strong> Tab 中管理触达计划。'
        '</span></div>',
        unsafe_allow_html=True,
    )

    tab1, tab2 = st.tabs(["📨 消息生成与预览", "📅 触达序列"])

    with tab1:
        # ---- 从上一步自动加载数据 ----
        msg_data = None
        source_leads = None  # 需要生成消息的线索

        if "messaged" in st.session_state:
            msg_data = st.session_state["messaged"]
            st.success(f"✅ 已加载 {len(msg_data)} 条带消息的线索")
        elif "qualified" in st.session_state:
            source_leads = st.session_state["qualified"]
            # 检查消息是否已存在
            if all("messages" in lead for lead in source_leads):
                msg_data = source_leads
                st.session_state["messaged"] = msg_data
                st.success(f"✅ 已加载 {len(msg_data)} 条带消息的线索（来自评分步骤）")
            else:
                st.info(f"📋 已加载 {len(source_leads)} 条已评分线索，点击下方按钮一键生成消息。")
        else:
            # 尝试查找输出文件
            files = find_output_files()
            auto_file = files.get("messages") or files.get("pipeline")
            if auto_file:
                msg_data = load_json_file(auto_file)
                if msg_data:
                    st.session_state["messaged"] = msg_data
                    st.success(f"✅ 已自动加载文件: {auto_file}")

        if not msg_data and not source_leads:
            st.markdown(
                '<div class="guide-card">'
                '<h4>📋 暂无线索数据</h4>'
                '<p>请先完成以下步骤：<br>'
                '• 前往 <strong>「🔍 发现与调研」</strong> 发现并调研公司<br>'
                '• 前往 <strong>「🎯 评分与筛选」</strong> 完成 ICP 评分<br>'
                '• 数据会自动传递到此页面</p></div>',
                unsafe_allow_html=True,
            )
            # 回退手动上传
            up = st.file_uploader("或手动上传线索 JSON", type=["json"], key="msg_upload")
            if up:
                loaded = json.load(up)
                if all("messages" in d for d in loaded):
                    msg_data = loaded
                else:
                    source_leads = loaded

        # ---- 一键消息生成 ----
        if source_leads and not msg_data:
            if st.button("💬 一键生成全部消息", key="btn_gen_messages"):
                from opengtm.message import generate_messages
                results = []
                progress_bar = st.progress(0)
                status_text = st.empty()
                total = len(source_leads)
                patterns = {}
                for idx, lead in enumerate(source_leads):
                    status_text.text(f"正在为 {lead.get('company', lead.get('domain', '?'))} 生成消息... ({idx+1}/{total})")
                    audit = lead.get("audit") or lead.get("research") or {}
                    if isinstance(audit, dict) and "research" in audit:
                        audit = audit["research"]
                    messages = generate_messages(
                        domain=lead.get("domain", ""),
                        company=lead.get("company", ""),
                        contact_name=lead.get("contact_name", ""),
                        industry=lead.get("industry", ""),
                        audit=audit,
                        region=lead.get("region", ""),
                        contact_title=lead.get("contact_title", ""),
                    )
                    results.append({**lead, "messages": messages})
                    p = messages["pattern"]
                    patterns[p] = patterns.get(p, 0) + 1
                    progress_bar.progress((idx + 1) / total)
                status_text.empty()
                progress_bar.empty()
                st.session_state["messaged"] = results
                msg_data = results
                st.success(f"✅ 消息生成完成！模式分布: {dict(sorted(patterns.items()))}")
                st.rerun()

        if msg_data and isinstance(msg_data, list):
            st.success(f"已加载 {len(msg_data)} 条带消息的线索")

            # 模式分布
            patterns = [d.get("messages", {}).get("pattern", "?") for d in msg_data]
            pattern_counts = pd.Series(patterns).value_counts()
            fig = px.bar(
                x=pattern_counts.index, y=pattern_counts.values,
                title="消息模式分布",
                labels={"x": "模式", "y": "数量"},
                color=pattern_counts.index,
            )
            st.plotly_chart(fig, use_container_width=True)

            # 每条线索的消息预览
            st.markdown('<div class="section-header"><h3>📨 消息预览</h3></div>', unsafe_allow_html=True)
            for i, lead in enumerate(msg_data):
                msgs = lead.get("messages", {})
                company = lead.get("company", lead.get("domain", f"线索 {i+1}"))
                tier = lead.get("qualification", {}).get("tier", "")

                with st.expander(f"{'🔥' if tier == 'hot' else '🌤️' if tier == 'warm' else '❄️'} {company} — 模式 {msgs.get('pattern', '?')}"):
                    st.markdown(f"**模式:** {msgs.get('pattern', '无')} — {msgs.get('pattern_reason', '')}")
                    st.markdown("---")

                    st.markdown("**🤝 连接请求 (第1次触达):**")
                    st.code(msgs.get("connection_note", "无"), language=None)

                    st.markdown("**💬 首次私信 (第2次触达):**")
                    st.code(msgs.get("first_dm", "无"), language=None)

                    st.markdown("**📩 跟进 1 (第3次触达):**")
                    st.code(msgs.get("followup", "无"), language=None)

                    st.markdown("**📩 跟进 2 (第4次触达):**")
                    st.code(msgs.get("followup_2", "无"), language=None)

                    if msgs.get("alternatives"):
                        st.markdown("**🔄 备选模式:**")
                        for alt in msgs["alternatives"]:
                            st.markdown(f"- **{alt['pattern']}**: {alt.get('reason', '')}")

    with tab2:
        st.markdown('<div class="section-header"><h3>📅 触达序列管理</h3></div>', unsafe_allow_html=True)

        state_file = st.text_input("状态文件路径", "/tmp/opengtm-outreach-state.json", key="outreach_state")

        if Path(state_file).exists():
            from opengtm.outreach import OutreachSequence
            seq = OutreachSequence.load(state_file)
            stats = seq.get_stats()

            col1, col2, col3, col4 = st.columns(4)
            col1.metric("线索总数", stats["total_leads"])
            col2.metric("今日待处理", stats["due_today"])
            col3.metric("剩余容量", stats["daily_capacity_remaining"])
            col4.metric("已完成", stats["status_breakdown"].get("completed", 0))

            # 状态细分
            status_df = pd.DataFrame([
                {"状态": k.title(), "数量": v}
                for k, v in stats["status_breakdown"].items()
            ])
            fig = px.bar(status_df, x="状态", y="数量", title="序列状态", color="状态")
            fig.update_layout(**PLOTLY_LAYOUT)
            st.plotly_chart(fig, use_container_width=True)

            # 今日待处理队列
            due = seq.get_due_today()
            if due:
                st.markdown('<div class="section-header"><h3>📋 今日待处理</h3></div>', unsafe_allow_html=True)
                for item in due:
                    touch = item.get("next_touch", "?")
                    msg = seq.get_touch_message(item["domain"], touch)
                    st.markdown(
                        f"**{item['company']}** ({item['domain']}) — "
                        f"第 {touch} 次触达 | {item.get('tier', '').upper()} | 评分: {item.get('score', '无')}"
                    )
                    st.code(msg[:200] + "..." if len(msg) > 200 else msg, language=None)
        else:
            st.markdown(
                '<div class="guide-card">'
                '<h4>📅 还没有触达序列？</h4>'
                '<p>触达序列帮你管理多步骤的客户触达计划（连接请求 → 首次私信 → 跟进1 → 跟进2），自动跟踪进度。'
                '<br><br><strong>如何开始：</strong><br>'
                '1. 先在左侧 <strong>「消息生成与预览」</strong> Tab 中生成消息<br>'
                '2. 然后通过 CLI 加载线索到序列：<br>'
                '<code>opengtm outreach load --input /tmp/opengtm-messages.json</code>'
                '</p></div>',
                unsafe_allow_html=True,
            )

            # 自动保存消息数据供CLI使用
            if "messaged" in st.session_state:
                save_path = "/tmp/opengtm-messages.json"
                try:
                    with open(save_path, "w") as f:
                        json.dump(st.session_state["messaged"], f, indent=2, ensure_ascii=False)
                    st.info(f"💡 消息数据已自动保存到 `{save_path}`，可直接运行：\n\n`opengtm outreach load --input {save_path}`")
                except Exception:
                    pass


# =========================================================================
# 页面：博客生成器
# =========================================================================

elif page == "📝 博客生成":
    st.markdown(
        '<div class="hero-banner">'
        '<h1>📝 AI 博客生成器</h1>'
        '<p>基于 SEO 研究自动生成高质量原创文章</p>'
        '</div>',
        unsafe_allow_html=True,
    )

    st.markdown(
        '<div class="next-step-banner">'
        '<span class="nst-icon">💡</span>'
        '<span class="nst-text">'
        '<strong>这个工具做什么？</strong>输入域名和 SEO 关键词，AI 会先研究竞品内容，然后生成一篇高质量原创文章（含 HTML 格式、参考来源、相似度检测）。'
        '</span></div>',
        unsafe_allow_html=True,
    )

    tab1, tab2 = st.tabs(["✍️ 生成", "👁️ 预览"])

    with tab1:
        col1, col2 = st.columns(2)
        domain = col1.text_input("域名", "example.com", key="blog_domain")
        keyword = col2.text_input("SEO 关键词", "best practices for SaaS onboarding", key="blog_keyword")

        col3, col4, col5 = st.columns(3)
        word_count = col3.number_input("字数", 500, 5000, 2000, key="blog_wc")
        language = col4.selectbox("语言", ["en", "de"], key="blog_lang")
        country = col5.text_input("国家", "United States", key="blog_country")

        if st.button("✍️ 生成文章", key="btn_blog"):
            with st.spinner("正在生成文章（可能需要 1-2 分钟）..."):
                try:
                    from opengtm.blog import generate_article
                    result = generate_article(
                        domain=domain, keyword=keyword,
                        word_count=word_count, language=language, country=country,
                    )
                    st.session_state["blog_result"] = result
                    st.success(f"文章已生成: {result.get('title', '')}")
                except Exception as e:
                    st.error(f"生成失败: {e}")

    with tab2:
        # 从文件或会话加载
        blog = st.session_state.get("blog_result")
        if not blog:
            up = st.file_uploader("上传博客 JSON", type=["json"], key="blog_upload")
            if up:
                blog = json.load(up)

        if blog:
            st.markdown(f"## {blog.get('title', '无标题')}")
            st.markdown(f"*{blog.get('meta_description', '')}*")

            col1, col2, col3, col4 = st.columns(4)
            col1.metric("字数", blog.get("word_count", 0))
            col2.metric("来源", len(blog.get("sources", [])))
            col3.metric("相似度", f"{blog.get('similarity_score', 0):.1%}")
            col4.metric("已验证链接", blog.get("urls_verified", 0))

            if blog.get("is_too_similar"):
                st.warning("⚠️ 检测到高度内容相似 — 可能存在内容自竞争风险！")

            st.markdown("---")
            st.markdown(blog.get("content_html", ""), unsafe_allow_html=True)

            if blog.get("sources"):
                st.markdown("### 📚 参考来源")
                for src in blog["sources"]:
                    st.markdown(f"- [{src.get('title', '来源')}]({src.get('url', '#')}) — {src.get('description', '')}")

            # 导出
            json_str = json.dumps(blog, indent=2, ensure_ascii=False)
            st.download_button("📥 下载博客 JSON", json_str, "blog.json", "application/json")

            # 导出为HTML
            html_content = f"""<!DOCTYPE html>
<html><head><meta charset="utf-8"><title>{blog.get('title', '')}</title>
<meta name="description" content="{blog.get('meta_description', '')}">
<style>body{{max-width:800px;margin:0 auto;padding:20px;font-family:system-ui;line-height:1.6;}}</style>
</head><body>{blog.get('content_html', '')}</body></html>"""
            st.download_button("📥 下载 HTML", html_content, "blog.html", "text/html")


# =========================================================================
# 页面：SEO关键词
# =========================================================================

elif page == "🔑 SEO 关键词":
    st.markdown(
        '<div class="hero-banner">'
        '<h1>🔑 SEO 关键词研究</h1>'
        '<p>7 阶段流水线深度分析，发现高价值关键词机会</p>'
        '</div>',
        unsafe_allow_html=True,
    )

    st.markdown(
        '<div class="next-step-banner">'
        '<span class="nst-icon">💡</span>'
        '<span class="nst-text">'
        '<strong>这个工具做什么？</strong>输入域名，AI 通过 7 阶段流水线（种子词生成 → 扩展 → 聚类 → 意图分析 → 评分 → 内容摘要 → 排序）深度分析关键词机会。'
        '</span></div>',
        unsafe_allow_html=True,
    )

    tab1, tab2 = st.tabs(["🔍 研究", "📊 分析"])

    with tab1:
        col1, col2, col3 = st.columns(3)
        domain = col1.text_input("域名", "example.com", key="kw_domain")
        limit = col2.number_input("最大关键词数", 10, 100, 30, key="kw_limit")
        language = col3.selectbox("语言", ["en", "de"], key="kw_lang")

        if st.button("🔍 研究关键词", key="btn_kw"):
            with st.spinner("正在研究关键词（7 阶段流水线，可能需要几分钟）..."):
                try:
                    from opengtm.keywords import research_keywords
                    results = research_keywords(domain=domain, limit=limit, language=language)
                    st.session_state["keywords"] = results
                    st.success(f"已找到 {len(results)} 个关键词！")
                except Exception as e:
                    st.error(f"关键词研究失败: {e}")

    with tab2:
        kw_data = st.session_state.get("keywords")
        if not kw_data:
            up = st.file_uploader("上传关键词 JSON", type=["json"], key="kw_upload")
            if up:
                kw_data = json.load(up)

        if kw_data and isinstance(kw_data, list):
            st.success(f"正在分析 {len(kw_data)} 个关键词")

            # 聚类分布
            clusters = [kw.get("cluster", "Other") for kw in kw_data]
            cluster_counts = pd.Series(clusters).value_counts()
            fig = px.bar(
                x=cluster_counts.index, y=cluster_counts.values,
                title="关键词聚类",
                labels={"x": "聚类", "y": "数量"},
                color=cluster_counts.index,
            )
            st.plotly_chart(fig, use_container_width=True)

            # 评分散点图
            scatter_data = pd.DataFrame([{
                "Keyword": kw.get("keyword", ""),
                "Score": kw.get("score", 0),
                "Cluster": kw.get("cluster", "Other"),
            } for kw in kw_data])

            if not scatter_data.empty:
                fig = px.scatter(
                    scatter_data, x="Score", y="Keyword",
                    color="Cluster", title="关键词评分",
                    height=max(400, len(kw_data) * 25),
                )
                fig.update_layout(**PLOTLY_LAYOUT)
                st.plotly_chart(fig, use_container_width=True)

            # 关键词表格
            st.markdown('<div class="section-header"><h3>📋 全部关键词</h3></div>', unsafe_allow_html=True)
            table = []
            for kw in kw_data:
                brief = kw.get("content_brief", {})
                table.append({
                    "关键词": kw.get("keyword", ""),
                    "评分": kw.get("score", 0),
                    "聚类": kw.get("cluster", ""),
                    "意图": kw.get("search_intent", ""),
                    "有摘要": "✅" if brief else "❌",
                })
            df = pd.DataFrame(table).sort_values("评分", ascending=False)
            st.dataframe(df, use_container_width=True)

            # 导出
            json_str = json.dumps(kw_data, indent=2, ensure_ascii=False)
            st.download_button("📥 下载关键词 JSON", json_str, "keywords.json", "application/json")


# =========================================================================
# 页面：AEO健康检查
# =========================================================================

elif page == "🏥 AEO 健康检查":
    st.markdown(
        '<div class="hero-banner">'
        '<h1>🏥 AEO / SEO 健康检查</h1>'
        '<p>29 项技术审计 — SEO、结构化数据、AI 爬虫访问、权威信号</p>'
        '</div>',
        unsafe_allow_html=True,
    )

    st.markdown(
        '<div class="next-step-banner">'
        '<span class="nst-icon">💡</span>'
        '<span class="nst-text">'
        '<strong>这个工具做什么？</strong>输入网站 URL，自动运行 29 项技术审计（SEO 基础、结构化数据、AI 爬虫可访问性、权威信号等），给出评分和改进建议。'
        '</span></div>',
        unsafe_allow_html=True,
    )

    url = st.text_input("网站 URL", "https://example.com", key="aeo_url")

    col1, col2 = st.columns(2)
    run_health = col1.button("🏥 运行健康检查", key="btn_health")
    run_mentions = col2.button("🔍 运行 AI 可见度检查", key="btn_mentions")

    if run_health:
        with st.spinner("正在运行 29 项健康检查..."):
            try:
                from opengtm.analytics import run_health_check
                result = run_health_check(url)
                st.session_state["health_result"] = result
                st.success(f"评分: {result.get('score', 0)} | 等级: {result.get('grade', '?')}")
            except Exception as e:
                st.error(f"健康检查失败: {e}")

    # 从文件加载
    if not st.session_state.get("health_result"):
        up = st.file_uploader("或上传分析 JSON", type=["json"], key="aeo_upload")
        if up:
            data = json.load(up)
            st.session_state["health_result"] = data.get("health", data)

    health = st.session_state.get("health_result")
    if health:
        # 评分展示
        score = health.get("score", 0)
        grade = health.get("grade", "?")

        col1, col2, col3 = st.columns([1, 1, 2])
        with col1:
            color = "#22c55e" if score >= 80 else "#f59e0b" if score >= 60 else "#ef4444"
            st.markdown(
                f'<div class="score-ring" style="background: linear-gradient(135deg, {color}, {color}dd);'
                f' box-shadow: 0 8px 40px {color}40;">'
                f'<h1>{grade}</h1>'
                f'<p>{score} / 100</p></div>',
                unsafe_allow_html=True,
            )

        with col2:
            # 分类评分
            categories = health.get("category_scores", {})
            if categories:
                for cat, cat_score in categories.items():
                    st.metric(cat.replace("_", " ").title(), f"{cat_score}%")

        with col3:
                # 按严重程度分类的发现
                findings = health.get("findings", [])
                if findings:
                    sev_counts = {"pass": 0, "warning": 0, "fail": 0}
                    for f in findings:
                        status = f.get("status", "").lower()
                        if status in sev_counts:
                            sev_counts[status] += 1

                    fig = px.bar(
                        x=list(sev_counts.keys()), y=list(sev_counts.values()),
                        title="检查结果",
                        color=list(sev_counts.keys()),
                        color_discrete_map={"pass": "#4caf50", "warning": "#ff9800", "fail": "#f44336"},
                    )
                st.plotly_chart(fig, use_container_width=True)

        # 详细发现
        st.markdown('<div class="section-header"><h3>🔍 详细发现</h3></div>', unsafe_allow_html=True)
        findings = health.get("findings", [])
        for f in findings:
            status = f.get("status", "").lower()
            icon = "✅" if status == "pass" else "⚠️" if status == "warning" else "❌"
            with st.expander(f"{icon} {f.get('check', f.get('type', '检查'))} — {status.upper()}"):
                st.write(f.get("detail", ""))
                if f.get("recommendation"):
                    st.info(f"💡 {f['recommendation']}")


# =========================================================================
# 页面：站点地图浏览器
# =========================================================================

elif page == "🗺️ 站点地图":
    st.markdown(
        '<div class="hero-banner">'
        '<h1>🗺️ 站点地图浏览器</h1>'
        '<p>爬取并分析网站结构，可视化 URL 分类分布</p>'
        '</div>',
        unsafe_allow_html=True,
    )

    st.markdown(
        '<div class="next-step-banner">'
        '<span class="nst-icon">💡</span>'
        '<span class="nst-text">'
        '<strong>这个工具做什么？</strong>输入网站 URL，自动爬取站点地图并分析 URL 结构，按类型（博客/产品/文档/服务等）分类统计，帮你快速了解目标网站的内容布局。'
        '</span></div>',
        unsafe_allow_html=True,
    )

    url = st.text_input("网站 URL", "https://example.com", key="sm_url")

    if st.button("🗺️ 爬取站点地图", key="btn_sitemap"):
        with st.spinner("正在爬取站点地图..."):
            try:
                from opengtm.sitemap import crawl_sitemap
                result = crawl_sitemap(url)
                st.session_state["sitemap_result"] = result
                st.success(f"已找到 {result.get('total_pages', 0)} 个页面！")
            except Exception as e:
                st.error(f"站点地图爬取失败: {e}")

    # 从文件加载
    if not st.session_state.get("sitemap_result"):
        up = st.file_uploader("或上传站点地图 JSON", type=["json"], key="sm_upload")
        if up:
            st.session_state["sitemap_result"] = json.load(up)

    sm = st.session_state.get("sitemap_result")
    if sm:
        st.metric("总页面数", sm.get("total_pages", 0))

        # 分类分布
        categories = {
            "博客": len(sm.get("blog_urls", [])),
            "产品": len(sm.get("product_urls", [])),
            "服务": len(sm.get("service_urls", [])),
            "文档": len(sm.get("docs_urls", [])),
            "资源": len(sm.get("resource_urls", [])),
            "公司": len(sm.get("company_urls", [])),
            "法律": len(sm.get("legal_urls", [])),
            "联系": len(sm.get("contact_urls", [])),
            "落地页": len(sm.get("landing_urls", [])),
            "其他": len(sm.get("other_urls", [])),
        }

        fig = px.pie(
            values=list(categories.values()),
            names=list(categories.keys()),
            title="URL 分类",
        )
        fig.update_layout(**PLOTLY_LAYOUT)
        st.plotly_chart(fig, use_container_width=True)

        # 按分类显示URL
        cat_key_map = {
            "博客": "blog_urls", "产品": "product_urls", "服务": "service_urls",
            "文档": "docs_urls", "资源": "resource_urls", "公司": "company_urls",
            "法律": "legal_urls", "联系": "contact_urls", "落地页": "landing_urls",
            "其他": "other_urls",
        }
        for cat, count in categories.items():
            if count > 0:
                key = cat_key_map.get(cat, f"{cat}_urls")
                urls = sm.get(key, [])
                with st.expander(f"📁 {cat}（{count} 个 URL）"):
                    for u in urls[:50]:
                        st.markdown(f"- [{u}]({u})")
                    if count > 50:
                        st.info(f"... 还有 {count - 50} 个")


# =========================================================================
# 页面：腾讯集成
# =========================================================================

elif page == "🔗 腾讯集成":
    st.markdown(
        '<div class="hero-banner">'
        '<h1>🔗 腾讯企业微信集成</h1>'
        '<p>连接企业微信机器人和腾讯文档，实现自动化工作流</p>'
        '</div>',
        unsafe_allow_html=True,
    )

    # 检查状态
    wecom_key = os.environ.get("WECOM_BOT_KEY", "")
    wecom_configured = bool(wecom_key)

    # 状态指示器
    col1, col2 = st.columns(2)
    ok_cls = "status-pill status-ok"
    err_cls = "status-pill status-err"
    col1.markdown(f'<span class="{ok_cls if wecom_configured else err_cls}">{"✅ 企业微信机器人已配置" if wecom_configured else "❌ 企业微信机器人未配置"}</span>', unsafe_allow_html=True)
    api_key = os.environ.get("TENCENT_API_KEY", "") or os.environ.get("OPENAI_API_KEY", "")
    col2.markdown(f'<span class="{ok_cls if api_key else err_cls}">{"✅ API密钥已配置" if api_key else "❌ API密钥未配置"}</span>', unsafe_allow_html=True)

    if not wecom_configured:
        st.warning(
            "⚠️ 企业微信机器人未配置。\n\n"
            "**设置步骤：**\n"
            "1. 在企业微信群中添加群机器人\n"
            "2. 复制机器人的 Webhook Key\n"
            "3. 在 `.env` 文件中设置 `WECOM_BOT_KEY=你的Key`\n"
            "4. 或设置 `CRM_WEBHOOK_URL=完整的Webhook地址`"
        )

    tab1, tab2 = st.tabs(["💬 企业微信推送", "📊 数据同步"])

    with tab1:
        st.markdown("### 💬 推送线索到企业微信群")
        st.markdown("将线索信息通过企业微信机器人推送到群聊。")

        # 从session_state自动加载
        leads = st.session_state.get("messaged") or st.session_state.get("qualified")
        if leads:
            st.success(f"✅ 已自动加载 {len(leads)} 条线索")
        else:
            up = st.file_uploader("上传线索 JSON", type=["json"], key="wecom_upload")
            if up:
                leads = json.load(up)
                st.success(f"已加载 {len(leads)} 条线索")

        if leads:
            if st.button("💬 推送到企业微信", key="btn_wecom"):
                with st.spinner("正在推送到企业微信..."):
                    try:
                        from opengtm.sync import sync_to_crm
                        results = sync_to_crm(leads)
                        success_count = sum(1 for r in results if r.get("success"))
                        st.success(f"✅ 成功推送 {success_count}/{len(results)} 条线索！")
                    except Exception as e:
                        st.error(f"推送失败: {e}")

    with tab2:
        st.markdown("### 📊 数据导出")
        st.markdown("将线索数据导出为CSV文件，可导入腾讯文档或其他系统。")

        export_leads = st.session_state.get("messaged") or st.session_state.get("qualified") or st.session_state.get("researched_leads")
        if export_leads:
            st.success(f"✅ 已自动加载 {len(export_leads)} 条线索")
            if st.button("📥 导出CSV", key="btn_export_csv"):
                df = pd.DataFrame(export_leads)
                csv = df.to_csv(index=False).encode("utf-8-sig")
                st.download_button(
                    label="📥 下载CSV文件",
                    data=csv,
                    file_name=f"opengtm_leads_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                    mime="text/csv",
                    key="download_csv",
                )
        else:
            up = st.file_uploader("上传线索 JSON", type=["json"], key="export_upload")
            if up:
                export_leads = json.load(up)
                df = pd.DataFrame(export_leads)
                csv = df.to_csv(index=False).encode("utf-8-sig")
                st.download_button(
                    label="📥 下载CSV文件",
                    data=csv,
                    file_name=f"opengtm_leads_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                    mime="text/csv",
                    key="download_csv2",
                )


# =========================================================================
# 页面：设置
# =========================================================================

elif page == "⚙️ 设置":
    st.markdown(
        '<div class="hero-banner">'
        '<h1>⚙️ 设置</h1>'
        '<p>管理 API 配置、输出文件和集成状态</p>'
        '</div>',
        unsafe_allow_html=True,
    )

    st.markdown('<div class="section-header"><h3>🔑 API 配置</h3></div>', unsafe_allow_html=True)
    st.markdown("当前 `.env` 文件中的设置：")

    env_vars = {
        "OPENAI_API_KEY": os.environ.get("OPENAI_API_KEY", ""),
        "OPENAI_BASE_URL": os.environ.get("OPENAI_BASE_URL", ""),
        "TENCENT_API_KEY": os.environ.get("TENCENT_API_KEY", ""),
        "CRM_WEBHOOK_URL": os.environ.get("CRM_WEBHOOK_URL", ""),
        "WECOM_BOT_KEY": os.environ.get("WECOM_BOT_KEY", ""),
        "DEFAULT_LANGUAGE": os.environ.get("DEFAULT_LANGUAGE", "zh"),
        "DEFAULT_DAILY_LIMIT": os.environ.get("DEFAULT_DAILY_LIMIT", "20"),
    }

    for key, val in env_vars.items():
        display_val = val[:20] + "..." if len(val) > 20 and "KEY" in key else val
        st.text_input(key, display_val, disabled=True, key=f"env_{key}")

    st.markdown("---")
    st.markdown('<div class="section-header"><h3>📁 输出文件</h3></div>', unsafe_allow_html=True)
    files = find_output_files()
    if files:
        for name, path in files.items():
            size = Path(path).stat().st_size / 1024
            st.markdown(f"- **{name}**: `{path}` ({size:.1f} KB)")
    else:
        st.info("未找到输出文件。")

    st.markdown("---")
    st.markdown('<div class="section-header"><h3>🔗 腾讯集成状态</h3></div>', unsafe_allow_html=True)
    wecom_key = os.environ.get("WECOM_BOT_KEY", "")
    api_key = os.environ.get("TENCENT_API_KEY", "") or os.environ.get("OPENAI_API_KEY", "")
    st.write(f"企业微信机器人: {'✅ 已配置' if wecom_key else '❌ 未配置'}")
    st.write(f"API密钥: {'✅ 已配置' if api_key else '❌ 未配置'}")
