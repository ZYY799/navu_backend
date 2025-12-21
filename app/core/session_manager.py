"""
会话管理器
"""
from typing import Dict, Optional
from app.models.schemas import NavigationSession, ConversationSession, NavState
import time


class SessionManager:
    """会话管理器（内存版本，生产环境应使用Redis）"""
    
    def __init__(self):
        self.conversation_sessions: Dict[str, ConversationSession] = {}
        self.navigation_sessions: Dict[str, NavigationSession] = {}
    
    def create_conversation(
        self,
        session_id: str,
        user_id: str
    ) -> ConversationSession:
        """创建对话会话"""
        session = ConversationSession(
            sessionId=session_id,
            userId=user_id,
            history=[],
            context={},
            createdAt=int(time.time() * 1000),
            updatedAt=int(time.time() * 1000)
        )
        self.conversation_sessions[session_id] = session
        return session
    
    def get_conversation(self, session_id: str) -> Optional[ConversationSession]:
        """获取对话会话"""
        return self.conversation_sessions.get(session_id)
    
    def create_navigation(
        self,
        nav_session_id: str,
        user_id: str,
        origin: Optional[Dict] = None,
        destination: Optional[Dict] = None
    ) -> NavigationSession:
        """创建导航会话"""
        session = NavigationSession(
            navSessionId=nav_session_id,
            userId=user_id,
            state=NavState.ASKING,
            origin=origin,
            destination=destination,
            createdAt=int(time.time() * 1000),
            updatedAt=int(time.time() * 1000)
        )
        self.navigation_sessions[nav_session_id] = session
        return session
    
    def get_navigation(self, nav_session_id: str) -> Optional[NavigationSession]:
        """获取导航会话"""
        return self.navigation_sessions.get(nav_session_id)
    
    def update_navigation_state(
        self,
        nav_session_id: str,
        state: NavState
    ) -> bool:
        """更新导航状态"""
        session = self.navigation_sessions.get(nav_session_id)
        if session:
            session.state = state
            session.updatedAt = int(time.time() * 1000)
            return True
        return False
    
    def clear_all(self):
        """清空所有会话"""
        self.conversation_sessions.clear()
        self.navigation_sessions.clear()


# 全局实例
session_manager = SessionManager()
