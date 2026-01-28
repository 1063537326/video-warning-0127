"""
视频监控报警系统 - 后端入口

主要功能：
- FastAPI 应用初始化
- 视频分析引擎集成
- WebSocket 服务端
- API 路由注册
"""
import asyncio
import logging
from contextlib import asynccontextmanager

from app.core.scheduler import init_scheduler, shutdown_scheduler
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Depends, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.core.config import settings
from app.api.v1 import router as api_v1_router
from app.websocket import (
    manager as ws_manager,
    engine_alert_callback,
    engine_status_callback,
)

# 配置日志
logging.basicConfig(
    level=logging.DEBUG if settings.DEBUG else logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# 引擎实例（延迟导入，避免循环依赖）
_engine_manager = None


async def init_engine():
    """
    初始化视频分析引擎
    """
    global _engine_manager
    
    try:
        from app.engine.manager import get_engine
        
        # 获取单例引擎实例
        _engine_manager = get_engine()
        
        # 设置回调
        _engine_manager.set_alert_callback(engine_alert_callback)
        _engine_manager.set_status_callback(engine_status_callback)
        
        # 启动引擎
        success = await _engine_manager.start()
        
        if success:
            logger.info("视频分析引擎初始化成功")
        else:
            logger.warning("视频分析引擎启动失败")
            # _engine_manager = None # Keep instance even if failed start, to allow retries? Or set None.
            
    except Exception as e:
        logger.error(f"引擎初始化异常: {e}")
        _engine_manager = None
        
    # 加载已启用摄像头
    if _engine_manager and _engine_manager.status.value == "running":
         try:
            from app.core.database import AsyncSessionLocal
            from app.models.camera import Camera, CameraStatus
            from sqlalchemy import select
            
            async with AsyncSessionLocal() as db:
                result = await db.execute(select(Camera).where(Camera.is_enabled == True))
                cameras = result.scalars().all()
                for cam in cameras:
                    # 构建带认证的 RTSP URL
                    rtsp_url = cam.rtsp_url
                    if cam.username and cam.password:
                        if "://" in rtsp_url:
                            protocol, rest = rtsp_url.split("://", 1)
                            rtsp_url = f"{protocol}://{cam.username}:{cam.password}@{rest}"
                            
                    _engine_manager.add_camera(
                        camera_id=cam.id,
                        name=cam.name,
                        rtsp_url=rtsp_url,
                        username=cam.username,
                        password=cam.password,
                        target_fps=cam.fps,
                        # config=cam.config # TODO: Pass config if needed
                    )
                    logger.info(f"已加载摄像头到引擎: {cam.name}")
                    
         except Exception as e:
            logger.error(f"加载摄像头失败: {e}")


async def shutdown_engine():
    """关闭视频分析引擎"""
    global _engine_manager
    
    if _engine_manager is not None:
        await _engine_manager.stop()
        _engine_manager = None
        logger.info("视频分析引擎已关闭")


def get_engine():
    """获取引擎实例（供依赖注入使用）"""
    return _engine_manager


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    # 启动时执行
    logger.info(f"[START] {settings.APP_NAME} v{settings.APP_VERSION} starting...")
    
    # 启动 WebSocket 管理器
    await ws_manager.start()
    logger.info("WebSocket 管理器已启动")
    
    # 初始化视频分析引擎（可选，失败不影响其他功能）
    await init_engine()
    
    # 启动定时任务调度器
    await init_scheduler()
    
    yield
    
    # 关闭时执行
    logger.info("[STOP] Application shutting down...")
    
    # 关闭调度器
    await shutdown_scheduler()
    
    # 关闭引擎
    await shutdown_engine()
    
    # 关闭 WebSocket 管理器
    await ws_manager.stop()
    logger.info("WebSocket 管理器已关闭")


app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="视频流陌生人检测报警系统 API",
    lifespan=lifespan,
)

# CORS 中间件
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["*"],
    expose_headers=["*"],
)

# 静态文件服务（人脸图片、截图等）
app.mount("/static", StaticFiles(directory=settings.DATA_DIR), name="static")

# API 路由
app.include_router(api_v1_router, prefix="/api/v1")


@app.get("/health", tags=["健康检查"])
async def health_check():
    """健康检查接口"""
    engine_status = "unavailable"
    if _engine_manager is not None:
        engine_status = _engine_manager.status.value
    
    return {
        "status": "healthy",
        "app": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "engine_status": engine_status,
        "websocket_clients": ws_manager.client_count,
    }


@app.websocket("/ws")
async def websocket_endpoint(
    websocket: WebSocket,
    token: str = Query(default=None, description="JWT Token")
):
    """
    WebSocket 连接端点
    
    客户端通过此端点建立 WebSocket 连接，接收实时消息：
    - 报警通知
    - 摄像头状态变更
    - 系统通知
    
    连接时可选传入 token 参数进行身份验证
    
    消息格式：
    ```json
    {
        "type": "alert|camera_status|notification|...",
        "data": {...},
        "timestamp": "2024-01-01T00:00:00"
    }
    ```
    
    客户端可发送的消息：
    - ping: 心跳
    - subscribe: 订阅摄像头 {"type": "subscribe", "data": {"camera_ids": [1, 2]}}
    - unsubscribe: 取消订阅 {"type": "unsubscribe", "data": {"camera_ids": [1]}}
    """
    # 简单的 token 验证（可选）
    user_id = None
    username = None
    
    if token:
        try:
            from app.core.security import verify_token
            payload = verify_token(token)
            if payload:
                user_id = payload.get("sub")
                username = payload.get("username")
        except Exception as e:
            logger.warning(f"WebSocket token 验证失败: {e}")
    
    # 接受连接
    client_id = await ws_manager.connect(websocket, user_id, username)
    
    try:
        while True:
            # 接收消息
            data = await websocket.receive_json()
            
            # 处理消息
            await ws_manager.handle_message(client_id, data)
            
    except WebSocketDisconnect:
        await ws_manager.disconnect(client_id, reason="客户端断开")
    except Exception as e:
        logger.error(f"WebSocket 异常: {e}")
        await ws_manager.disconnect(client_id, reason=str(e))


@app.get("/api/v1/engine/status", tags=["引擎"])
async def get_engine_status():
    """
    获取视频分析引擎状态
    
    返回引擎运行状态、摄像头数量、人脸库信息等
    """
    if _engine_manager is None:
        return {
            "status": "unavailable",
            "message": "视频分析引擎未初始化（InsightFace 可能未安装）"
        }
    
    return _engine_manager.get_engine_stats()


@app.get("/api/v1/engine/cameras", tags=["引擎"])
async def get_engine_cameras():
    """
    获取引擎管理的所有摄像头状态
    
    返回每个摄像头的运行状态、帧率、队列大小等信息
    """
    if _engine_manager is None:
        return []
    
    return _engine_manager.get_all_camera_status()


if __name__ == "__main__":
    import uvicorn
    import sys
    
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
        
    uvicorn.run("main:app", host="0.0.0.0", port=8001, reload=settings.DEBUG)
