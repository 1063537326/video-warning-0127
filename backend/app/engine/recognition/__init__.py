"""
人脸识别模块

提供人脸检测、特征提取、人脸比对功能，支持：
- InsightFace 人脸检测
- 512 维特征向量提取
- 余弦相似度比对
- 人脸库管理
- 报警冷却控制
"""
from .face_detector import (
    FaceDetector,
    FaceInfo,
    DetectorConfig,
)
from .face_database import (
    FaceDatabase,
    PersonFeature,
    MatchResult,
)
from .face_recognizer import (
    FaceRecognizer,
    RecognitionResult,
    RecognizerConfig,
    AlertCooldownManager,
)

__all__ = [
    # 检测器
    "FaceDetector",
    "FaceInfo",
    "DetectorConfig",
    # 数据库
    "FaceDatabase",
    "PersonFeature",
    "MatchResult",
    # 识别器
    "FaceRecognizer",
    "RecognitionResult",
    "RecognizerConfig",
    "AlertCooldownManager",
]
