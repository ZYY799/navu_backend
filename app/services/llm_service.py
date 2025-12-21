"""
LLM服务 - 对话理解与生成
"""
from typing import Dict, Any, List, Optional
from config.settings import settings
import json
import re
from typing import Optional, Tuple

class LLMService:
    """LLM服务类"""

    def __init__(self):
        self.api_key = settings.LLM_API_KEY
        self.model = settings.LLM_MODEL
        self.mock_mode = settings.MOCK_MODE
        self.amap_service = None  # 延迟初始化，避免循环导入
    
    def _strip_dsml(self, reply: str) -> str:
        """把 DSML 工具调用痕迹从回复中裁掉（前端不会看到中间过程）"""
        if not reply:
            return reply

        # 兼容两种 DSML 标记：<｜DSML｜... 和 <|DSML|...
        markers = ["<｜DSML｜", "<|DSML|"]
        cut_pos = -1
        for m in markers:
            p = reply.find(m)
            if p != -1:
                cut_pos = p if cut_pos == -1 else min(cut_pos, p)
                
        if cut_pos != -1:
            head = reply[:cut_pos].strip()
            # ✅ 如果 DSML 在开头导致 head 为空，就别裁（至少别返回空）
            if head:
                return head
            return reply.strip()

        return reply

    def _extract_dsml_search_poi(self, reply: str) -> Optional[Tuple[str, str]]:
        # very KISS：只处理 search_poi 这一种
        if 'invoke name="search_poi"' not in reply:
            return None
        m1 = re.search(r'parameter name="poi_name"[^>]*>(.*?)</', reply)
        m2 = re.search(r'parameter name="city"[^>]*>(.*?)</', reply)
        poi = (m1.group(1).strip() if m1 else "")
        city = (m2.group(1).strip() if m2 else "上海")
        if poi:
            return (poi, city)
        return None
    
    async def process_conversation(
        self,
        user_message: str,
        session: Any
    ) -> Dict[str, Any]:
        """
        处理对话消息

        Returns:
            {
                "reply": "系统回复",
                "nav_state": "asking/navigating/arrived",
                "data": {...}  # 解析的起终点等信息
            }
        """
        if self.mock_mode:
            return self._mock_llm_response(user_message, session)

        # 真实LLM调用，带工具调用支持
        try:
            import openai

            client = openai.OpenAI(
                api_key=self.api_key,
                base_url=settings.LLM_API_BASE
            )

            messages = self._build_messages(session.history, user_message, session)
            tools = self._get_tools_definition()

            last_loc: Optional[Dict[str, float]] = None
            try:
                last_loc = session.context.get("last_location")
            except Exception:
                last_loc = None

            # 第一次调用LLM
            response = client.chat.completions.create(
                model=self.model,
                messages=messages,
                tools=tools,
                tool_choice="auto",
                temperature=settings.LLM_TEMPERATURE,
                max_tokens=settings.LLM_MAX_TOKENS
            )

            assistant_message = response.choices[0].message

            print("[LLM] tool_calls =", getattr(assistant_message, "tool_calls", None))
            print("[LLM] content(head) =", (assistant_message.content or "")[:200])

            # 检查是否需要调用工具
            if assistant_message.tool_calls:
                # 执行工具调用
                messages.append(assistant_message)

                merged_data: Dict[str, Any] = {}
                destination: Optional[Dict[str, float]] = None
                destination_name: Optional[str] = None
                route_preview: Optional[Dict[str, Any]] = None

                for tool_call in assistant_message.tool_calls:
                    function_name = tool_call.function.name
                    function_args = json.loads(tool_call.function.arguments)

                    if function_name == "plan_route" and isinstance(function_args, dict):
                        if "origin" not in function_args and last_loc:
                            function_args["origin"] = last_loc

                    # 执行工具
                    function_response = await self._execute_tool(
                        function_name,
                        function_args
                    )
                    print(f"[TOOL] {function_name} args = {function_args}")
                    print(f"[TOOL] {function_name} resp = {json.dumps(function_response, ensure_ascii=False)[:800]}")

                    if isinstance(function_response, dict):
                        # search_poi 返回 { success, poi: { name, location:{lat,lng} } }
                        poi = function_response.get("poi")
                        if isinstance(poi, dict):
                            loc = poi.get("location")
                            if isinstance(loc, dict) and "lat" in loc and "lng" in loc:
                                destination = {"lat": float(loc["lat"]), "lng": float(loc["lng"])}
                                destination_name = str(poi.get("name")) if poi.get("name") else destination_name

                        # plan_route 返回 { success, route: {...} }
                        if function_response.get("success") is True and "route" in function_response:
                            r = function_response.get("route")
                            if isinstance(r, dict):
                                route_preview = r

                    # 添加工具返回结果
                    messages.append({
                        "role": "tool",
                        "tool_call_id": tool_call.id,
                        "name": function_name,
                        "content": json.dumps(function_response, ensure_ascii=False)
                    })

                # 第二次调用LLM，让它基于工具结果生成最终回复
                second_response = client.chat.completions.create(
                    model=self.model,
                    messages=messages,
                    temperature=settings.LLM_TEMPERATURE,
                    max_tokens=settings.LLM_MAX_TOKENS
                )

                reply = self._strip_dsml(second_response.choices[0].message.content or "")

                if destination:
                    merged_data["destination"] = destination
                if destination_name:
                    merged_data["destinationName"] = destination_name
                if route_preview:
                    merged_data["routePreview"] = route_preview
                if last_loc:
                    merged_data["origin"] = last_loc

                return {
                    "reply": reply,
                    "nav_state": "navigating" if destination else "asking",
                    "data": merged_data
                }
            
            else:
                # 无需调用工具，直接返回
                reply = assistant_message.content or ""

                # ✅ DSML 兜底：模型把工具调用写进了文本（不是 tool_calls）
                hit = self._extract_dsml_search_poi(reply)
                if hit:
                    poi_name, city = hit
                    poi_res = await self._tool_search_poi({"poi_name": poi_name, "city": city})

                    # 构造输出 data：把 origin / destination 都补齐
                    data_out: Dict[str, Any] = {}
                    # 如果 voice_routes.py 里把 last_location 存进 session.context，这里就能取到
                    last_loc = session.context.get("last_location") if hasattr(session, "context") else None
                    if last_loc:
                        data_out["origin"] = last_loc

                    if poi_res.get("success") and poi_res.get("poi") and poi_res["poi"].get("location"):
                        data_out["destination"] = poi_res["poi"]["location"]

                        # ✅ 前端只看到“干净文案”，中间 DSML 不会显示
                        clean_reply = f"我已找到「{poi_res['poi'].get('name', poi_name)}」的位置。现在要开始导航吗？"
                        return {
                            "reply": clean_reply,
                            "nav_state": "asking",   # KISS：先让用户确认；你也可以直接 navigating
                            "data": data_out
                        }

                    # POI 没搜到：也要把 DSML 裁掉再返回
                    clean_reply = self._strip_dsml(reply)
                    if not clean_reply:
                        clean_reply = f"我没找到「{poi_name}」的准确位置。可以换一个更具体的名称吗？"
                    return {"reply": clean_reply, "nav_state": "asking", "data": data_out}

                # ✅ 没命中 DSML：正常解析 / 原逻辑
                reply = self._strip_dsml(reply)  # 即便没 DSML，也不坏
                parsed = self._parse_llm_reply(reply)

                return {
                    "reply": parsed.get("reply", reply),
                    "nav_state": parsed.get("nav_state", "asking"),
                    "data": parsed.get("data", {})
                }

        except Exception as e:
            print(f"LLM调用失败: {e}")
            import traceback
            traceback.print_exc()
            return self._mock_llm_response(user_message, session)
    
    def _build_messages(self, history: List[Dict], user_message: str, session: Any) -> List[Dict]:
        """构建LLM消息列表"""
        system_prompt = """你是一个为老年人和视障人士设计的导航助手。
你的任务是：
1. 理解用户的导航需求（去哪里）
2. 如果用户提供了起点和终点，使用 plan_route 工具规划路线
3. 如果已知用户当前位置坐标，则直接把它作为 origin
4. 如果信息不完整，友好地询问
5. 基于路线规划结果，用简洁的语言告诉用户

特点：
- 语言简洁友好，适合老年人理解
- 耐心重复
- 避免复杂术语
- 主动使用工具获取实时路线信息
"""

        messages = [{"role": "system", "content": system_prompt}]
        last_loc = None
        try:
            last_loc = getattr(session, "context", {}).get("last_location")
        except Exception:
            last_loc = None

        if isinstance(last_loc, dict) and "lat" in last_loc and "lng" in last_loc:
            messages.append({
                "role": "system",
                "content": (
                    f"已知用户当前位置坐标：lat={last_loc['lat']}, lng={last_loc['lng']}。"
                    f"当需要起点(origin)时，直接使用该坐标作为 origin，"
                    f"不要再询问“您现在在哪里”。只有当没有任何 location 时才询问。"
                )
            })
        messages.extend(history[-10:])  # 只保留最近10轮对话
        messages.append({"role": "user", "content": user_message})

        return messages

    def _get_tools_definition(self) -> List[Dict]:
        return [
            {
                "type": "function",
                "function": {
                    "name": "search_poi",
                    "description": "当用户提到要去某个地点/找某个地点，但没有提供坐标时，必须先调用本工具获得终点坐标。",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "poi_name": {"type": "string", "description": "地点名称"},
                            "city": {"type": "string", "description": "城市名称", "default": "北京"}
                        },
                        "required": ["poi_name"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "plan_route",
                    "description": "当已知起点(origin)和终点(destination)坐标时，需要规划路线时，必须调用本工具规划步行路线。",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "origin": {
                                "type": "object",
                                "properties": {"lat": {"type": "number"}, "lng": {"type": "number"}},
                                "required": ["lat", "lng"]
                            },
                            "destination": {
                                "type": "object",
                                "properties": {"lat": {"type": "number"}, "lng": {"type": "number"}},
                                "required": ["lat", "lng"]
                            }
                        },
                        "required": ["origin", "destination"]
                    }
                }
            },
        ]

    async def _execute_tool(
        self,
        function_name: str,
        function_args: Dict
    ) -> Dict:
        """执行工具调用"""
        if function_name == "plan_route":
            return await self._tool_plan_route(function_args)
        elif function_name == "search_poi":
            return await self._tool_search_poi(function_args)
        else:
            return {"error": f"未知工具: {function_name}"}

    async def _tool_plan_route(self, args: Dict) -> Dict:
        """工具: 规划路线"""
        try:
            # 延迟导入，避免循环依赖
            if self.amap_service is None:
                from app.services.amap_service import AmapService
                self.amap_service = AmapService()

            origin = args["origin"]
            destination = args["destination"]

            routes = await self.amap_service.plan_walking_route(origin, destination)

            if routes:
                route = routes[0]  # 使用第一条推荐路线
                return {
                    "success": True,
                    "route": {
                        "name": route.get("name"),
                        "distance": route.get("distance"),
                        "duration": route.get("duration"),
                        "steps": route.get("steps", [])[:3],  # 只返回前3步
                        "accessibility_score": route.get("accessibilityScore")
                    }
                }
            else:
                return {
                    "success": False,
                    "error": "未找到路线"
                }

        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }

    async def _tool_search_poi(self, args: Dict) -> Dict:
        """工具: 搜索地点坐标（真实高德 POI 搜索）"""
        try:
            if self.amap_service is None:
                from app.services.amap_service import AmapService
                self.amap_service = AmapService()

            poi_name = (args.get("poi_name") or "").strip()
            city = (args.get("city") or "").strip() or None

            if not poi_name:
                return {"success": False, "error": "poi_name empty"}

            r = await self.amap_service.search_poi_text(
                keywords=poi_name,
                city=city,
                limit=5,
            )

            if not r.get("success"):
                return {"success": False, "error": r.get("error", "search_poi failed")}

            poi = r["poi"]
            # ✅ 这里返回给 LLM/前端的统一结构
            return {
                "success": True,
                "poi": {
                    "name": poi.get("name", poi_name),
                    "location": {"lat": poi["lat"], "lng": poi["lng"]},
                    "address": poi.get("address", ""),
                    "adcode": poi.get("adcode", ""),
                },
                "candidates": [
                    {
                        "name": x.get("name", ""),
                        "location": {"lat": x["lat"], "lng": x["lng"]},
                        "address": x.get("address", ""),
                        "adcode": x.get("adcode", ""),
                    }
                    for x in (r.get("candidates") or [])
                ],
            }

        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def _parse_llm_reply(self, reply: str) -> Dict:
        """解析LLM回复，提取结构化信息"""
        # 尝试提取JSON
        try:
            if "```json" in reply:
                json_str = reply.split("```json")[1].split("```")[0].strip()
                data = json.loads(json_str)
                return {
                    "reply": reply.split("```json")[0].strip(),
                    "data": data,
                    "nav_state": "asking" if not data.get("confirmed") else "navigating"
                }
        except:
            pass
        
        return {"reply": reply, "nav_state": "asking", "data": {}}
    
    def _mock_llm_response(
        self,
        user_message: str,
        session: Any
    ) -> Dict[str, Any]:
        """模拟LLM响应（用于测试）"""
        message_lower = user_message.lower()
        
        if any(keyword in message_lower for keyword in ["超市", "商店", "买菜"]):
            return {
                "reply": "好的，我帮您查找附近的超市。请问您现在在哪里呢？",
                "nav_state": "asking",
                "data": {"destination_type": "supermarket"}
            }
        elif any(keyword in message_lower for keyword in ["医院", "看病"]):
            return {
                "reply": "明白了，我帮您找最近的医院。请告诉我您的具体位置。",
                "nav_state": "asking",
                "data": {"destination_type": "hospital"}
            }
        elif "确认" in message_lower or "开始" in message_lower:
            return {
                "reply": "好的，开始为您导航。",
                "nav_state": "navigating",
                "data": {"confirmed": True}
            }
        else:
            return {
                "reply": "我是您的导航助手，可以帮您规划路线。您想去哪里呢？",
                "nav_state": "asking",
                "data": {}
            }
    
    async def generate_guidance(
        self,
        obstacles: List[Any],
        location: Dict
    ) -> str:
        """生成AI指路建议"""
        if self.mock_mode:
            if obstacles:
                return f"前方{obstacles[0].distance:.1f}米处有{obstacles[0].type}，建议减速慢行。"
            return "前方道路通畅，请继续直行。"
        
        # 真实LLM生成指路建议
        # ... 类似上面的实现
        return "前方道路通畅，请继续直行。"
