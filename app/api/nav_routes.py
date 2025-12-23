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

def _parse_polyline_points(polyline: str) -> list[dict]:
    # "lng,lat;lng,lat;..." -> [{"lat":..,"lng":..}, ...]
    out: list[dict] = []
    if not isinstance(polyline, str) or not polyline.strip():
        return out
    for seg in polyline.split(";"):
        seg = seg.strip()
        if not seg or "," not in seg:
            continue
        try:
            lng_s, lat_s = seg.split(",", 1)
            out.append({"lat": float(lat_s), "lng": float(lng_s)})
        except Exception:
            continue
    return out

def _haversine_m(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    import math
    R = 6371000.0
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dl = math.radians(lng2 - lng1)
    a = (math.sin(dphi/2)**2 +
         math.cos(phi1)*math.cos(phi2)*(math.sin(dl/2)**2))
    c = 2*math.atan2(math.sqrt(a), math.sqrt(1-a))
    return R * c

def _remaining_distance_along(points: list[dict], start_idx: int) -> int:
    # 近似：把 idx..end 的点段距离累加
    if not points or start_idx >= len(points) - 1:
        return 0
    total = 0.0
    for i in range(start_idx, len(points) - 1):
        p1, p2 = points[i], points[i+1]
        total += _haversine_m(p1["lat"], p1["lng"], p2["lat"], p2["lng"])
    return int(total)

def _find_nearest_idx(points: list[dict], loc: dict) -> int:
    if not points or not loc:
        return 0
    best_i = 0
    best_d = float("inf")
    lat, lng = float(loc["lat"]), float(loc["lng"])
    for i, p in enumerate(points):
        d = _haversine_m(lat, lng, p["lat"], p["lng"])
        if d < best_d:
            best_d = d
            best_i = i
    return best_i


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
def _build_step_cumdist(steps: list[dict]) -> list[int]:
    # steps: [{"instruction":..., "distance":int, ...}, ...]
    cum: list[int] = []
    s = 0
    for st in steps or []:
        try:
            s += int(st.get("distance", 0) or 0)
        except Exception:
            pass
        cum.append(s)
    return cum

def _pick_step_index(total_dist: int, remaining_dist: int, cum: list[int]) -> int:
    # 用“已走距离”定位在哪个 step
    walked = max(0, total_dist - remaining_dist)
    for i, c in enumerate(cum):
        if walked <= c:
            return i
    return max(0, len(cum) - 1)


def dump_obj(o):
    # pydantic v2
    if hasattr(o, "model_dump"):
        try:
            return o.model_dump()
        except Exception:
            pass
    # pydantic v1
    if hasattr(o, "dict"):
        try:
            return o.dict()
        except Exception:
            pass
    # plain dict-like
    if isinstance(o, dict):
        return o
    # last resort
    try:
        return dict(o)
    except Exception:
        return {"_repr": repr(o)}
    
def _downsample_points(points: list[dict], max_n: int = 80) -> list[dict]:
    if not points or len(points) <= max_n:
        return points
    step = max(1, len(points) // max_n)
    out = points[::step]
    if out[-1] != points[-1]:
        out.append(points[-1])
    return out

def _min_dist_to_points(loc: dict, pts: list[dict]) -> float:
    # 简化版：loc 到 pts 中最近点的距离（米）
    if not pts:
        return float("inf")
    best = float("inf")
    for p in pts:
        d = _haversine_m(float(loc["lat"]), float(loc["lng"]), p["lat"], p["lng"])
        if d < best:
            best = d
    return best

def _build_step_points(steps: list[dict], max_points_per_step: int = 60) -> list[list[dict]]:
    step_pts: list[list[dict]] = []
    for st in steps or []:
        pl = (st.get("polyline") or "").strip()
        pts = _parse_polyline_points(pl) if pl else []
        pts = _downsample_points(pts, max_points_per_step)
        step_pts.append(pts)
    return step_pts

def _pick_step_index_by_polyline(loc: dict, step_points: list[list[dict]]) -> int:
    # 找“loc 最近的 step”
    best_i = -1
    best_d = float("inf")
    for i, pts in enumerate(step_points):
        if not pts:
            continue
        d = _min_dist_to_points(loc, pts)
        if d < best_d:
            best_d = d
            best_i = i
    return best_i


# -----------------------------
# 后台：指令循环（你原来缺的核心）
# -----------------------------

async def nav_instruction_loop(nav_session_id: str) -> None:
    print(f"[LOOP][START] navSessionId={nav_session_id}")

    # 先确认 WS 已连上（否则直接退出）
    hello_text = "导航已启动，我会根据您的位置持续播报指引。"
    hello_audio = await tts_service.text_to_speech(text=hello_text, session_id=nav_session_id)
    ok0 = await websocket_manager.send_message(
        nav_session_id=nav_session_id,
        message_type="NAV_INSTRUCTION",
        data={
            "text": hello_text,
            "audioUrl": hello_audio,
            "remainingDistance": 0,
            "remainingTime": 0,
        },
    )
    if not ok0:
        print(f"[LOOP][ABORT] no ws connection for {nav_session_id}")
        return

    last_step_idx: int = -1
    last_sent_text: str = ""
    last_loc_seen_at: int = 0
    tts_cache: Dict[str, str] = {}
    try:
        while True:
            await asyncio.sleep(1.0)  # ✅ 真 loop 建议 1s tick（指令节流由“step变化”控制）

            nav = session_manager.get_navigation(nav_session_id)
            if nav is None:
                print(f"[LOOP][STOP] session missing navSessionId={nav_session_id}")
                return

            if nav.state in [NavState.ARRIVED, NavState.CANCELLED]:
                print(f"[LOOP][STOP] state={nav.state} navSessionId={nav_session_id}")
                return

            route_data = nav.routeData or {}
            active = route_data.get("activeRoute") if isinstance(route_data, dict) else None
            if not isinstance(active, dict):
                # 没有路线：只能等（或发提示）
                await websocket_manager.send_message(
                    nav_session_id=nav_session_id,
                    message_type="NAV_INSTRUCTION",
                    data={
                        "text": "路线数据尚未准备好，请稍候。",
                        "audioUrl": None,
                        "remainingDistance": 0,
                        "remainingTime": 0,
                    },
                )
                continue

            # 取路线信息
            total_dist = int(active.get("distance", 0) or 0)
            steps = active.get("steps") or []
            polyline = (active.get("polyline") or active.get("polylineStr") or "").strip()
            points = _parse_polyline_points(polyline)

            # 必须有定位才能推进
            if not isinstance(nav.currentLocation, dict) or "lat" not in nav.currentLocation or "lng" not in nav.currentLocation:
                # 每隔几秒提醒一次（避免刷屏）
                if now_ms() - last_loc_seen_at > 4000:
                    last_loc_seen_at = now_ms()
                    await websocket_manager.send_message(
                        nav_session_id=nav_session_id,
                        message_type="NAV_INSTRUCTION",
                        data={
                            "text": "我还没收到您的定位，请打开定位权限并保持在室外。",
                            "audioUrl": None,
                            "remainingDistance": total_dist,
                            "remainingTime": int(total_dist / 1.2) if total_dist > 0 else 0,
                        },
                    )
                continue

            loc = nav.currentLocation

            # 估算剩余距离/时间
            if points:
                near_idx = _find_nearest_idx(points, loc)
                remaining = _remaining_distance_along(points, near_idx)
            else:
                # 兜底：用 total_dist（不精准但可用）
                remaining = total_dist

            remaining_time = int(remaining / 1.2)  # 1.2m/s 兜底步行速度

            # 到达判定（你也可以换成 settings.ARRIVE_THRESHOLD）
            if remaining <= 15:
                session_manager.update_navigation_state(nav_session_id, NavState.ARRIVED)
                await websocket_manager.send_message(
                    nav_session_id=nav_session_id,
                    message_type="NAV_INSTRUCTION",
                    data={
                        "text": "已到达目的地。导航结束。",
                        "audioUrl": None,
                        "remainingDistance": 0,
                        "remainingTime": 0,
                    },
                )
                return

            # 选 step（只在 step 变化时推一次指令）
            cache = (route_data.get("_cache") or {}) if isinstance(route_data, dict) else {}
            step_points = cache.get("stepPoints") or []
            route_points = cache.get("routePoints") or []

            # 没缓存就兜底现算一次（避免线上突然空）
            if not step_points:
                step_points = _build_step_points(steps, max_points_per_step=60)

            # 1) 用 step.polyline 找最近 step
            step_idx = _pick_step_index_by_polyline(loc, step_points)

            # 2) remaining 仍然用 route-level polyline（更连续）
            if route_points:
                near_idx = _find_nearest_idx(route_points, loc)
                remaining = _remaining_distance_along(route_points, near_idx)
            else:
                # 没缓存就用你旧逻辑 points
                if points:
                    near_idx = _find_nearest_idx(points, loc)
                    remaining = _remaining_distance_along(points, near_idx)
                else:
                    remaining = total_dist

            text = ""
            if 0 <= step_idx < len(steps):
                text = (steps[step_idx].get("instruction") or "").strip()

            if not text:
                text = "请继续沿路线前进。"

            # ✅ 节流：step 变了 或者 text 变了才发
            if step_idx != last_step_idx or text != last_sent_text:
                last_step_idx = step_idx
                last_sent_text = text
                # ✅ 给主导航指令生成音频（缓存避免重复合成）
                audio_url: Optional[str] = None
                try:
                    if text in tts_cache:
                        audio_url = tts_cache[text]
                    else:
                        audio_url = await tts_service.text_to_speech(text=text, session_id=nav_session_id)
                        if audio_url:
                            tts_cache[text] = audio_url
                except Exception:
                    audio_url = None
                ok = await websocket_manager.send_message(
                    nav_session_id=nav_session_id,
                    message_type="NAV_INSTRUCTION",
                    data={
                        "text": text,
                        "audioUrl": audio_url,
                        "remainingDistance": int(remaining),
                        "remainingTime": int(remaining_time),
                    },
                )
                if not ok:
                    print(f"[LOOP][ABORT] disconnected navSessionId={nav_session_id}")
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
        warning_text = ""   # ✅ 避免后面引用未定义
        if obstacles:
            warning_text = yolo_service.generate_warning_text(obstacles)
            audio_url = await tts_service.text_to_speech(
                text=warning_text,
                session_id=request.navSessionId
            )

        # ✅ 1) 写入导航会话快照（给主导航/LLM增强/调试用）
        nav = None  # ✅ 作用域固定
        try:
            nav = session_manager.get_navigation(request.navSessionId)
            if nav is not None:
                nav.lastPerceptionAt = now_ms()
                nav.lastSafetyLevel = int(safety_level)
                nav.lastRoadCondition = yolo_service.describe_road_condition(obstacles)
                nav.lastAiGuidance = ai_guidance or ""
                nav.lastObstacles = [dump_obj(o) for o in (obstacles or [])]

                if obstacles:
                    nav.lastWarningText = warning_text
                    nav.lastWarningAudioUrl = audio_url

                nav.updatedAt = now_ms()
        except Exception:
            # 不影响主流程
            pass

        # ✅ 2) 如果有障碍物：同时推 WS 预警（统一进 seq & 抢占播放）
        if obstacles:
            try:
                await websocket_manager.send_message(
                    nav_session_id=request.navSessionId,
                    message_type="OBSTACLE_WARNING",
                    data={
                        "text": warning_text,
                        "audioUrl": audio_url,
                        "safetyLevel": int(safety_level),
                        "obstacles": (nav.lastObstacles if (nav is not None and nav.lastObstacles) else []),
                    },
                )
            except Exception:
                # WS 推送失败也不影响 HTTP
                pass

        # ✅ 保持你原有 HTTP 输出（这里建议把字段补全，不然前端 fromPerception 可能拿不到）
        road_condition = yolo_service.describe_road_condition(obstacles)
        return PerceptionBatchResponse(
            success=True,
            obstacles=obstacles,
            roadCondition=road_condition,
            safetyLevel=int(safety_level),
            aiGuidance=ai_guidance,
            audioUrl=audio_url,
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    
# -----------------------------
# POST /v1/nav/start
# -----------------------------
@router.post("/start", response_model=NavStartResponse)
async def start_navigation(request: NavStartRequest, req: Request):
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
        if request.origin is None:
            raise HTTPException(status_code=400, detail="origin is required (lat/lng).")
            
        origin = request.origin

        # 路径规划
        routes = await amap_service.plan_walking_route(
            origin=origin,
            destination=request.destination
        )
        # ✅ 默认选第一条路线（route_0）
        active_route = routes[0] if routes else None
        if active_route:
            # 存 routeId
            nav_session.routeId = active_route.get("routeId")

            # ✅ 1) 预先缓存 stepPoints（用于更准的“当前 step”判断）
            steps = active_route.get("steps") or []
            step_points = _build_step_points(steps, max_points_per_step=60)

            # ✅ 2) 预先缓存 routePoints（用于 remainingDistance 最近点/剩余距离）
            polyline = (active_route.get("polyline") or active_route.get("polylineStr") or "").strip()
            route_points_raw = _parse_polyline_points(polyline)
            route_points = _downsample_points(route_points_raw, max_n=800)

            # 存 routeData（给 loop 用）
            nav_session.routeData = {
                "activeRoute": active_route,  # 原样保留
                "routes": routes,             # 原样保留
                "_cache": {                   # ✅ 新增：内部缓存
                    "stepPoints": step_points,
                    "routePoints": route_points,
                }
            }
            nav_session.updatedAt = now_ms()

        
        # 生成提示音频
        message = f"已为您规划{len(routes)}条路线，请选择一条开始导航"
        audio_url = await tts_service.text_to_speech(
            text=message,
            session_id=nav_session.navSessionId
        )
        
        # 构建WebSocket URL
        ws_url = build_ws_url(req, nav_session.navSessionId)
        
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