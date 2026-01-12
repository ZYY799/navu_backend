"""
WebSocket连接管理器
"""
from typing import Dict
from fastapi import WebSocket
from app.models.schemas import WSMessage
import time
import json


class WebSocketManager:
    
    def __init__(self):
        self.connections: Dict[str, WebSocket] = {}
        self.sequence_numbers: Dict[str, int] = {}
    
    async def connect(self, websocket: WebSocket, nav_session_id: str):
        await websocket.accept()
        self.connections[nav_session_id] = websocket
        self.sequence_numbers[nav_session_id] = 0
        print(f"WebSocket连接建立: {nav_session_id}")
    
    def disconnect(self, nav_session_id: str):
        if nav_session_id in self.connections:
            del self.connections[nav_session_id]
            del self.sequence_numbers[nav_session_id]
            print(f"WebSocket连接断开: {nav_session_id}")
    
    async def send_message(
        self,
        nav_session_id: str,
        message_type: str,
        data: Dict
    ):
        if nav_session_id not in self.connections:
            return False

        seq = self.sequence_numbers[nav_session_id]
        self.sequence_numbers[nav_session_id] += 1

        message = WSMessage(
            type=message_type,
            seq=seq,
            timestamp=int(time.time() * 1000),
            data=data
        )
        
        try:
            await self.connections[nav_session_id].send_json(message.model_dump())
            return True
        except Exception as e:
            print(f"WebSocket发送失败: {e}")
            self.disconnect(nav_session_id)
            return False

websocket_manager = WebSocketManager()
