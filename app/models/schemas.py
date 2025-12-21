"""
数据模型定义
"""
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field
from enum import Enum


# ==================== 枚举类型 ====================

class NavState(str, Enum):
    """导航状态"""
    ASKING = "asking"  # 询问阶段
    NAVIGATING = "navigating"  # 导航中
    ARRIVED = "arrived"  # 已到达
    CANCELLED = "cancelled"  # 已取消


class ObstacleType(str, Enum):
    """障碍物类型"""
    STAIRS = "stairs"  # 台阶
    CURB = "curb"  # 路沿
    OBSTACLE = "obstacle"  # 障碍物
    BLIND_PATH_BROKEN = "blind_path_broken"  # 盲道中断
    SLOPE = "slope"  # 坡道
    TURN = "turn"  # 转弯


class SafetyLevel(int, Enum):
    """安全等级 (1-5, 5最安全)"""
    DANGEROUS = 1
    UNSAFE = 2
    MODERATE = 3
    SAFE = 4
    VERY_SAFE = 5


# ==================== 请求模型 ====================

class VoiceTextRequest(BaseModel):
    """语音文本请求"""
    userId: str = Field(..., description="用户ID")
    sessionId: str = Field(..., description="会话ID")
    text: str = Field(..., description="识别的文本内容")
    location: Optional[Dict[str, float]] = Field(None, description="当前位置 {lat, lng}")
    timestamp: int = Field(..., description="时间戳（毫秒）")


class PerceptionBatchRequest(BaseModel):
    """感知批次请求"""
    userId: str = Field(..., description="用户ID")
    navSessionId: str = Field(..., description="导航会话ID")
    images: List[str] = Field(..., description="Base64编码的图片列表（最多3张）", max_length=3)
    location: Dict[str, float] = Field(..., description="当前位置 {lat, lng}")
    timestamp: int = Field(..., description="时间戳（毫秒）")


class NavStartRequest(BaseModel):
    """开始导航请求"""
    userId: str = Field(..., description="用户ID")
    sessionId: str = Field(..., description="对话会话ID")
    origin: Optional[Dict[str, float]] = Field(None, description="起点坐标 {lat, lng}")
    destination: Dict[str, float] = Field(..., description="终点坐标 {lat, lng}")


# ==================== 响应模型 ====================

class VoiceTextResponse(BaseModel):
    """语音文本响应"""
    success: bool
    message: str = Field(..., description="系统回复文本")
    audioUrl: Optional[str] = Field(None, description="TTS音频URL")
    navState: Optional[str] = Field(None, description="导航状态")
    data: Optional[Dict[str, Any]] = Field(None, description="额外数据")


class ObstacleInfo(BaseModel):
    """障碍物信息"""
    type: str = Field(..., description="障碍物类型")
    distance: float = Field(..., description="距离（米）")
    direction: str = Field(..., description="方向（前方/左前方/右前方）")
    confidence: float = Field(..., description="置信度")


class PerceptionBatchResponse(BaseModel):
    """感知批次响应"""
    success: bool
    obstacles: List[ObstacleInfo] = Field(default_factory=list, description="检测到的障碍物")
    roadCondition: str = Field(..., description="道路状况描述")
    safetyLevel: int = Field(..., description="安全等级 (1-5)")
    aiGuidance: Optional[str] = Field(None, description="AI指路建议")
    audioUrl: Optional[str] = Field(None, description="语音提醒URL")


class RouteStep(BaseModel):
    """路线步骤"""
    instruction: str = Field(..., description="指令文本")
    distance: int = Field(..., description="距离（米）")
    duration: int = Field(..., description="时间（秒）")


class RouteOption(BaseModel):
    """路线选项"""
    routeId: str = Field(..., description="路线ID")
    name: str = Field(..., description="路线名称（推荐/最短/无障碍）")
    distance: int = Field(..., description="总距离（米）")
    duration: int = Field(..., description="预计时间（秒）")
    steps: List[RouteStep] = Field(default_factory=list, description="路线步骤")
    accessibilityScore: int = Field(..., description="无障碍评分 (1-100)")


class NavStartResponse(BaseModel):
    """开始导航响应"""
    success: bool
    navSessionId: str = Field(..., description="导航会话ID")
    routes: List[RouteOption] = Field(default_factory=list, description="路线选项")
    message: str = Field(..., description="系统消息")
    wsUrl: str = Field(..., description="WebSocket连接URL")
    audioUrl: Optional[str] = Field(None, description="语音提示URL")


# ==================== WebSocket消息模型 ====================

class WSMessage(BaseModel):
    """WebSocket消息基类"""
    type: str = Field(..., description="消息类型")
    seq: int = Field(..., description="序列号")
    timestamp: int = Field(..., description="时间戳")
    data: Dict[str, Any] = Field(default_factory=dict, description="消息数据")


class NavInstruction(BaseModel):
    """导航指令"""
    text: str = Field(..., description="指令文本")
    audioUrl: Optional[str] = Field(None, description="语音URL")
    remainingDistance: int = Field(..., description="剩余距离（米）")
    remainingTime: int = Field(..., description="剩余时间（秒）")


class ObstacleWarning(BaseModel):
    """障碍物预警"""
    type: str = Field(..., description="障碍物类型")
    distance: float = Field(..., description="距离（米）")
    direction: str = Field(..., description="方向")
    urgency: str = Field(..., description="紧急程度 (low/medium/high)")
    suggestion: str = Field(..., description="建议")


# ==================== 内部数据模型 ====================

class NavigationSession(BaseModel):
    """导航会话"""
    navSessionId: str
    userId: str
    state: NavState = NavState.ASKING
    routeId: Optional[str] = None
    origin: Optional[Dict[str, float]] = None
    destination: Optional[Dict[str, float]] = None
    currentLocation: Optional[Dict[str, float]] = None
    routeData: Optional[Dict[str, Any]] = None
    createdAt: int
    updatedAt: int


class ConversationSession(BaseModel):
    """对话会话"""
    sessionId: str
    userId: str
    history: List[Dict[str, str]] = Field(default_factory=list)
    context: Dict[str, Any] = Field(default_factory=dict)
    createdAt: int
    updatedAt: int
