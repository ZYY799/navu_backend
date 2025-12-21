# 无障碍导航后端API文档

**Base URL**: `http://localhost:8000`

---

## 核心接口

### 1. 语音交互 - 处理用户语音输入

**接口**: `POST /v1/voice/text`

**请求体**:
```json
{
  "userId": "user_123",
  "sessionId": "session_456",
  "text": "我想去故宫",
  "location": {
    "lat": 39.916527,
    "lng": 116.397128
  }
}
```

**响应**:
```json
{
  "success": true,
  "message": "好的，正在为您规划去故宫的路线",
  "audioUrl": "/audio/abc123.mp3",
  "navState": "navigating",
  "data": {
    "route": {
      "distance": "500米",
      "duration": "7分钟"
    }
  }
}
```

**navState 状态说明**:
- `asking`: LLM正在询问信息（起点/终点不完整）
- `navigating`: 已开始导航
- `arrived`: 已到达目的地

---

### 2. 环境感知 - 障碍物检测

**接口**: `POST /v1/nav/perception/batch`

**请求体**:
```json
{
  "navSessionId": "nav_789",
  "images": [
    "base64_encoded_image_1",
    "base64_encoded_image_2",
    "base64_encoded_image_3"
  ],
  "location": {
    "lat": 39.916527,
    "lng": 116.397128
  }
}
```

**响应**:
```json
{
  "success": true,
  "obstacles": [
    {
      "type": "stairs",
      "distance": 3.5,
      "direction": "正前方",
      "confidence": 0.85
    }
  ],
  "roadCondition": "前方3.5米处有台阶，请注意",
  "safetyLevel": 3,
  "aiGuidance": "前方有台阶，建议减速慢行",
  "audioUrl": "/audio/warning_xyz.mp3"
}
```

**障碍物类型**:
- `stairs`: 台阶
- `curb`: 路沿
- `obstacle`: 障碍物
- `blind_path_broken`: 盲道中断
- `slope`: 坡道

**安全等级**: 1-5 (1最危险, 5最安全)

---

### 3. 开始导航

**接口**: `POST /v1/nav/start`

**请求体**:
```json
{
  "userId": "user_123",
  "origin": {
    "lat": 39.916527,
    "lng": 116.397128
  },
  "destination": {
    "lat": 39.918058,
    "lng": 116.403414
  }
}
```

**响应**:
```json
{
  "success": true,
  "navSessionId": "nav_1234567890",
  "routes": [
    {
      "routeId": "route_001",
      "name": "推荐路线",
      "distance": "500米",
      "duration": "7分钟",
      "accessibilityScore": 85,
      "steps": [
        {
          "instruction": "向北直行100米",
          "distance": "100米",
          "duration": "1分钟"
        }
      ]
    }
  ],
  "message": "已为您规划1条路线，请选择一条开始导航",
  "wsUrl": "ws://localhost:8000/v1/nav/stream?navSessionId=nav_1234567890",
  "audioUrl": "/audio/nav_start_abc.mp3"
}
```

---

### 4. 导航实时推送 (WebSocket)

**接口**: `WS /v1/nav/stream?navSessionId={navSessionId}`

**接收消息类型**:

```json
{
  "type": "NAV_STARTED",
  "data": { "message": "导航已开始" }
}
```

```json
{
  "type": "NAV_INSTRUCTION",
  "data": {
    "instruction": "向北直行100米",
    "audioUrl": "/audio/instruction_123.mp3"
  }
}
```

```json
{
  "type": "OBSTACLE_WARNING",
  "data": {
    "obstacle": {
      "type": "stairs",
      "distance": 3.5,
      "direction": "正前方"
    },
    "audioUrl": "/audio/warning_456.mp3"
  }
}
```

**发送消息格式**:

心跳:
```json
{ "type": "PING" }
```

位置更新:
```json
{
  "type": "LOCATION_UPDATE",
  "location": {
    "lat": 39.916527,
    "lng": 116.397128
  }
}
```

---

## 数据格式说明

### Location (位置)
```typescript
{
  lat: number  // 纬度
  lng: number  // 经度
}
```

### Obstacle (障碍物)
```typescript
{
  type: string         // 类型: stairs/curb/obstacle/blind_path_broken/slope
  distance: number     // 距离(米)
  direction: string    // 方向: 左前方/正前方/右前方
  confidence: number   // 置信度 0-1
}
```

### Route (路线)
```typescript
{
  routeId: string              // 路线ID
  name: string                 // 路线名称
  distance: string             // 总距离
  duration: string             // 预计时长
  accessibilityScore: number   // 无障碍评分 0-100
  steps: Step[]                // 导航步骤
}
```

---

## 错误响应

```json
{
  "detail": "错误描述信息"
}
```

**HTTP状态码**:
- `200`: 成功
- `400`: 请求参数错误
- `500`: 服务器内部错误

---

## 图片格式要求

**编码**: Base64
**格式**: JPEG/PNG
**分辨率**: 建议 640x480 或更高
**数量**: 每次请求 1-3 张图片

**前端编码示例 (JavaScript)**:
```javascript
// 将图片转为 Base64
function imageToBase64(file) {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => resolve(reader.result.split(',')[1]);
    reader.onerror = reject;
    reader.readAsDataURL(file);
  });
}

// 使用
const imageBase64 = await imageToBase64(imageFile);
```

---

## 音频文件

**格式**: MP3
**访问**: `http://localhost:8000/audio/{filename}.mp3`
**语音**: 中文女声 (Edge TTS)

---

## 健康检查

**接口**: `GET /health`

**响应**:
```json
{
  "status": "healthy",
  "mode": "production"
}
```
