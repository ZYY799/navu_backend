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
import json

router = APIRouter()
llm_service = LLMService()
tts_service = TTSService()


@router.post("/text", response_model=VoiceTextResponse)
async def process_voice_text(request: VoiceTextRequest):
    print("[voice/text] MOCK_MODE =", settings.MOCK_MODE)

    try:
        req_dict = request.model_dump() if hasattr(request, "model_dump") else request.dict()
        print("[voice/text][REQ] raw =", json.dumps(req_dict, ensure_ascii=False))

        session = session_manager.get_conversation(request.sessionId)
        if not session:
            session = session_manager.create_conversation(request.sessionId, request.userId)

        if getattr(request, "location", None):
            session.context["last_location"] = request.location

        llm_response = await llm_service.process_conversation(
            user_message=request.text,
            session=session
        )

        session.history.append({"role": "user", "content": request.text})
        session.history.append({"role": "assistant", "content": llm_response.get("reply", "")})
        session.updatedAt = int(time.time() * 1000)

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

        resp_dict = resp.model_dump() if hasattr(resp, "model_dump") else resp.dict()
        print("[voice/text][RESP] out =", json.dumps(resp_dict, ensure_ascii=False))

        return resp

    except Exception as e:
        print("[voice/text][ERR] ", str(e))
        raise HTTPException(status_code=500, detail=str(e))