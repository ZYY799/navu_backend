"""
语音交互API路由
"""
from fastapi import APIRouter, HTTPException
from app.models.schemas import VoiceTextRequest, VoiceTextResponse
from app.services.llm_service import LLMService
from app.services.tts_service import TTSService
from app.core.session_manager import session_manager
import time

router = APIRouter()
llm_service = LLMService()
tts_service = TTSService()


@router.post("/text", response_model=VoiceTextResponse)
async def process_voice_text(request: VoiceTextRequest):
    """
    处理语音识别文本
    
    流程:
    1. 获取会话历史
    2. LLM分析用户意图
    3. 更新会话状态
    4. 生成TTS音频
    5. 返回响应
    """
    try:
        # 获取会话
        session = session_manager.get_conversation(request.sessionId)
        if not session:
            session = session_manager.create_conversation(
                request.sessionId,
                request.userId
            )
        
        # LLM处理
        llm_response = await llm_service.process_conversation(
            user_message=request.text,
            session=session
        )
        
        # 更新会话历史
        session.history.append({"role": "user", "content": request.text})
        session.history.append({"role": "assistant", "content": llm_response["reply"]})
        session.updatedAt = int(time.time() * 1000)
        
        # 生成TTS音频
        audio_url = None
        if llm_response["reply"]:
            audio_url = await tts_service.text_to_speech(
                text=llm_response["reply"],
                session_id=request.sessionId
            )
        
        return VoiceTextResponse(
            success=True,
            message=llm_response["reply"],
            audioUrl=audio_url,
            navState=llm_response.get("nav_state"),
            data=llm_response.get("data", {})
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
