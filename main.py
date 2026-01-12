"""
无障碍老年人导航后端系统 - 主程序入口
"""
import time
import uvicorn
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from contextlib import asynccontextmanager

from config.settings import settings
from app.api import voice_routes, nav_routes
from app.core.session_manager import session_manager
from fastapi import Request
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    # 启动时初始化
    print("系统启动中...")
    print(f"运行模式: {'模拟模式' if settings.MOCK_MODE else '生产模式'}")
    print(f"调试模式: {settings.DEBUG}")
    yield

    print("系统关闭中...")
    session_manager.clear_all()


app = FastAPI(
    title="无障碍导航后端API",
    description="为老年人设计的AI导航系统后端服务",
    version="1.0.0",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(voice_routes.router, prefix="/v1/voice", tags=["语音交互"])
app.include_router(nav_routes.router, prefix="/v1/nav", tags=["导航服务"])

app.mount("/audio", StaticFiles(directory=settings.AUDIO_OUTPUT_DIR), name="audio")


@app.get("/")
async def root():
    return {
        "service": "无障碍老年人导航后端",
        "version": "1.0.0",
        "status": "running",
        "mode": "mock" if settings.MOCK_MODE else "production",
        "docs": "/docs"
    }

@app.middleware("http")
async def log_in_out(request: Request, call_next):
    t0 = time.time()
    print(f"[HTTP_IN] {request.method} {request.url.path}")
    try:
        resp = await call_next(request)
        return resp
    finally:
        dt = (time.time() - t0) * 1000
        print(f"[HTTP_OUT] {request.method} {request.url.path} dtMs={dt:.1f}")

@app.get("/health")
async def health_check():

    return {
        "status": "healthy",
        "mode": "mock" if settings.MOCK_MODE else "production"
    }



@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    try:
        body = await request.body()
        body_text = body.decode("utf-8", errors="replace")
    except Exception:
        body_text = "<cannot_read_body>"

    print("\n[422][VALIDATION_ERROR]")
    print("path =", request.url.path)
    print("errors =", exc.errors())
    print("body =", body_text)
    print("[/422]\n")

    return JSONResponse(
        status_code=422,
        content={"detail": exc.errors()},
    )

if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=settings.PORT,
        reload=settings.DEBUG,
        log_level="info"
    )