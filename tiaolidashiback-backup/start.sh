#!/bin/bash

echo "🎁 挑礼大师启动中..."

# 检查 Python3 是否安装
if ! command -v python3 &> /dev/null; then
    echo "❌ 错误: 未找到 python3，请先安装 Python 3.11 或更高版本"
    exit 1
fi

PYTHON_VERSION=$(python3 --version 2>&1 | awk '{print $2}')
echo "✅ 检测到 Python: $PYTHON_VERSION"

# 创建虚拟环境目录
VENV_DIR=".venv"

if [ ! -d "$VENV_DIR" ]; then
    echo "📦 创建虚拟环境..."
    python3 -m venv "$VENV_DIR"
fi

echo "✅ 使用虚拟环境: $VENV_DIR"

# 激活虚拟环境并安装依赖
echo "📥 安装依赖..."
source "$VENV_DIR/bin/activate"
pip install -r backend/requirements.txt -q

# 检查 API Key
if [ -z "$DEEPSEEK_API_KEY" ]; then
    echo ""
    echo "⚠️  请设置 DeepSeek API Key："
    echo "   export DEEPSEEK_API_KEY='your-api-key-here'"
    echo ""
    read -p "或者现在直接输入 API Key（回车跳过）: " API_KEY
    if [ -n "$API_KEY" ]; then
        export DEEPSEEK_API_KEY="$API_KEY"
    fi
fi

echo ""
echo "🚀 启动后端服务..."
echo "   前端地址: http://localhost:7890"
echo "   API 文档: http://localhost:7890/docs"
echo ""

cd backend
python main.py
