"""
简单的API测试脚本
"""
import requests
import json
import sys

if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

BASE_URL = "http://localhost:8000"

print("\n1. 测试健康检查...")
try:
    response = requests.get(f"{BASE_URL}/health", timeout=5)
    data = response.json()
    print(f"   状态: {data['status']}")
    print(f"   模式: {data['mode']}")
except Exception as e:
    print(f"   失败: {e}")
    sys.exit(1)

# 测试2: 根路径
print("\n2. 测试根路径...")
try:
    response = requests.get(f"{BASE_URL}/", timeout=5)
    data = response.json()
    print(f"   服务: {data['service']}")
    print(f"   版本: {data['version']}")
except Exception as e:
    print(f"   失败: {e}")

# 测试3: 语音交互API
print("\n3. 测试语音交互API...")
try:
    payload = {
        "userId": "test_user",
        "sessionId": "session_api_test",
        "text": "你好，我想去天安门",
        "timestamp": 1734451200000
    }
    response = requests.post(f"{BASE_URL}/v1/voice/text", json=payload, timeout=15)
    data = response.json()
    print(f"   成功")
    print(f"   用户: {payload['text']}")
    print(f"   回复: {data.get('message', 'N/A')[:50]}...")
    print(f"   音频: {data.get('audioUrl', 'N/A')}")
    print(f"   状态: {data.get('navState', 'N/A')}")
except Exception as e:
    print(f"   失败: {e}")

# 测试4: 导航启动API
print("\n4. 测试导航启动API...")
try:
    payload = {
        "userId": "test_user",
        "sessionId": "session_api_test",
        "origin": "116.397128,39.916527",
        "destination": "116.403414,39.918058"
    }
    response = requests.post(f"{BASE_URL}/v1/nav/start", json=payload, timeout=15)
    data = response.json()
    print(f"   成功")
    print(f"   导航ID: {data.get('navSessionId', 'N/A')}")
    print(f"   路线数: {len(data.get('routes', []))}")
    if data.get('routes'):
        route = data['routes'][0]
        print(f"   距离: {route['distance']} 米")
        print(f"   时间: {route['duration']} 秒")
    print(f"   音频: {data.get('audioUrl', 'N/A')}")
except Exception as e:
    print(f"   失败: {e}")

