      

# 无障碍导航后端系统


高德开发者竞赛后端程序
合作开发项目的伙伴：
- [@luoxinlan322-sudo](https://github.com/luoxinlan322-sudo) - 技术搭档


---

## 视频演示
[NAVU完整视频演示](https://www.bilibili.com/video/BV1horYBmEiP/?vd_source=17c0a0142f8ebd7df1073a5c92d75ed0)

[识别结果演示](https://www.bilibili.com/video/BV1aorYBmEAx/?share_source=copy_web&vd_source=e72afecb05b00958296c3d225a203fdc)

[11](./docs/media/demo.mp4)


## 快速开始

### 1. 安装依赖

> 说明：`requirements.txt` 为基础依赖
> 如需开启 YOLO 识别，再额外安装 CPU 或 GPU 依赖（二选一）。

```bash
pip install -U pip
pip install -r requirements.txt

#开启 YOLO（CPU 版）
pip install -r requirements-yolo-cpu.txt
#开启 YOLO（GPU 版，CUDA 11.8 示例）
pip install -r requirements-yolo-gpu-cu118.txt
```

### 2. 配置环境变量

复制 `.env.example` 为 `.env`，填写配置:

```LLM_API_KEY=your_deepseek_api_key
AMAP_API_KEY=your_amap_api_key
MOCK_MODE=false
```

### 3. 启动服务

```
uvicorn main:app --host 0.0.0.0 --port 8000
```

**访问地址**：

- 服务：http://127.0.0.1:8000
- API文档：http://127.0.0.1:8000/docs

## 项目结构

```
accessible-nav-backend/
├── main.py                 # 应用入口
├── API.md                  # API接口文档
├── requirements.txt        # 基础依赖
├── requirements-yolo-*.txt # YOLO依赖
├── .env                    # 环境配置
├── .env.example            # 配置模板
├── app/
│   ├── api/
│   │   ├── voice_routes.py    # 语音接口
│   │   └── nav_routes.py      # 导航接口
│   ├── services/
│   │   ├── tts_service.py     # 语音合成
│   │   ├── yolo_service.py    # 障碍物识别
│   │   ├── llm_service.py     # 大模型对话
│   │   └── amap_service.py    # 地图服务
│   ├── core/
│   │   ├── session_manager.py     # 会话管理
│   │   └── websocket_manager.py   # WebSocket管理
│   └── models/
│       └── schemas.py         # 数据模型
├── config/
│   └── settings.py            # 系统配置
└── tests/
    └── test_frontend.py       # 前端测试
```

## 快速尝试




