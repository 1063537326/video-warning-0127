"""
视频采集模块

提供 RTSP 视频流采集功能，支持：
- 单路/多路摄像头采集
- 断流自动重连
- 帧率控制与跳帧
- 帧队列管理
"""
from .camera_capture import (
    CameraCapture,
    CaptureConfig,
    CaptureStatus,
    FrameData,
    test_rtsp_connection,
)

__all__ = [
    "CameraCapture",
    "CaptureConfig", 
    "CaptureStatus",
    "FrameData",
    "test_rtsp_connection",
]
