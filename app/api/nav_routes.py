"""
导航服务API路由
"""
import time
import asyncio
from typing import Dict, Any, Optional
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Request, HTTPException
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
from app.models.schemas import NavState


router = APIRouter()
yolo_service = YOLOService()
amap_service = AmapService()
llm_service = LLMService()
tts_service = TTSService()

# -----------------------------
# 工具函数
# -----------------------------

def now_ms() -> int:
    return int(time.time() * 1000)


def build_ws_url(req: Request, nav_session_id: str) -> str:
    """
    用请求 host + scheme 组装 wsUrl
    - http -> ws
    - https -> wss
    """
    host = req.headers.get("host", "")
    if not host:
        host = "127.0.0.1:8000"

    scheme = req.url.scheme  # "http" / "https"
    ws_scheme = "wss" if scheme == "https" else "ws"
    return f"{ws_scheme}://{host}/v1/nav/stream?navSessionId={nav_session_id}"


def to_latlng_dict(opt: Optional[Dict[str, float]]) -> Optional[Dict[str, float]]:
    """
    schemas 里 origin/destination/location 都是 {lat, lng}
    """
    if opt is None:
        return None
    if "lat" in opt and "lng" in opt:
        return {"lat": float(opt["lat"]), "lng": float(opt["lng"])}
    return None


# -----------------------------
# 后台：指令循环（你原来缺的核心）
# -----------------------------

async def nav_instruction_loop(nav_session_id: str) -> None:
    print(f"[LOOP][START] navSessionId={nav_session_id}")

    # ✅ 先立刻发一条，不要先 sleep
    ok0 = await websocket_manager.send_message(
        nav_session_id=nav_session_id,
        message_type="NAV_INSTRUCTION",
        data={
            "text": "（loop test）如果你看到这句，说明 loop 在工作。",
            "audioUrl": None,
            "remainingDistance": 500,
            "remainingTime": 420,
        },
    )
    print(f"[LOOP][SEND0] navSessionId={nav_session_id} ok={ok0}")
    if not ok0:
        print(f"[LOOP][ABORT] no ws connection for {nav_session_id}")
        return

    remaining_distance = 500
    remaining_time = 420
    step = 0

    try:
        while True:
            await asyncio.sleep(3.0)

            nav = session_manager.get_navigation(nav_session_id)
            if nav is None:
                print(f"[LOOP][STOP] session missing navSessionId={nav_session_id}")
                return

            if nav.state in [NavState.ARRIVED, NavState.CANCELLED]:
                print(f"[LOOP][STOP] state={nav.state} navSessionId={nav_session_id}")
                return

            step += 1
            remaining_distance = max(0, remaining_distance - 35)
            remaining_time = max(0, remaining_time - 25)

            ok = await websocket_manager.send_message(
                nav_session_id=nav_session_id,
                message_type="NAV_INSTRUCTION",
                data={
                    "text": f"（loop test）step={step} 请继续直行。",
                    "audioUrl": None,
                    "remainingDistance": remaining_distance,
                    "remainingTime": remaining_time,
                },
            )
            print(f"[LOOP][SEND] navSessionId={nav_session_id} ok={ok} step={step}")

            if not ok:
                print(f"[LOOP][ABORT] send failed (disconnected?) navSessionId={nav_session_id}")
                return
    except asyncio.CancelledError:
        print(f"[LOOP][CANCEL] navSessionId={nav_session_id}")
        return
    except Exception as e:
        print(f"[LOOP][ERROR] navSessionId={nav_session_id} err={e}")
        return


# -----------------------------
# POST /v1/nav/perception/batch
# -----------------------------

@router.post("/perception/batch", response_model=PerceptionBatchResponse)
async def process_perception_batch(request: PerceptionBatchRequest):
    print("[perception] HIT navSessionId=", request.navSessionId, "imgCount=", len(request.images))
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

# -----------------------------
# POST /v1/nav/start
# -----------------------------
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

        session_manager.update_navigation_state(nav_session.navSessionId, NavState.NAVIGATING)
        
        origin = request.origin if request.origin is not None else request.destination
        # 路径规划
        routes = await amap_service.plan_walking_route(
            origin=origin,
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


# -----------------------------
# WS /v1/nav/stream
# -----------------------------

@router.websocket("/stream")
async def navigation_stream(websocket: WebSocket, navSessionId: str):
    """
    你前端会上行：
    - {"type":"PING"}
    - {"type":"LOCATION_UPDATE","location":{"lat":..,"lng":..}}
    """
    print(f"[WS][ENTER] stream handler NEW_CODE navSessionId={navSessionId}")
    await websocket_manager.connect(websocket, navSessionId)

    nav_task: Optional[asyncio.Task] = None

    try:
        # 连接成功：NAV_STARTED（你日志里已经看到这个）
        await websocket_manager.send_message(
            nav_session_id=navSessionId,
            message_type="NAV_STARTED",
            data={"message": "导航已开始"},
        )

        # ✅ 核心：启动后台指令 loop（你之前的问题就在这里缺失）
        nav_task = asyncio.create_task(nav_instruction_loop(navSessionId))
        def _on_done(t: asyncio.Task) -> None:
            try:
                exc = t.exception()
                print(f"[WS][TASK_DONE] navSessionId={navSessionId} exc={exc}")
            except asyncio.CancelledError:
                print(f"[WS][TASK_DONE] navSessionId={navSessionId} cancelled")

        nav_task.add_done_callback(_on_done)
        print(f"[WS][TASK_START] navSessionId={navSessionId} task={nav_task}")
        while True:
            try:
                data: Dict[str, Any] = await asyncio.wait_for(websocket.receive_json(), timeout=30.0)
                print(f"[WS][RECV] navSessionId={navSessionId} data={data}")

                msg_type = data.get("type", "")

                if msg_type == "PING":
                    await websocket_manager.send_message(
                        nav_session_id=navSessionId,
                        message_type="PONG",
                        data={},
                    )
                    continue

                if msg_type == "LOCATION_UPDATE":
                    location = data.get("location")
                    if isinstance(location, dict) and ("lat" in location) and ("lng" in location):
                        nav = session_manager.get_navigation(navSessionId)
                        if nav is not None:
                            nav.currentLocation = {
                                "lat": float(location["lat"]),
                                "lng": float(location["lng"]),
                            }
                            nav.updatedAt = now_ms()
                    continue

                # 其他类型先忽略即可

            except asyncio.TimeoutError:
                # 30 秒没收到客户端上行：发 HEARTBEAT
                await websocket_manager.send_message(
                    nav_session_id=navSessionId,
                    message_type="HEARTBEAT",
                    data={},
                )

    except WebSocketDisconnect:
        websocket_manager.disconnect(navSessionId)

    except Exception as e:
        print(f"WebSocket error navSessionId={navSessionId} err={e}")
        websocket_manager.disconnect(navSessionId)

    finally:
        if nav_task is not None:
            nav_task.cancel()
        websocket_manager.disconnect(navSessionId)