# Contributing to OpenGTM-CN

## Setup

```bash
git clone https://github.com/pennypny163/openGTM-CN
cd openGTM-CN
pip install -e ".[dev]"
cp .env.example .env
# 在 .env 中填入你的 API Key（支持 DeepSeek、OpenAI 等任何兼容端点）
```

## Making changes

1. Fork the repo and create a branch: `git checkout -b my-feature`
2. Make your changes
3. Run tests: `pytest tests/`
4. Open a PR against `main`

For significant changes (new modules, breaking changes), open an issue first to discuss.

## Where to contribute

- **New ICP profiles** — add to `ICP_PROFILES` dict in `qualify.py`
- **New message frameworks** — add patterns to `message.py` (支持中/英/德)
- **CRM integrations** — add adapters in `sync.py` (飞书、钉钉、HubSpot)
- **Language support** — extend `_STRINGS` dict in `message.py`
- **SERP volume** — integrate Serper or DataForSEO in `keywords.py` stage 6

## Code style

- Python 3.9+
- `from __future__ import annotations` at top of every module
- Use `DEFAULT_MODEL` from `opengtm/__init__.py`, never hardcode model strings
- All LLM calls go through `opengtm/llm.py`（OpenAI 兼容接口）
- No external runtime dependencies beyond those in `pyproject.toml`
- Run `ruff check .` before submitting
