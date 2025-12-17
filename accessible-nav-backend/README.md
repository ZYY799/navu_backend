# 无障碍老年人导航后端系统

## 快速开始

### 1. 安装依赖
```bash
pip install -r requirements.txt
```

### 2. 配置环境
```bash
# 复制配置文件
cp .env.example .env

# 编辑配置（可选，模拟模式无需配置）
nano .env
```

### 3. 启动服务
```bash
python main.py
```

### 4. 访问API文档
打开浏览器访问: http://localhost:8000/docs

## 测试

```bash
# 运行测试脚本
python tests/test_system.py

# 或使用一键测试脚本
./quick_test.sh  # Linux/Mac
quick_test.bat   # Windows
```

## 项目结构

```
accessible-nav-backend/
├── main.py                    # 主程序入口
├── requirements.txt           # 依赖列表
├── Dockerfile                 # Docker配置
├── .env.example              # 配置示例
├── config/
│   └── settings.py           # 配置管理
├── app/
│   ├── api/                  # API路由
│   ├── services/             # 业务服务
│   ├── core/                 # 核心模块
│   └── models/               # 数据模型
└── tests/
    └── test_system.py        # 测试脚本
```

## 核心功能

1. **语音交互** - LLM驱动的多轮对话
2. **路径规划** - 高德API步行导航
3. **视觉识别** - YOLO障碍物检测
4. **实时推送** - WebSocket导航指令
5. **会话管理** - Redis状态存储

## 许可证

MIT License
