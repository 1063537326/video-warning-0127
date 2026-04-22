"""
视频流 API

提供 MJPEG 格式的实时视频流接口。
使用 multipart/x-mixed-replace 协议，可直接在浏览器 <img> 标签中渲染。
"""
from fastapi import APIRouter, HTTPException, Request, Query
from fastapi.responses import StreamingResponse
from app.engine.stream import stream_broadcaster
from app.core.security import verify_token

router = APIRouter()

@router.get("/{camera_id}", response_class=StreamingResponse)
async def video_stream(
    camera_id: int, 
    request: Request,
    token: str = Query(None, description="认证 Token（<img> 标签无法使用 Header，通过 URL 参数传递）")
):
    """
    获取指定摄像头的实时视频流（MJPEG）
    
    使用 multipart/x-mixed-replace 格式，可以直接在 <img> 标签的 src 中使用。
    认证方式：通过 URL 查询参数 `token` 传递 JWT Token。
    """
    # 鉴权：验证 token
    if not token:
        raise HTTPException(status_code=401, detail="缺少认证 Token")
    
    payload = verify_token(token)
    if payload is None or payload.get("type") != "access":
        raise HTTPException(status_code=401, detail="Token 无效或已过期")
    
    async def stream_generator():
        """生成 MJPEG 帧流"""
        subscriber = stream_broadcaster.subscribe(camera_id)
        
        try:
            async for frame in subscriber:
                # 检查客户端是否断开
                if await request.is_disconnected():
                    break
                    
                yield (b'--frame\r\n'
                       b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')
        except Exception:
            pass
            
    return StreamingResponse(
        stream_generator(), 
        media_type="multipart/x-mixed-replace; boundary=frame"
    )

