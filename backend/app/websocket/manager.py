"""
WebSocket 连接管理器

功能：
- 管理客户端连接
- 消息广播
- 心跳检测
- 用户认证
- 房间管理
"""
import asyncio
import logging
import time
from typing import Dict, List, Optional, Set
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum

from fastapi import WebSocket, WebSocketDisconnect

logger = logging.getLogger(__name__)


class MessageType(str, Enum):
    """消息类型枚举"""
    # 系统消息
    CONNECT = "connect"             # 连接成功
    DISCONNECT = "disconnect"       # 断开连接
    HEARTBEAT = "heartbeat"         # 心跳
    PONG = "pong"                   # 心跳响应
    ERROR = "error"                 # 错误
    
    # 业务消息
    ALERT = "alert"                 # 报警
    CAMERA_STATUS = "camera_status"  # 摄像头状态
    NOTIFICATION = "notification"   # 系统通知
    ENGINE_STATUS = "engine_status"  # 引擎状态


@dataclass
class ClientInfo:
    """客户端信息"""
    websocket: WebSocket
    client_id: str
    user_id: Optional[int] = None
    username: Optional[str] = None
    connected_at: datetime = field(default_factory=datetime.now)
    last_heartbeat: float = field(default_factory=time.time)
    subscribed_cameras: Set[int] = field(default_factory=set)  # 订阅的摄像头
    
    def to_dict(self) -> dict:
        """转换为字典"""
        return {
            "client_id": self.client_id,
            "user_id": self.user_id,
            "username": self.username,
            "connected_at": self.connected_at.isoformat(),
            "subscribed_cameras": list(self.subscribed_cameras),
        }


