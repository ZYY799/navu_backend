# 无障碍导航后端系统

为老年人和视障人士设计的AI导航系统后端服务

---

## 快速开始

### 1. 安装依赖

> 说明：`requirements.txt` 为基础依赖（FastAPI/WS/TTS 等，任何电脑都能装）。
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

## 项目结构

```
accessible-nav-backend/
├── main.py                 # 主程序入口
├── API.md                  # 前端对接文档
├── requirements.txt        # 依赖列表
├── .env                    # 环境变量配置
│
├── app/                    # 应用代码
│   ├── api/                # API路由
│   │   ├── voice_routes.py # 语音交互接口
│   │   └── nav_routes.py   # 导航服务接口
│   │
│   ├── services/           # 核心服务
│   │   ├── tts_service.py  # 文字转语音
│   │   ├── yolo_service.py # 障碍物检测
│   │   ├── llm_service.py  # 大模型对话
│   │   └── amap_service.py # 高德地图路径规划
│   │
│   ├── core/               # 核心组件
│   │   ├── session_manager.py    # 会话管理
│   │   └── websocket_manager.py  # WebSocket管理
│   │
│   └── models/             # 数据模型
│       └── schemas.py      # Pydantic数据模型
│
├── config/                 # 配置
│   └── settings.py         # 系统配置
│
└── tests/                  # 测试代码
    └── test_frontend.py    # 前端集成测试

```

---

## 核心功能

### 1. 语音交互
- 接收前端语音识别文字
- LLM理解用户意图
- 自动调用高德API规划路线
- TTS生成语音回复

### 2. 环境感知
- YOLOv8检测障碍物
- 识别: 台阶/路沿/障碍物/盲道中断/坡道
- 评估安全等级
- 生成语音警告

### 3. 导航服务
- 高德地图路径规划
- 无障碍评分
- WebSocket实时推送
- 偏航重新规划

---

## 技术栈

- **FastAPI**: Web框架
- **YOLOv8**: 障碍物检测
- **Edge TTS**: 文字转语音
- **Deepseek LLM**: 对话理解 + Function Calling
- **高德地图API**: 路径规划

---

## 前端对接

详见 **[API.md](./API.md)**

### 核心接口

1. **语音交互**: `POST /v1/voice/text`
2. **环境感知**: `POST /v1/nav/perception/batch`
3. **开始导航**: `POST /v1/nav/start`
4. **实时推送**: `WS /v1/nav/stream`

### 数据格式

**前端输入**:
```javascript
{
  location: { lat: 39.916527, lng: 116.397128 },  // 当前位置
  text: "我想去故宫",                              // 语音文字
  image: "base64_encoded_image"                   // 图片Base64
}
```

**后端返回**:
```javascript
{
  success: true,
  message: "好的，正在为您规划去故宫的路线",
  audioUrl: "/audio/abc123.mp3",
  obstacles: [...],
  safetyLevel: 5,
  navState: "navigating"
}
```

---

## 测试

### 前端集成测试
模拟前端调用完整流程:
```bash
python tests/test_frontend.py
```

输入:
- 位置: `lat=39.916527, lng=116.397128`
- 文字: `"我想去故宫"`
- 图片: `fig/R-C.jpg` (Base64)

输出:
- 障碍物检测结果
- LLM导航回复
- TTS音频文件

---

## 配置说明

`.env` 配置项:

| 配置项 | 说明 | 默认值 |
|--------|------|--------|
| `PORT` | 服务端口 | 8000 |
| `DEBUG` | 调试模式 | True |
| `MOCK_MODE` | 模拟模式 | False |
| `LLM_API_KEY` | Deepseek API密钥 | - |
| `AMAP_API_KEY` | 高德地图API密钥 | - |
| `YOLO_MODEL_PATH` | YOLO模型路径 | yolov8n.pt |

---

## API文档

启动服务后访问:
- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

---

## 联系方式

前端对接问题请查阅 `API.md`
