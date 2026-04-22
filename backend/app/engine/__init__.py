"""
视频分析引擎包

提供完整的视频流目标检测与人脸识别分析功能：
- 视频流采集（capture）
- 目标追踪（analyzers/tracker — YOLO + ByteTrack）
- 人脸识别（recognition — CompreFace REST API）
- 视频帧广播（stream — MJPEG Pub/Sub）
- 引擎管理（manager）
"""
from .manager import (
    EngineManager,
    EngineStatus,
    CameraTask,
    get_engine,
)

__all__ = [
    "EngineManager",
    "EngineStatus",
    "CameraTask",
    "get_engine",
]
