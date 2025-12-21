#!/bin/bash

echo "========================================="
echo "无障碍导航后端 - 一键测试"
echo "========================================="

# 1. 检查Python
if ! command -v python3 &> /dev/null; then
    echo "❌ Python3 未安装"
    exit 1
fi
echo "✅ Python3: $(python3 --version)"

# 2. 创建虚拟环境（可选）
if [ ! -d "venv" ]; then
    echo "📦 创建虚拟环境..."
    python3 -m venv venv
fi

# 3. 激活虚拟环境
source venv/bin/activate 2>/dev/null || true

# 4. 安装依赖
echo "📦 安装依赖..."
pip install -q -r requirements.txt

# 5. 创建配置文件
if [ ! -f ".env" ]; then
    echo "⚙️  创建配置文件..."
    cat > .env << 'ENVFILE'
DEBUG=True
MOCK_MODE=True
PORT=8000
ENVFILE
fi

# 6. 启动服务
echo "🚀 启动服务..."
python main.py &
SERVER_PID=$!
sleep 3

# 7. 运行测试
echo "🧪 运行测试..."
python tests/test_system.py

# 8. 停止服务
echo "🛑 停止服务..."
kill $SERVER_PID 2>/dev/null

echo ""
echo "========================================="
echo "测试完成！"
echo "========================================="
