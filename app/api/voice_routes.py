"""
语音交互API路由
"""
from fastapi import APIRouter, HTTPException
from app.models.schemas import VoiceTextRequest, VoiceTextResponse
from app.services.llm_service import LLMService
from app.services.tts_service import TTSService
from app.core.session_manager import session_manager
from config.settings import settings
import time
import json  # ✅
router = APIRouter()
llm_service = LLMService()
tts_service = TTSService()


@router.post("/text", response_model=VoiceTextResponse)
async def process_voice_text(request: VoiceTextRequest):
    print("[voice/text] MOCK_MODE =", settings.MOCK_MODE)

    try:
        # ✅ 入参日志（Pydantic v2: model_dump；v1: dict）
        req_dict = request.model_dump() if hasattr(request, "model_dump") else request.dict()
        print("[voice/text][REQ] raw =", json.dumps(req_dict, ensure_ascii=False))

        # 获取/创建会话
        session = session_manager.get_conversation(request.sessionId)
        if not session:
            session = session_manager.create_conversation(request.sessionId, request.userId)

        # ✅ 把前端 location 存到 session.context（用于后续 LLM）
        # 前提：schemas.py 里 VoiceTextRequest 要有 location 字段
        if getattr(request, "location", None):
            session.context["last_location"] = request.location

        # LLM 处理
        llm_response = await llm_service.process_conversation(
            user_message=request.text,
            session=session
        )

        # 更新会话历史
        session.history.append({"role": "user", "content": request.text})
        session.history.append({"role": "assistant", "content": llm_response.get("reply", "")})
        session.updatedAt = int(time.time() * 1000)

        # 生成 TTS
        audio_url = None
        reply_text = llm_response.get("reply", "")
        if reply_text:
            audio_url = await tts_service.text_to_speech(
                text=reply_text,
                session_id=request.sessionId
            )

        resp = VoiceTextResponse(
            success=True,
            message=reply_text,
            audioUrl=audio_url,
            navState=llm_response.get("nav_state"),
            data=llm_response.get("data", {})
        )

        # ✅ 返回前打印响应（这句才会生效）
        resp_dict = resp.model_dump() if hasattr(resp, "model_dump") else resp.dict()
        print("[voice/text][RESP] out =", json.dumps(resp_dict, ensure_ascii=False))

        return resp

    except Exception as e:
        print("[voice/text][ERR] ", str(e))
        raise HTTPException(status_code=500, detail=str(e))