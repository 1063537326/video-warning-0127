"""
WebSocket 模块

提供实时消息推送功能：
- 报警消息推送
- 摄像头状态推送
- 系统通知推送
- 心跳检测
"""
from .manager import ConnectionManager, ClientInfo, MessageType, manager
from .handlers import (
    push_alert,
    push_camera_status,
    push_batch_camera_status,
    push_system_notification,
    push_engine_status,
    push_to_user,
    engine_alert_callback,
    engine_status_callback,
)

__all__ = [
    # 管理器
    "ConnectionManager",
    "ClientInfo",
    "MessageType",
    "manager",
    # 推送函数
    "push_alert",
    "push_camera_status",
    "push_batch_camera_status",
    "push_system_notification",
    "push_engine_status",
    "push_to_user",
    # 引擎回调
    "engine_alert_callback",
    "engine_status_callback",
]
