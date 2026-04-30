# 🚀 OpenGTM-CN — AI驱动的B2B获客自动化平台

<div align="center">

![Python 3.9+](https://img.shields.io/badge/python-3.9+-blue.svg)
![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)

**Clay ($800/月) 的开源替代品，适配中国 B2B 市场**

支持 DeepSeek / OpenAI / 混元等任何 OpenAI 兼容 API

</div>

---

## ⚡ 一句话介绍

OpenGTM 是一个 **AI 驱动的 B2B GTM 自动化工具包**，帮你：
- 🔍 **按行业+地区发现目标公司**（LLM + URL 验证）
- 🔬 **调研公司网站**（提取决策者联系人 + 技术审计）
- 🎯 **ICP 评分 0-100**（6 维度，自动分级 hot/warm/cold）
- ✍️ **生成个性化外展消息**（5 种模式，中/英/德三语）
- 🩺 **AEO 健康检查**（29 项检查，AI 可见性评分）
- 📝 **内容流水线**（博客生成 + SEO 关键词研究）
- 🔄 **企业微信 CRM 同步**

**成本对比：** Clay ($800/月) vs OpenGTM ($0 + API ≈ ¥0.07/条线索)

---

## 🚀 快速开始

```bash
# 1. 安装
pip install -e .

# 2. 配置
cp .env.example .env
# 编辑 .env，填入你的 API Key

# 3. 运行完整流水线
opengtm pipeline --industry "B2B SaaS" --region "北京" --limit 5

# 4. 或启动 Web 界面
python api_server.py
# 访问 http://localhost:5001
```

---

## 🎯 核心模块

| 模块 | 功能 | CLI 命令 |
|------|------|----------|
| **Discover** | 按行业+地区发现目标公司 | `opengtm discover` |
| **Research** | 调研网站：联系人 + 7维度审计 | `opengtm research` |
| **Qualify** | ICP评分 0-100（hot/warm/cold） | `opengtm qualify` |
| **Message** | 5种模式个性化外展消息 | `opengtm message` |
| **Analytics** | 29项 AEO 健康检查 | `opengtm analytics` |
| **Blog** | 5阶段 AI 博客生成 | `opengtm blog` |
| **Keywords** | 7阶段 SEO 关键词研究 | `opengtm keywords` |
| **Pipeline** | 一键全流程 | `opengtm pipeline` |
| **Sync** | 企业微信 CRM 推送 | `opengtm sync` |

---

## 🏗️ 架构

```
Discover → Research → Qualify → Message → Outreach → Sync
   |           |          |          |          |         |
   v           v          v          v          v         v
 LLM搜索    网站审计    6维评分    5模式消息   多触点序列  企业微信
```

---

## 🎯 ICP 评分体系

| 维度 | 满分 | 信号来源 |
|------|------|----------|
| 行业匹配度 | 25 | 5级行业分层 |
| 痛点信号 | 20 | 网站审计发现 |
| 公司规模 | 20 | 博客/社交/网站复杂度 |
| 数字化成熟度 | 15 | Schema/社交/内容 |
| 营收信号 | 10 | 内容投入代理 |
| 联系人质量 | 10 | 邮箱/电话/微信 |

**分级：** 🔥 Hot (70+) · 🌤 Warm (45-69) · ❄️ Cold (<45)

---

## 💬 消息框架

AI 根据审计发现自动选择最佳模式：

| 模式 | 触发条件 | 示例 |
|------|----------|------|
| **A - 具体发现** | 网站有明确技术问题 | "你们的 meta 描述缺失，5分钟即可修复" |
| **B - 竞争对手** | 竞品在 AI 搜索中可见 | "[竞品]在ChatGPT中出现了，你们还没有" |
| **C - 内容未索引** | 博客存在但未被收录 | "博客内容在搜索中不可见，1-2个技术修复" |
| **D - 免费工具** | 无强发现 | "60秒查看你在AI搜索中的排名" |
| **E - AI可见性** | 兜底/干净网站 | "测试了你是否出现在ChatGPT中，大多数同行还没有" |

---

## 🔧 配置

项目使用 `.env` 文件配置，支持任何 OpenAI 兼容 API：

```bash
# 必需
OPENAI_API_KEY=your_key_here
OPENAI_BASE_URL=https://api.deepseek.com/v1
HUNYUAN_MODEL=deepseek-chat

# 可选
CRM_WEBHOOK_URL=企业微信群机器人Webhook
DEFAULT_LANGUAGE=zh
DEFAULT_DAILY_LIMIT=20
```

**支持的 API 端点：** DeepSeek、OpenAI、腾讯混元、通义千问、Ollama 等。

---

## 🐍 Python API

```python
from opengtm.discover import discover
from opengtm.research import research
from opengtm.qualify import qualify_batch
from opengtm.message import generate_messages

# 发现目标公司
leads = discover(industry="B2B SaaS", region="北京", limit=5)

# 调研
for lead in leads:
    lead["audit"] = research(domain=lead["domain"], company=lead["company"])

# 评分
qualified = qualify_batch(leads, icp_profile="saas")

# 生成消息
for lead in qualified:
    lead["messages"] = generate_messages(
        domain=lead["domain"],
        company=lead["company"],
        audit=lead.get("audit"),
        language="zh",
    )
```

---

## 🌐 Web 界面

启动 Flask 服务后提供现代化暗色仪表盘 UI：

```bash
PORT=5001 python api_server.py
```

功能：一键流水线、线索发现、公司调研、ICP评分、AEO健康检查、外展管理、CRM同步。

---

## 📂 项目结构

```
opengtm/
├── __init__.py          # 版本 & 模型常量
├── llm.py              # 统一LLM客户端（OpenAI兼容）
├── discover.py         # 线索发现
├── research.py         # 公司调研 + 联系人提取
├── qualify.py          # ICP评分（纯逻辑）
├── message.py          # 消息生成（模板引擎）
├── outreach.py         # 外展序列管理
├── sync.py             # 企业微信CRM同步
├── analytics.py        # AEO健康检查（29项）
├── context.py          # 公司上下文提取
├── blog.py             # 博客生成流水线
├── keywords.py         # 关键词研究流水线
├── sitemap.py          # 站点地图爬取
├── tencent_integration.py  # 腾讯生态集成
└── cli.py              # 统一CLI入口
```

---

## 🤝 贡献

See [CONTRIBUTING.md](CONTRIBUTING.md)

---

## 📄 License

MIT License. See [LICENSE](LICENSE).
