"""
LLM服务 - 对话理解与生成
"""
from typing import Dict, Any, List
from config.settings import settings
import json


class LLMService:
    """LLM服务类"""
    
    def __init__(self):
        self.api_key = settings.LLM_API_KEY
        self.model = settings.LLM_MODEL
        self.mock_mode = settings.MOCK_MODE
    
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
        
        # 真实LLM调用
        try:
            # 这里可以调用OpenAI/Anthropic/通义千问等API
            # 示例使用OpenAI格式
            import openai
            
            client = openai.OpenAI(
                api_key=self.api_key,
                base_url=settings.LLM_API_BASE
            )
            
            messages = self._build_messages(session.history, user_message)
            
            response = client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=settings.LLM_TEMPERATURE,
                max_tokens=settings.LLM_MAX_TOKENS
            )
            
            reply = response.choices[0].message.content
            
            # 解析回复，提取结构化信息
            parsed = self._parse_llm_reply(reply)
            
            return {
                "reply": parsed.get("reply", reply),
                "nav_state": parsed.get("nav_state"),
                "data": parsed.get("data", {})
            }
            
        except Exception as e:
            print(f"LLM调用失败: {e}")
            return self._mock_llm_response(user_message, session)
    
    def _build_messages(
        self,
        history: List[Dict],
        user_message: str
    ) -> List[Dict]:
        """构建LLM消息列表"""
        system_prompt = """你是一个为老年人设计的导航助手。
你的任务是：
1. 理解用户的导航需求（去哪里）
2. 提取起点和终点信息
3. 如果信息不完整，友好地询问
4. 确认后返回JSON格式：{"origin": {...}, "destination": {...}, "confirmed": true}

特点：
- 语言简洁友好
- 耐心重复
- 避免复杂术语
"""
        
        messages = [{"role": "system", "content": system_prompt}]
        messages.extend(history[-10:])  # 只保留最近10轮对话
        messages.append({"role": "user", "content": user_message})
        
        return messages
    
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
