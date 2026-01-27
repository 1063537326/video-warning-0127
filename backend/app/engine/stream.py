import asyncio
import logging
from typing import Dict, Set, AsyncGenerator

logger = logging.getLogger(__name__)

class StreamBroadcaster:
    """
    视频流广播器
    
    采用发布-订阅模式 (Pub/Sub)，接收 EngineManager 的处理后帧，
    分发给所有连接的前端客户端 (MJPEG)。
    """
    
    def __init__(self):
        # 存储每个摄像头的活动订阅者 (Queue)
        # camera_id -> Set[asyncio.Queue]
        self._subscribers: Dict[int, Set[asyncio.Queue]] = {}
        self._lock = asyncio.Lock()
        
    async def broadcast(self, camera_id: int, frame_bytes: bytes):
        """
        向指定摄像头的所有订阅者广播一帧
        """
        if camera_id not in self._subscribers:
            return
            
        # 获取该摄像头的所有订阅者
        queues = self._subscribers[camera_id]
        if not queues:
            return
            
        # 广播 (非阻塞放，如果满了就丢弃旧帧，保证实时性)
        for q in list(queues): # 使用 list 副本以防迭代时变更
            if q.full():
                try:
                    q.get_nowait() # 丢弃旧帧
                except asyncio.QueueEmpty:
                    pass
            
            try:
                q.put_nowait(frame_bytes)
            except asyncio.QueueFull:
                pass # 极端情况，忽略

    async def subscribe(self, camera_id: int) -> AsyncGenerator[bytes, None]:
        """
        订阅指定摄像头的视频流
        
        Yields:
            MJPEG 格式的帧 (bytes)
        """
        queue = asyncio.Queue(maxsize=2) # 缓冲2帧，避免延迟
        
        async with self._lock:
            if camera_id not in self._subscribers:
                self._subscribers[camera_id] = set()
            self._subscribers[camera_id].add(queue)
            
        logger.debug(f"客户端加入流订阅: Camera {camera_id}")
        
        try:
            while True:
                # 等待新帧
                frame = await queue.get()
                
                # 封装为 MJPEG 格式 (multipart/x-mixed-replace)
                # 这一步通常在 FastAPI response generator 中做，这里只返回 raw bytes
                # 或者直接 yield 封装好的 chunk
                yield frame
                
        except asyncio.CancelledError:
            # 客户端断开连接
            pass
        finally:
            # 清理订阅
            async with self._lock:
                if camera_id in self._subscribers and queue in self._subscribers[camera_id]:
                    self._subscribers[camera_id].remove(queue)
                    if not self._subscribers[camera_id]:
                        del self._subscribers[camera_id]
            logger.debug(f"客户端退出流订阅: Camera {camera_id}")

# 全局单例
stream_broadcaster = StreamBroadcaster()
