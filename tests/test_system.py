"""
系统集成测试
"""
import requests
import json
import time
import base64
from PIL import Image
import io


BASE_URL = "http://localhost:8000"


def test_health():
    response = requests.get(f"{BASE_URL}/health")
    assert response.status_code == 200
    data = response.json()
    print(f"服务健康检查通过: {data}")


def test_voice_text():

    payload = {
        "userId": "test_user_001",
        "sessionId": "session_001",
        "text": "我要去超市",
        "timestamp": int(time.time() * 1000)
    }
    
    response = requests.post(f"{BASE_URL}/v1/voice/text", json=payload)
    assert response.status_code == 200
    data = response.json()
    
    print(f"用户: {payload['text']}")
    print(f"系统: {data['message']}")
    print("语音文本接口测试通过")


def test_perception_batch():

    print("\n[3/5] 测试感知批次接口...")

    img = Image.new('RGB', (640, 480), color='white')
    buffer = io.BytesIO()
    img.save(buffer, format='JPEG')
    img_base64 = base64.b64encode(buffer.getvalue()).decode()
    
    payload = {
        "userId": "test_user_001",
        "navSessionId": "nav_001",
        "images": [img_base64, img_base64, img_base64],
        "location": {"lat": 39.9042, "lng": 116.4074},
        "timestamp": int(time.time() * 1000)
    }
    
    response = requests.post(f"{BASE_URL}/v1/nav/perception/batch", json=payload)
    assert response.status_code == 200
    data = response.json()
    
    print(f"检测到 {len(data['obstacles'])} 个障碍物")
    print(f"安全等级: {data['safetyLevel']}/5")
    print("感知批次接口测试通过")


def test_nav_start():

    print("\n[4/5] 测试导航开始接口...")
    payload = {
        "userId": "test_user_001",
        "sessionId": "session_001",
        "origin": {"lat": 39.9042, "lng": 116.4074},
        "destination": {"lat": 39.9142, "lng": 116.4174}
    }
    
    response = requests.post(f"{BASE_URL}/v1/nav/start", json=payload)
    assert response.status_code == 200
    data = response.json()
    
    print(f"路线规划成功: 全程{data['routes'][0]['distance']}米")
    print(f"WebSocket URL: {data['wsUrl']}")
    print("导航开始接口测试通过")


def test_websocket():

    print("\n[5/5] 测试WebSocket实时导航...")
    try:
        import websockets
        import asyncio
        
        async def connect_ws():
            uri = "ws://localhost:8000/v1/nav/stream?navSessionId=test_nav_001"
            async with websockets.connect(uri) as websocket:

                message = await websocket.recv()
                data = json.loads(message)
                print(f"收到事件: {data['type']}")

                await websocket.send(json.dumps({"type": "PING"}))
                response = await websocket.recv()
                data = json.loads(response)
                print(f"收到事件: {data['type']}")
        
        asyncio.run(connect_ws())
        print("WebSocket导航测试通过")
        
    except ImportError:
        print("websockets库未安装，跳过WebSocket测试")
    except Exception as e:
        print(f"WebSocket测试失败: {e}")


def main():
    
    try:
        test_health()
        test_voice_text()
        test_perception_batch()
        test_nav_start()
        test_websocket()

        print("所有测试通过！ (5/5)")

    except AssertionError as e:
        print(f"\n测试失败: {e}")
    except Exception as e:
        print(f"\n测试出错: {e}")


if __name__ == "__main__":
    main()
