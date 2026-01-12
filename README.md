# 🧭 无障碍导航后端系统

> 高德开发者竞赛后端程序

## 👥 项目协作者

本项目由 [@luoxinlan322-sudo](https://github.com/luoxinlan322-sudo) 共同协作完成。

---


## 🎬 视频演示

| 演示内容 | 预览 | 链接 |
|---------|------|------|
| 完整功能演示 | ![封面](./docs/media/cover1.png) | [观看视频](https://www.bilibili.com/video/BV1horYBmEiP/) |
| 识别效果展示 | ![封面](./docs/media/cover2.png) | [观看视频](https://www.bilibili.com/video/BV1aorYBmEAx/) |



## 🚀 快速开始

### 1. 安装依赖

> **说明**：`requirements.txt` 为基础依赖
> 如需开启 YOLO 识别，请根据硬件条件选择安装 CPU 或 GPU 版本（二选一）

```bash
# 更新 pip
pip install -U pip

# 安装基础依赖
pip install -r requirements.txt

# 选择一：开启 YOLO（CPU 版）
pip install -r requirements-yolo-cpu.txt

# 选择二：开启 YOLO（GPU 版，CUDA 11.8 示例）
pip install -r requirements-yolo-gpu-cu118.txt
```

### 2. 配置环境变量

复制 `.env.example` 为 `.env`，并填写相关配置：

```bash
cp .env.example .env
```

配置示例：

```env
LLM_API_KEY=your_deepseek_api_key
AMAP_API_KEY=your_amap_api_key
MOCK_MODE=false
```

### 3. 启动服务

```bash
uvicorn main:app --host 0.0.0.0 --port 8000
```

**访问地址：**

- 服务地址：http://127.0.0.1:8000
- API 文档：http://127.0.0.1:8000/docs

---

## 📁 项目结构

```
accessible-nav-backend/
├── main.py                      # 应用入口
├── API.md                       # API接口文档
├── requirements.txt             # 基础依赖
├── requirements-yolo-*.txt      # YOLO依赖配置
├── .env                         # 环境配置（需自行创建）
├── .env.example                 # 配置模板
│
├── app/
│   ├── api/                     # API路由层
│   │   ├── voice_routes.py      # 语音交互接口
│   │   └── nav_routes.py        # 导航服务接口
│   │
│   ├── services/                # 业务逻辑层
│   │   ├── tts_service.py       # 文字转语音服务
│   │   ├── yolo_service.py      # 障碍物识别服务
│   │   ├── llm_service.py       # 大模型对话服务
│   │   └── amap_service.py      # 高德地图服务
│   │
│   ├── core/                    # 核心功能模块
│   │   ├── session_manager.py   # 会话管理器
│   │   └── websocket_manager.py # WebSocket管理器
│   │
│   └── models/                  # 数据模型
│       └── schemas.py           # Pydantic数据模型
│
├── config/                      # 配置文件
│   └── settings.py              # 系统配置管理
│
└── tests/                       # 测试文件
    ├── test_frontend.py         # 前端测试脚本
    └── test.ipynb               # 快速测试 Notebook
```

---

## 🧪 快速测试

使用 Jupyter Notebook 快速体验：

```bash
jupyter notebook tests/test.ipynb
```

---

## 📚 相关文档

- [API 接口文档](./API.md)
- [配置说明](./.env.example)

---

## 📄 开源协议

本项目基于 MIT License 开源。