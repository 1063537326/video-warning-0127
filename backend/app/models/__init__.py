# SQLAlchemy Models Package
# 导出所有模型以便 Alembic 能够检测到

from app.models.user import User, UserRole
from app.models.camera import Camera, CameraZone, CameraStatus
from app.models.person import KnownPerson, PersonGroup, FaceImage
from app.models.alert import AlertLog, AlertType, AlertStatus
from app.models.system import SystemConfig, OperationLog, CleanupLog

__all__ = [
    # User
    "User",
    "UserRole",
    # Camera
    "Camera",
    "CameraZone", 
    "CameraStatus",
    # Person
    "KnownPerson",
    "PersonGroup",
    "FaceImage",
    # Alert
    "AlertLog",
    "AlertType",
    "AlertStatus",
    # System
    "SystemConfig",
    "OperationLog",
    "CleanupLog",
]
