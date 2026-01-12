"""
前端集成测试
模拟前端发送: 当前位置 + 语音文字 + 图片
"""
import asyncio
import base64
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


async def frontend_integration_test():

    from app.services.tts_service import TTSService
    from app.services.yolo_service import YOLOService
    from app.services.llm_service import LLMService
    from app.core.session_manager import session_manager


    # 前端输入 (模拟前端传来的三个变量)
    # 1. 当前位置
    current_location = {
        "lat": 39.916527,
        "lng": 116.397128
    }

    # 2. 语音识别后的文字
    voice_text = "我想去故宫"

    # 3. 摄像头拍摄的图片 (Base64编码)
    image_path = "test_fig/R-C.jpg"
    if os.path.exists(image_path):
        with open(image_path, 'rb') as f:
            image_bytes = f.read()
            image_base64 = base64.b64encode(image_bytes).decode('utf-8')
    else:
        print(f"测试图片不存在: {image_path}")
        return

    print("\n前端输入:")
    print(f"  位置: lat={current_location['lat']}, lng={current_location['lng']}")
    print(f"  文字: {voice_text}")
    print(f"  图片: {image_path} (已转Base64)")

    # 后端处理流程
    # 步骤1: 障碍物检测
    print("\n[1/3] YOLO障碍物检测...")
    yolo_service = YOLOService()
    detection_results = await yolo_service.detect_batch([image_base64])
    obstacles = yolo_service.aggregate_obstacles(detection_results)
    safety_level = yolo_service.calculate_safety_level(obstacles)

    print(f"  检测到 {len(obstacles)} 个障碍物")
    print(f"  安全等级: {safety_level}/5")
    if obstacles:
        for i, obs in enumerate(obstacles[:3], 1):
            print(f"     {i}. {obs.type} - {obs.distance}m - {obs.direction}")

    # 步骤2: LLM理解用户意图
    print("\n[2/3] LLM理解用户需求...")
    llm_service = LLMService()
    session = session_manager.create_conversation("test_user", "test_session")

    full_message = f"用户当前位置: {current_location['lat']}, {current_location['lng']}\n用户说: {voice_text}"
    llm_response = await llm_service.process_conversation(full_message, session)

    print(f"  LLM回复: {llm_response['reply'][:80]}...")
    print(f"  导航状态: {llm_response['nav_state']}")

    # 步骤3: 生成语音回复
    print("\n[3/3] 生成TTS语音...")
    tts_service = TTSService()

    if obstacles:
        warning = yolo_service.generate_warning_text(obstacles)
        final_reply = f"{warning}。{llm_response['reply']}"
    else:
        final_reply = llm_response['reply']

    audio_url = await tts_service.text_to_speech(final_reply, "test_session")
    print(f"  音频文件: {audio_url}")

    # 后端返回结果 (前端接收)

    backend_response = {
        "success": True,
        "message": final_reply,
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

    print(f"\n  success: {backend_response['success']}")
    print(f"  message: {backend_response['message']}")
    print(f"  audioUrl: {backend_response['audioUrl']}")
    print(f"  obstacles: {len(backend_response['obstacles'])} 个")
    print(f"  safetyLevel: {backend_response['safetyLevel']}/5")
    print(f"  navState: {backend_response['navState']}")

    return backend_response

if __name__ == "__main__":
    result = asyncio.run(frontend_integration_test())
