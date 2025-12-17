"""
无障碍老年人导航后端系统 - 主程序入口
"""
import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from config.settings import settings
from app.api import voice_routes, nav_routes
from app.core.session_manager import session_manager


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    # 启动时初始化
    print("🚀 系统启动中...")
    print(f"📍 运行模式: {'模拟模式' if settings.MOCK_MODE else '生产模式'}")
    print(f"🔧 调试模式: {settings.DEBUG}")
    yield
    # 关闭时清理
    print("👋 系统关闭中...")
    session_manager.clear_all()


# 创建FastAPI应用
app = FastAPI(
    title="无障碍导航后端API",
    description="为老年人设计的AI导航系统后端服务",
    version="1.0.0",
    lifespan=lifespan
)

# 配置CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 生产环境应限制具体域名
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 注册路由
app.include_router(voice_routes.router, prefix="/v1/voice", tags=["语音交互"])
app.include_router(nav_routes.router, prefix="/v1/nav", tags=["导航服务"])


@app.get("/")
async def root():
    """根路径 - 健康检查"""
    return {
        "service": "无障碍老年人导航后端",
        "version": "1.0.0",
        "status": "running",
        "mode": "mock" if settings.MOCK_MODE else "production",
        "docs": "/docs"
    }


@app.get("/health")
async def health_check():
    """健康检查接口"""
    return {
        "status": "healthy",
        "mode": "mock" if settings.MOCK_MODE else "production"
    }


if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=settings.PORT,
        reload=settings.DEBUG,
        log_level="info"
    )
