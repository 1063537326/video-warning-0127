"""
视频分析引擎包

提供完整的视频流人脸识别分析功能：
- 视频流采集 (capture)
- 人脸识别 (recognition)
- 分析管道 (pipeline)
- 引擎管理 (manager)
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
