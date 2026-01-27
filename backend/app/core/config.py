"""
应用配置管理模块
使用 Pydantic Settings 管理配置
"""
import os
from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional

# 获取 backend 目录的绝对路径
_BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class Settings(BaseSettings):
    """应用配置"""
    
    # 应用基础配置
    APP_NAME: str = "视频监控报警系统"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = False
    
    # 数据库配置
    DATABASE_URL: str = "postgresql+asyncpg://postgres:password@localhost:5432/video_warning"
    
    # JWT 配置
    SECRET_KEY: str = "your-secret-key-change-in-production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    
    # 文件存储配置（使用绝对路径）
    DATA_DIR: str = os.path.join(_BACKEND_DIR, "data")
    CAPTURES_DIR: str = os.path.join(_BACKEND_DIR, "data", "captures")
    FACES_DIR: str = os.path.join(_BACKEND_DIR, "data", "faces")
    
    # 模型路径配置
    MODELS_DIR: str = os.path.join(_BACKEND_DIR, "data", "models")
    YOLO_BODY_MODEL: str = os.path.join(_BACKEND_DIR, "data", "models", "yolo11n.pt")
    YOLO_FACE_MODEL: str = os.path.join(_BACKEND_DIR, "data", "models", "face_yolov8n.pt")
    
    # CompreFace 配置
    COMPREFACE_URL: str = "http://172.16.18.22:8000"  # 外部识别服务
    COMPREFACE_API_KEY: str = "cebc9355-1aea-4e62-8a84-8e129d20054e"
    COMPREFACE_THRESHOLD: float = 0.88  # 陌生人判定阈值
    
    # 追踪与检测配置
    CONF_BODY: float = 0.55
    CONF_FACE: float = 0.50
    TRACKER_TYPE: str = "bytetrack.yaml"
    
    # 系统与报警配置
    ALERT_COOLDOWN_SECONDS: int = 60
    CONCURRENT_LIMIT_DEFAULT: int = 5
    
    # 数据清理配置
    DATA_RETENTION_DAYS: int = 30
    CAPTURE_QUALITY: int = 85
    
    # CORS 配置
    CORS_ORIGINS: list = ["*"]
    
    # ROI 区域配置 (x_min, y_min, x_max, y_max) 0.0-1.0
    # 左上角为(0,0), 右下角为(1,1)
    # 默认值参考：顶部裁掉 25% (避开远景走廊), 左右保留 15% 边距 (类似黄框宽度)
    DETECTION_ROI: list = [0.15, 0.25, 0.85, 0.95]
    
    model_config = SettingsConfigDict(
        env_file=".env",
        case_sensitive=True,
        extra="ignore"
    )


settings = Settings()
