"""
完整流程测试：模拟前端请求
输入：当前位置 + 图片 + 语音文字
输出：障碍物检测 + 导航指引 + 语音返回
"""
import asyncio
import base64
import sys
import os

if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

async def test_complete_flow():

    from app.services.tts_service import TTSService
    from app.services.yolo_service import YOLOService
    from app.services.llm_service import LLMService
    from app.services.amap_service import AmapService
    from app.core.session_manager import session_manager

    print("\n模拟前端输入:")

    current_location = {"lat": 39.916527, "lng": 116.397128}
    print(f"  位置: {current_location}")

    user_text = "我想去故宫"
    print(f"  语音文字: {user_text}")

    img_path = "test_fig/R-C.jpg"
    if os.path.exists(img_path):
        with open(img_path, 'rb') as f:
            img_bytes = f.read()
            img_base64 = base64.b64encode(img_bytes).decode('utf-8')
        print(f"  图片: {img_path} (已加载)")
    else:
        from PIL import Image
        import io as iolib
        img = Image.new('RGB', (640, 480), color=(100, 100, 100))
        buf = iolib.BytesIO()
        img.save(buf, format='JPEG')
        img_bytes = buf.getvalue()
        img_base64 = base64.b64encode(img_bytes).decode('utf-8')
        print(f"  图片: 测试图片 (已创建)")

    print("\n" + "=" * 70)

    print("\n步骤1: 障碍物检测")
    yolo_service = YOLOService()
    results = await yolo_service.detect_batch([img_base64])
    obstacles = yolo_service.aggregate_obstacles(results)
    safety_level = yolo_service.calculate_safety_level(obstacles)

    print(f"  检测到 {len(obstacles)} 个障碍物")
    print(f"  安全等级: {safety_level}/5")
    if obstacles:
        for i, obs in enumerate(obstacles[:3], 1):
            print(f"    {i}. {obs.type} - {obs.distance}m - {obs.direction}")

    print("\n步骤2: 理解用户需求")
    llm_service = LLMService()
    session = session_manager.create_conversation("test_user", "test_session")

    context_message = f"用户当前位置: {current_location['lat']}, {current_location['lng']}"
    full_message = f"{context_message}\n用户说: {user_text}"

    llm_response = await llm_service.process_conversation(full_message, session)
    print(f"  LLM回复: {llm_response['reply'][:100]}...")
    print(f"  导航状态: {llm_response['nav_state']}")

    print("\n🔊 步骤3: 生成语音回复")
    tts_service = TTSService()

    if obstacles:
        warning = yolo_service.generate_warning_text(obstacles)
        full_reply = f"{warning}。{llm_response['reply']}"
    else:
        full_reply = llm_response['reply']

    audio_url = await tts_service.text_to_speech(full_reply, "test_session")
    print(f"  生成音频: {audio_url}")


    result = {
        "success": True,
        "message": full_reply,
        "audioUrl": audio_url,
        "obstacles": [
            {
                "type": obs.type,
                "distance": obs.distance,
                "direction": obs.direction,
                "confidence": obs.confidence
            }
            for obs in obstacles
        ],
        "safetyLevel": safety_level,
        "navState": llm_response['nav_state'],
        "navData": llm_response.get('data', {})
    }

    print(f"\n成功: {result['success']}")
    print(f"消息: {result['message']}")
    print(f"音频: {result['audioUrl']}")
    print(f"障碍物: {len(result['obstacles'])} 个")
    print(f"⚠安全等级: {result['safetyLevel']}/5")
    print(f"导航状态: {result['navState']}")

    return result

if __name__ == "__main__":
    result = asyncio.run(test_complete_flow())
