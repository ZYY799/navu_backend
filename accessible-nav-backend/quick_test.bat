@echo off
echo =========================================
echo 无障碍导航后端 - 一键测试
echo =========================================

REM 检查Python
where python >nul 2>nul
if errorlevel 1 (
    echo ❌ Python 未安装
    exit /b 1
)
echo ✅ Python已安装

REM 安装依赖
echo 📦 安装依赖...
pip install -q -r requirements.txt

REM 创建配置
if not exist ".env" (
    echo ⚙️  创建配置文件...
    (
        echo DEBUG=True
        echo MOCK_MODE=True
        echo PORT=8000
    ) > .env
)

REM 启动服务
echo 🚀 启动服务...
start /b python main.py
timeout /t 3

REM 运行测试
echo 🧪 运行测试...
python tests/test_system.py

REM 停止服务
echo 🛑 停止服务...
taskkill /f /im python.exe

echo.
echo =========================================
echo 测试完成！
echo =========================================
pause
