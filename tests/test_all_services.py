"""
完整的服务测试脚本
"""
import asyncio
import os
import sys
import time
import base64
from io import BytesIO
from PIL import Image

if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

from config.settings import settings
from app.services.tts_service import TTSService
from app.services.llm_service import LLMService
from app.services.yolo_service import YOLOService
from app.services.amap_service import AmapService


def print_header(title):
    print("\n" + "=" * 70)
    print(f"  {title}")
    print("=" * 70)


async def test_tts():
    print_header("TTS服务测试")

    try:
        tts_service = TTSService()
        print(f"TTS服务初始化成功")
        print(f"  Provider: {tts_service.provider}")
        print(f"  Mock Mode: {tts_service.mock_mode}")

        text = "前方50米左转"
        audio_url = await tts_service.text_to_speech(text, "test_session")
        print(f"\n测试文本: {text}")
        print(f"生成音频: {audio_url}")

        if not audio_url.startswith('/audio/mock_'):
            filename = audio_url.replace('/audio/', '')
            filepath = os.path.join(settings.AUDIO_OUTPUT_DIR, filename)
            if os.path.exists(filepath):
                size = os.path.getsize(filepath) / 1024
                print(f"文件存在: {size:.2f} KB")
                return True
            else:
                print(f"文件不存在")
                return False
        else:
            print(f"Mock模式")
            return True

    except Exception as e:
        print(f"TTS测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_llm():

    print_header("LLM服务测试")

    try:
        from app.core.session_manager import session_manager

        llm_service = LLMService()
        print(f"LLM服务初始化成功")
        print(f" Model: {settings.LLM_MODEL}")
        print(f" API Base: {settings.LLM_API_BASE}")
        print(f" Mock Mode: {settings.MOCK_MODE}")

        session_id = f"test_llm_{int(time.time())}"
        user_id = "test_user"
        session = session_manager.create_conversation(user_id, session_id)

        user_msg = "你好"

        print(f"\n测试对话:")
        print(f"  用户: {user_msg}")

        response = await llm_service.process_conversation(user_msg, session)
        print(f"  助手: {response['reply']}")
        print(f"  导航状态: {response.get('nav_state', 'unknown')}")

        if response.get('reply'):
            print(f"LLM响应成功")
            return True
        else:
            print(f"LLM响应为空")
            return False

    except Exception as e:
        print(f"LLM测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_yolo():

    print_header("YOLO服务测试")

    try:
        yolo_service = YOLOService()
        print(f"YOLO服务初始化成功")
        print(f"  Model: {settings.YOLO_MODEL_PATH}")
        print(f"  Confidence: {settings.YOLO_CONFIDENCE}")
        print(f"  Mock Mode: {settings.MOCK_MODE}")

        img = Image.new('RGB', (640, 480), color=(73, 109, 137))
        img_byte_arr = BytesIO()
        img.save(img_byte_arr, format='JPEG')
        img_bytes = img_byte_arr.getvalue()
        img_base64 = base64.b64encode(img_bytes).decode('utf-8')

        print(f"\n测试图片: 640x480")

        results = await yolo_service.detect_batch([img_base64])

        if results:
            result = results[0]
            obstacles_raw = result.get('obstacles', [])

            obstacles = yolo_service.aggregate_obstacles(results)
            safety = yolo_service.calculate_safety_level(obstacles)
            road_condition = yolo_service.describe_road_condition(obstacles)

            print(f"检测结果:")
            print(f"  原始检测: {len(obstacles_raw)} 个对象")
            print(f"  障碍物数量: {len(obstacles)}")
            print(f"  安全等级: {safety}/5")
            print(f"  路况: {road_condition}")

            print(f"YOLO检测成功")
            return True
        else:
            print(f"YOLO检测失败")
            return False

    except Exception as e:
        print(f"YOLO测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_amap():
    print_header("高德地图服务测试")

    try:
        amap_service = AmapService()
        print(f"高德地图服务初始化成功")
        print(f"  API Key: {'已配置' if settings.AMAP_API_KEY else '未配置'}")
        print(f"  Mock Mode: {settings.MOCK_MODE}")

        origin = {"lat": 39.916527, "lng": 116.397128}
        destination = {"lat": 39.918058, "lng": 116.403414}

        print(f"\n测试路径规划:")
        print(f"  起点: {origin['lng']},{origin['lat']}")
        print(f"  终点: {destination['lng']},{destination['lat']}")

        routes = await amap_service.plan_walking_route(origin, destination)

        if routes:
            print(f"路径规划成功")
            print(f"  找到 {len(routes)} 条路线")

            if routes:
                route = routes[0]
                print(f"  名称: {route.get('name', 'N/A')}")
                print(f"  距离: {route.get('distance', 0)} 米")
                print(f"  时间: {route.get('duration', 0)} 秒")
                print(f"  无障碍评分: {route.get('accessibilityScore', 0)}")
                steps = route.get('steps', [])
                print(f"  步骤数: {len(steps)}")
                if steps:
                    print(f"  第一步: {steps[0].get('instruction', 'N/A')}")

            return True
        else:
            print(f"路径规划失败: 没有返回路线")
            return False

    except Exception as e:
        print(f"高德地图测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


async def main():

    print(f"\n📋 系统配置:")
    print(f"  DEBUG: {settings.DEBUG}")
    print(f"  MOCK_MODE: {settings.MOCK_MODE}")
    print(f"  PORT: {settings.PORT}")

    results = {}

    results['TTS'] = await test_tts()
    results['LLM'] = await test_llm()
    results['YOLO'] = await test_yolo()
    results['Amap'] = await test_amap()

    total = len(results)
    passed = sum(1 for v in results.values() if v)

    print(f"\n测试结果:")
    for service, result in results.items():
        status = "通过" if result else "失败"
        print(f"  {service:10s} - {status}")

    return passed == total

if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)