class ConnectionManager:
    """
    WebSocket 连接管理器
    
    功能：
    - 管理所有 WebSocket 连接
    - 支持广播和定向发送
    - 心跳检测与自动断开
    - 摄像头订阅管理
    
    使用示例：
        manager = ConnectionManager()
        
        # 在 WebSocket 端点中
        async def websocket_endpoint(websocket: WebSocket):
            client_id = await manager.connect(websocket)
            try:
                while True:
                    data = await websocket.receive_json()
                    await manager.handle_message(client_id, data)
            except WebSocketDisconnect:
                manager.disconnect(client_id)
    """
    
    def __init__(
        self,
        heartbeat_interval: float = 30.0,
        heartbeat_timeout: float = 60.0
    ):
        """
        初始化连接管理器
        
        Args:
            heartbeat_interval: 心跳间隔（秒）
            heartbeat_timeout: 心跳超时（秒）
        """
        self.heartbeat_interval = heartbeat_interval
        self.heartbeat_timeout = heartbeat_timeout
        
        # 连接存储
        self._clients: Dict[str, ClientInfo] = {}
        self._user_clients: Dict[int, Set[str]] = {}  # user_id -> client_ids
        
        # 心跳任务
        self._heartbeat_task: Optional[asyncio.Task] = None
        self._is_running = False
    
    @property
    def client_count(self) -> int:
        """当前连接数"""
        return len(self._clients)
    
    @property
    def clients(self) -> List[ClientInfo]:
        """所有客户端"""
        return list(self._clients.values())
    
    async def start(self) -> None:
        """启动心跳检测"""
        if self._is_running:
            return
        
        self._is_running = True
        self._heartbeat_task = asyncio.create_task(self._heartbeat_loop())
        logger.info("WebSocket 连接管理器已启动")
    
    async def stop(self) -> None:
        """停止心跳检测"""
        self._is_running = False
        
        if self._heartbeat_task:
            self._heartbeat_task.cancel()
            try:
                await self._heartbeat_task
            except asyncio.CancelledError:
                pass
            self._heartbeat_task = None
        
        # 断开所有连接
        for client_id in list(self._clients.keys()):
            await self.disconnect(client_id, reason="服务器关闭")
        
        logger.info("WebSocket 连接管理器已停止")
    
    async def _heartbeat_loop(self) -> None:
        """心跳检测循环"""
        while self._is_running:
            try:
                await asyncio.sleep(self.heartbeat_interval)
                await self._check_heartbeats()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"心跳检测异常: {e}")
    
    async def _check_heartbeats(self) -> None:
        """检查心跳超时"""
        current_time = time.time()
        timeout_clients = []
        
        for client_id, client in self._clients.items():
            if current_time - client.last_heartbeat > self.heartbeat_timeout:
                timeout_clients.append(client_id)
        
        for client_id in timeout_clients:
            logger.warning(f"客户端 {client_id} 心跳超时，断开连接")
            await self.disconnect(client_id, reason="心跳超时")
    
    def _generate_client_id(self) -> str:
        """生成客户端 ID"""
        import uuid
        return uuid.uuid4().hex[:16]
    
    async def connect(
        self,
        websocket: WebSocket,
        user_id: Optional[int] = None,
        username: Optional[str] = None
    ) -> str:
        """
        接受新连接
        
        Args:
            websocket: WebSocket 对象
            user_id: 用户 ID
            username: 用户名
            
        Returns:
            客户端 ID
        """
        await websocket.accept()
        
        client_id = self._generate_client_id()
        client = ClientInfo(
            websocket=websocket,
            client_id=client_id,
            user_id=user_id,
            username=username
        )
        
        self._clients[client_id] = client
        
        # 记录用户连接
        if user_id:
            if user_id not in self._user_clients:
                self._user_clients[user_id] = set()
            self._user_clients[user_id].add(client_id)
        
        logger.info(f"客户端连接: {client_id} (user={username})")
        
        # 发送连接成功消息
        await self.send_to_client(client_id, {
            "type": MessageType.CONNECT.value,
            "data": {
                "client_id": client_id,
                "message": "连接成功",
            }
        })
        
        return client_id
    
    async def disconnect(self, client_id: str, reason: str = "正常断开") -> None:
        """
        断开连接
        
        Args:
            client_id: 客户端 ID
            reason: 断开原因
        """
        client = self._clients.pop(client_id, None)
        if client is None:
            return
        
        # 移除用户连接记录
        if client.user_id and client.user_id in self._user_clients:
            self._user_clients[client.user_id].discard(client_id)
            if not self._user_clients[client.user_id]:
                del self._user_clients[client.user_id]
        
        # 关闭 WebSocket
        try:
            await client.websocket.close()
        except Exception:
            pass
        
        logger.info(f"客户端断开: {client_id} (reason={reason})")
    
    def update_heartbeat(self, client_id: str) -> bool:
        """
        更新心跳时间
        
        Args:
            client_id: 客户端 ID
            
        Returns:
            是否更新成功
        """
        client = self._clients.get(client_id)
        if client:
            client.last_heartbeat = time.time()
            return True
        return False
    
    def subscribe_camera(self, client_id: str, camera_id: int) -> bool:
        """
        订阅摄像头
        
        Args:
            client_id: 客户端 ID
            camera_id: 摄像头 ID
            
        Returns:
            是否订阅成功
        """
        client = self._clients.get(client_id)
        if client:
            client.subscribed_cameras.add(camera_id)
            return True
        return False
    
    def unsubscribe_camera(self, client_id: str, camera_id: int) -> bool:
        """
        取消订阅摄像头
        
        Args:
            client_id: 客户端 ID
            camera_id: 摄像头 ID
            
        Returns:
            是否取消成功
        """
        client = self._clients.get(client_id)
        if client:
            client.subscribed_cameras.discard(camera_id)
            return True
        return False
    
    async def send_to_client(self, client_id: str, message: dict) -> bool:
        """
        发送消息给指定客户端
        
        Args:
            client_id: 客户端 ID
            message: 消息字典
            
        Returns:
            是否发送成功
        """
        client = self._clients.get(client_id)
        if client is None:
            return False
        
        try:
            await client.websocket.send_json(message)
            return True
        except Exception as e:
            logger.warning(f"发送消息失败 (client={client_id}): {e}")
            await self.disconnect(client_id, reason="发送失败")
            return False
    
    async def send_to_user(self, user_id: int, message: dict) -> int:
        """
        发送消息给指定用户的所有连接
        
        Args:
            user_id: 用户 ID
            message: 消息字典
            
        Returns:
            成功发送的连接数
        """
        client_ids = self._user_clients.get(user_id, set())
        success_count = 0
        
        for client_id in list(client_ids):
            if await self.send_to_client(client_id, message):
                success_count += 1
        
        return success_count
    
    async def broadcast(self, message: dict, exclude: Optional[Set[str]] = None) -> int:
        """
        广播消息给所有客户端
        
        Args:
            message: 消息字典
            exclude: 排除的客户端 ID 集合
            
        Returns:
            成功发送的连接数
        """
        exclude = exclude or set()
        success_count = 0
        
        for client_id in list(self._clients.keys()):
            if client_id in exclude:
                continue
            if await self.send_to_client(client_id, message):
                success_count += 1
        
        return success_count
    
    async def broadcast_to_camera_subscribers(
        self,
        camera_id: int,
        message: dict
    ) -> int:
        """
        广播消息给订阅了指定摄像头的客户端
        
        Args:
            camera_id: 摄像头 ID
            message: 消息字典
            
        Returns:
            成功发送的连接数
        """
        success_count = 0
        
        for client_id, client in list(self._clients.items()):
            if camera_id in client.subscribed_cameras:
                if await self.send_to_client(client_id, message):
                    success_count += 1
        
        return success_count
    
    async def handle_message(self, client_id: str, data: dict) -> None:
        """
        处理客户端消息
        
        Args:
            client_id: 客户端 ID
            data: 消息数据
        """
        msg_type = data.get("type", "")
        
        if msg_type == "ping" or msg_type == MessageType.HEARTBEAT.value:
            # 心跳
            self.update_heartbeat(client_id)
            await self.send_to_client(client_id, {
                "type": MessageType.PONG.value,
                "data": {"timestamp": time.time()}
            })
        
        elif msg_type == "subscribe":
            # 订阅摄像头
            camera_ids = data.get("data", {}).get("camera_ids", [])
            for camera_id in camera_ids:
                self.subscribe_camera(client_id, camera_id)
            logger.debug(f"客户端 {client_id} 订阅摄像头: {camera_ids}")
        
        elif msg_type == "unsubscribe":
            # 取消订阅
            camera_ids = data.get("data", {}).get("camera_ids", [])
            for camera_id in camera_ids:
                self.unsubscribe_camera(client_id, camera_id)
            logger.debug(f"客户端 {client_id} 取消订阅摄像头: {camera_ids}")
        
        else:
            logger.warning(f"未知消息类型: {msg_type}")
    
    def get_stats(self) -> dict:
        """
        获取统计信息
        
        Returns:
            统计信息字典
        """
        return {
            "client_count": len(self._clients),
            "user_count": len(self._user_clients),
            "heartbeat_interval": self.heartbeat_interval,
            "heartbeat_timeout": self.heartbeat_timeout,
        }


# 全局连接管理器实例
manager = ConnectionManager()
