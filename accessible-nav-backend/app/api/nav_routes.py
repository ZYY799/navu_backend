"""
导航服务API路由
"""
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, HTTPException
from app.models.schemas import (
    PerceptionBatchRequest, PerceptionBatchResponse,
    NavStartRequest, NavStartResponse,
    WSMessage
)
from app.services.yolo_service import YOLOService
from app.services.amap_service import AmapService
from app.services.llm_service import LLMService
from app.services.tts_service import TTSService
from app.core.session_manager import session_manager
from app.core.websocket_manager import websocket_manager
import time
import asyncio

router = APIRouter()
yolo_service = YOLOService()
amap_service = AmapService()
llm_service = LLMService()
tts_service = TTSService()


@router.post("/perception/batch", response_model=PerceptionBatchResponse)
async def process_perception_batch(request: PerceptionBatchRequest):
    """
    处理感知批次数据
    
    输入:
    - 3张图片 (Base64)
    - 当前位置
    
    输出:
    - 障碍物检测结果
    - 道路状况
    - AI指路建议
    """
    try:
        # YOLO检测
        detection_results = await yolo_service.detect_batch(request.images)
        
        # 整合障碍物信息
        obstacles = yolo_service.aggregate_obstacles(detection_results)
        
        # 评估安全等级
        safety_level = yolo_service.calculate_safety_level(obstacles)
        
        # LLM生成指路建议
        ai_guidance = await llm_service.generate_guidance(
            obstacles=obstacles,
            location=request.location
        )
        
        # TTS生成提醒
        audio_url = None
        if obstacles:
            warning_text = yolo_service.generate_warning_text(obstacles)
            audio_url = await tts_service.text_to_speech(
                text=warning_text,
                session_id=request.navSessionId
            )
        
        return PerceptionBatchResponse(
            success=True,
            obstacles=obstacles,
            roadCondition=yolo_service.describe_road_condition(obstacles),
            safetyLevel=safety_level,
            aiGuidance=ai_guidance,
            audioUrl=audio_url
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/start", response_model=NavStartResponse)
async def start_navigation(request: NavStartRequest):
    """
    开始导航
    
    流程:
    1. 创建导航会话
    2. 调用高德API规划路径
    3. 生成多条路线选项
    4. 返回WebSocket连接URL
    """
    try:
        # 创建导航会话
        nav_session = session_manager.create_navigation(
            nav_session_id=f"nav_{int(time.time() * 1000)}",
            user_id=request.userId,
            origin=request.origin,
            destination=request.destination
        )
        
        # 路径规划
        routes = await amap_service.plan_walking_route(
            origin=request.origin or request.destination,  # 如果没有起点，使用目的地
            destination=request.destination
        )
        
        # 生成提示音频
        message = f"已为您规划{len(routes)}条路线，请选择一条开始导航"
        audio_url = await tts_service.text_to_speech(
            text=message,
            session_id=nav_session.navSessionId
        )
        
        # 构建WebSocket URL
        ws_url = f"ws://localhost:8000/v1/nav/stream?navSessionId={nav_session.navSessionId}"
        
        return NavStartResponse(
            success=True,
            navSessionId=nav_session.navSessionId,
            routes=routes,
            message=message,
            wsUrl=ws_url,
            audioUrl=audio_url
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.websocket("/stream")
async def navigation_stream(websocket: WebSocket, navSessionId: str):
    """
    导航实时推送WebSocket
    
    事件类型:
    - NAV_STARTED: 导航开始
    - NAV_INSTRUCTION: 导航指令
    - OBSTACLE_WARNING: 障碍预警
    - ROUTE_DEVIATION: 路线偏离
    - NAV_COMPLETED: 导航完成
    """
    await websocket_manager.connect(websocket, navSessionId)
    
    try:
        # 发送连接成功消息
        await websocket_manager.send_message(
            nav_session_id=navSessionId,
            message_type="NAV_STARTED",
            data={"message": "导航已开始"}
        )
        
        # 保持连接并处理客户端消息
        while True:
            try:
                data = await asyncio.wait_for(
                    websocket.receive_json(),
                    timeout=30.0
                )
                
                # 处理客户端消息（心跳、位置更新等）
                if data.get("type") == "PING":
                    await websocket_manager.send_message(
                        nav_session_id=navSessionId,
                        message_type="PONG",
                        data={}
                    )
                elif data.get("type") == "LOCATION_UPDATE":
                    # 更新位置并检查是否需要重新规划
                    location = data.get("location")
                    # 这里可以添加偏航检测逻辑
                    pass
                    
            except asyncio.TimeoutError:
                # 30秒没收到消息，发送心跳
                await websocket_manager.send_message(
                    nav_session_id=navSessionId,
                    message_type="HEARTBEAT",
                    data={}
                )
                
    except WebSocketDisconnect:
        websocket_manager.disconnect(navSessionId)
    except Exception as e:
        print(f"WebSocket error: {e}")
        websocket_manager.disconnect(navSessionId)
