"""
摄像头相关模型
"""
from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, JSON, Enum as SQLEnum
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
import enum

from app.core.database import Base


class CameraStatus(str, enum.Enum):
    """摄像头状态枚举"""
    ONLINE = "online"
    OFFLINE = "offline"
    ERROR = "error"


class CameraZone(Base):
    """摄像头区域表"""
    __tablename__ = "camera_zones"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    description = Column(String(500), nullable=True)
    building = Column(String(100), nullable=True)
    floor = Column(String(50), nullable=True)
    sort_order = Column(Integer, default=0)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    
    # 关联
    cameras = relationship("Camera", back_populates="zone")


class Camera(Base):
    """摄像头配置表"""
    __tablename__ = "cameras"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    zone_id = Column(Integer, ForeignKey("camera_zones.id"), nullable=True)
    rtsp_url = Column(String(500), nullable=False)
    username = Column(String(100), nullable=True)
    password = Column(String(255), nullable=True)  # 加密存储
    resolution = Column(String(20), nullable=True)  # e.g., "1920x1080"
    fps = Column(Integer, default=25)
    status = Column(SQLEnum(CameraStatus), default=CameraStatus.OFFLINE, nullable=False)
    is_enabled = Column(Boolean, default=True, nullable=False)
    last_heartbeat_at = Column(DateTime(timezone=True), nullable=True)
    config = Column(JSON, nullable=True)  # 扩展配置：ROI、灵敏度等
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    
    # 关联
    zone = relationship("CameraZone", back_populates="cameras")
