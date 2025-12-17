# 快速开始指南

## 📦 解压和安装

```bash
# 1. 解压文件
tar -xzf accessible-nav-backend.tar.gz
cd accessible-nav-backend

# 2. 安装依赖
pip install -r requirements.txt
```

## 🚀 启动服务

### 方式一：一键测试（推荐）

```bash
# Linux/Mac
./quick_test.sh

# Windows
quick_test.bat
```

### 方式二：手动启动

```bash
# 1. 创建配置文件（可选）
cat > .env << EOF
DEBUG=True
MOCK_MODE=True
PORT=8000
EOF

# 2. 启动服务
python main.py

# 3. 访问API文档
# 打开浏览器: http://localhost:8000/docs
```

## 🧪 测试接口

### 健康检查
```bash
curl http://localhost:8000/health
```

### 语音文本接口
```bash
curl -X POST http://localhost:8000/v1/voice/text \
  -H "Content-Type: application/json" \
  -d '{
    "userId": "test_001",
    "sessionId": "session_001",
    "text": "我要去超市",
    "timestamp": 1702800000000
  }'
```

### 导航开始接口
```bash
curl -X POST http://localhost:8000/v1/nav/start \
  -H "Content-Type: application/json" \
  -d '{
    "userId": "test_001",
    "sessionId": "session_001",
    "origin": {"lat": 39.9042, "lng": 116.4074},
    "destination": {"lat": 39.9142, "lng": 116.4174}
  }'
```

## 📝 配置说明

### 模拟模式（默认）
无需任何API密钥，所有功能返回模拟数据，适合：
- 快速测试
- 开发调试
- 演示展示

### 生产模式
需要配置真实API密钥：

```bash
# .env
MOCK_MODE=False
AMAP_API_KEY=你的高德地图密钥
LLM_API_KEY=你的LLM密钥
TTS_API_KEY=你的TTS密钥
```

## 🎯 核心接口

| 接口 | 方法 | 说明 |
|------|------|------|
| `/health` | GET | 健康检查 |
| `/v1/voice/text` | POST | 语音文本处理 |
| `/v1/nav/perception/batch` | POST | 感知批次分析 |
| `/v1/nav/start` | POST | 开始导航 |
| `/v1/nav/stream` | WebSocket | 实时导航推送 |

## 📖 详细文档

- API文档: http://localhost:8000/docs
- 项目结构: 见 README.md
- 测试指南: 见 TESTING.md
- 技术架构: 见 ARCHITECTURE.md

## ❓ 常见问题

**Q: 端口被占用怎么办？**
```bash
PORT=8001 python main.py
```

**Q: 依赖安装失败？**
```bash
# 使用国内镜像
pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple
```

**Q: 如何停止服务？**
```bash
# Ctrl+C 或找到进程
ps aux | grep main.py
kill <PID>
```

## 🚀 下一步

1. 配置真实API密钥（生产环境）
2. 训练YOLO模型（使用实际场景数据）
3. 部署到服务器
4. 对接前端应用

## 📞 支持

如有问题，请查看完整文档或联系开发团队。
