# 前端集成指南

## 快速对接

### 测试验证
```bash
python tests/test_frontend.py
```

### 三个输入变量

```javascript
// 1. 当前位置
const location = {
  lat: 39.916527,  // 纬度
  lng: 116.397128  // 经度
}

// 2. 语音文字
const voiceText = "我想去故宫"

// 3. 图片Base64
const imageBase64 = "..." // 相机拍摄的Base64编码图片
```

### 后端返回

```javascript
{
  success: true,
  message: "好的，正在为您规划去故宫的路线",
  audioUrl: "/audio/abc123.mp3",         // 语音文件URL
  obstacles: [                            // 障碍物列表
    {
      type: "stairs",                     // 类型
      distance: 3.5,                      // 距离(米)
      direction: "正前方",                 // 方向
      confidence: 0.85                    // 置信度
    }
  ],
  safetyLevel: 5,                        // 安全等级 1-5
  navState: "navigating",                 // 导航状态
  navData: {...}                          // 导航数据
}
```

---

## 图片编码示例

```javascript
// 将File对象转为Base64
async function imageToBase64(file) {
  return new Promise((resolve, reject) => {
    const reader = new FileReader()
    reader.onload = () => {
      // 去掉 "data:image/jpeg;base64," 前缀
      const base64 = reader.result.split(',')[1]
      resolve(base64)
    }
    reader.onerror = reject
    reader.readAsDataURL(file)
  })
}

// 使用
const file = document.querySelector('input[type="file"]').files[0]
const imageBase64 = await imageToBase64(file)
```

---

## 完整调用示例

```javascript
// 前端调用
async function sendToBackend(location, voiceText, cameraImage) {
  // 转换图片为Base64
  const imageBase64 = await imageToBase64(cameraImage)

  // 发送请求
  const response = await fetch('http://localhost:8000/v1/voice/text', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      userId: 'user_123',
      sessionId: 'session_456',
      text: voiceText,
      location: location
    })
  })

  const result = await response.json()

  // 处理返回结果
  console.log('后端回复:', result.message)
  console.log('语音URL:', result.audioUrl)
  console.log('障碍物:', result.obstacles)
  console.log('安全等级:', result.safetyLevel)

  // 播放语音
  const audio = new Audio('http://localhost:8000' + result.audioUrl)
  audio.play()

  return result
}
```

---

## 状态说明

### navState (导航状态)

| 状态 | 说明 |
|------|------|
| `asking` | LLM正在询问信息(起点/终点不完整) |
| `navigating` | 已开始导航 |
| `arrived` | 已到达目的地 |

### safetyLevel (安全等级)

| 等级 | 说明 |
|------|------|
| 1 | 非常危险 (障碍物<2米) |
| 2 | 危险 (障碍物2-5米) |
| 3 | 注意 (障碍物5-10米) |
| 4 | 安全 (障碍物10-20米) |
| 5 | 非常安全 (无障碍物或>20米) |

### 障碍物类型

| 类型 | 中文 |
|------|------|
| `stairs` | 台阶 |
| `curb` | 路沿 |
| `obstacle` | 障碍物 |
| `blind_path_broken` | 盲道中断 |
| `slope` | 坡道 |

---

## 测试数据

运行 `python tests/test_frontend.py` 的实际输出:

```
📥 前端输入:
  位置: lat=39.916527, lng=116.397128
  文字: 我想去故宫
  图片: fig/R-C.jpg (已转Base64)

📤 后端返回:
  success: True
  message: 好的，正在为您规划去故宫的路线
  audioUrl: /audio/250331b7d637e95fe9810fa15ff7f699.mp3
  obstacles: 0 个
  safetyLevel: 5/5
  navState: navigating
```

---

## API详细文档

完整API文档见 **[API.md](./API.md)**
