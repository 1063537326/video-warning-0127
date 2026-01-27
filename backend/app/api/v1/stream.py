from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import StreamingResponse
from app.engine.stream import stream_broadcaster

router = APIRouter()

@router.get("/{camera_id}", response_class=StreamingResponse)
async def video_stream(camera_id: int, request: Request):
    """
    获取指定摄像头的实时视频流 (MJPEG)
    
    使用 multipart/x-mixed-replace 格式，可以直接在 <img> 标签的 src 中使用
    """
    async def stream_generator():
        # 订阅流
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
