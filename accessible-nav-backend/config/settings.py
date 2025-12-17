"""
系统配置管理
"""
import os
from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    """系统配置类"""
    
    # 基础配置
    DEBUG: bool = os.getenv("DEBUG", "True") == "True"
    PORT: int = int(os.getenv("PORT", "8000"))
    MOCK_MODE: bool = os.getenv("MOCK_MODE", "True") == "True"
    
    # API密钥
    AMAP_API_KEY: str = os.getenv("AMAP_API_KEY", "")
    LLM_API_KEY: str = os.getenv("LLM_API_KEY", "")
    LLM_API_BASE: str = os.getenv("LLM_API_BASE", "https://api.anthropic.com")
    
    # LLM配置
    LLM_MODEL: str = os.getenv("LLM_MODEL", "claude-sonnet-4-20250514")
    LLM_TEMPERATURE: float = float(os.getenv("LLM_TEMPERATURE", "0.7"))
    LLM_MAX_TOKENS: int = int(os.getenv("LLM_MAX_TOKENS", "1000"))
    
    # YOLO模型配置
    YOLO_MODEL_PATH: str = os.getenv("YOLO_MODEL_PATH", "yolov8n.pt")
    YOLO_CONFIDENCE: float = float(os.getenv("YOLO_CONFIDENCE", "0.5"))
    YOLO_DEVICE: str = os.getenv("YOLO_DEVICE", "cpu")
    
    # TTS配置
    TTS_PROVIDER: str = os.getenv("TTS_PROVIDER", "azure")  # azure/aliyun/edge
    TTS_API_KEY: str = os.getenv("TTS_API_KEY", "")
    TTS_REGION: str = os.getenv("TTS_REGION", "eastus")
    TTS_VOICE: str = os.getenv("TTS_VOICE", "zh-CN-XiaoxiaoNeural")
    
    # Redis配置（可选）
    REDIS_HOST: str = os.getenv("REDIS_HOST", "localhost")
    REDIS_PORT: int = int(os.getenv("REDIS_PORT", "6379"))
    REDIS_DB: int = int(os.getenv("REDIS_DB", "0"))
    
    # 导航参数
    NAV_UPDATE_INTERVAL: int = int(os.getenv("NAV_UPDATE_INTERVAL", "5"))  # 秒
    NAV_DEVIATION_THRESHOLD: int = int(os.getenv("NAV_DEVIATION_THRESHOLD", "20"))  # 米
    NAV_ARRIVAL_THRESHOLD: int = int(os.getenv("NAV_ARRIVAL_THRESHOLD", "10"))  # 米
    
    # WebSocket配置
    WS_HEARTBEAT_INTERVAL: int = int(os.getenv("WS_HEARTBEAT_INTERVAL", "30"))  # 秒
    WS_MESSAGE_QUEUE_SIZE: int = int(os.getenv("WS_MESSAGE_QUEUE_SIZE", "100"))
    
    # 文件路径
    AUDIO_OUTPUT_DIR: str = os.getenv("AUDIO_OUTPUT_DIR", "./audio_output")
    ROUTE_OUTPUT_DIR: str = os.getenv("ROUTE_OUTPUT_DIR", "./route_output")
    
    class Config:
        env_file = ".env"
        case_sensitive = True


@lru_cache()
def get_settings() -> Settings:
    """获取配置实例（单例）"""
    return Settings()


# 全局配置实例
settings = get_settings()


# 创建必要的目录
os.makedirs(settings.AUDIO_OUTPUT_DIR, exist_ok=True)
os.makedirs(settings.ROUTE_OUTPUT_DIR, exist_ok=True)
