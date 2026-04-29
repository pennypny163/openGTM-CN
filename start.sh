#!/bin/bash
# OpenGTM 前端启动脚本
# 用法: bash start.sh

set -e

echo "=== OpenGTM 前端启动 ==="

# 安装依赖
echo "[1/3] 安装Python依赖..."
pip install flask python-dotenv openai requests httpx click beautifulsoup4 lxml 2>&1 | tail -3

# 检查floom（可选）
pip install floom 2>/dev/null || echo "floom未安装（可选）"

# 检查端口
PORT=${PORT:-5000}
if lsof -i :$PORT -t >/dev/null 2>&1; then
  echo "端口 $PORT 已被占用，尝试使用 5001..."
  PORT=5001
fi

echo "[2/3] 依赖安装完成"
echo "[3/3] 启动Flask服务 (端口: $PORT)..."
echo ""
echo "  访问地址: http://0.0.0.0:$PORT"
echo ""

export PORT=$PORT
python3 api_server.py
