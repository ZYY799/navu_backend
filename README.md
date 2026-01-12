# 无障碍导航后端系统
高德开发者竞赛后端程序
---

## 快速开始

### 1. 安装依赖

> 说明：`requirements.txt` 为基础依赖
> 如需开启 YOLO 识别，再额外安装 CPU 或 GPU 依赖（二选一）。

```bash
pip install -U pip
pip install -r requirements.txt

开启 YOLO（CPU 版）
pip install -r requirements-yolo-cpu.txt
开启 YOLO（GPU 版，CUDA 11.8 示例）
pip install -r requirements-yolo-gpu-cu118.txt

### 2. 配置环境变量
复制 `.env.example` 为 `.env`，填写配置:
```
LLM_API_KEY=your_deepseek_api_key
AMAP_API_KEY=your_amap_api_key
MOCK_MODE=false
```

### 3. 启动服务
```
uvicorn main:app --host 0.0.0.0 --port 8000
```

服务地址：http://127.0.0.1:8000

API 文档：http://127.0.0.1:8000/docs

---

## 技术栈

- **FastAPI**: Web框架
- **YOLOv8**: 障碍物检测
- **Edge TTS**: 文字转语音
- **Deepseek LLM**: 对话理解 + Function Calling
- **高德地图API**: 路径规划

---

## 测试

