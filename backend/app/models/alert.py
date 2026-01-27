"""
报警记录模型
"""
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Float, JSON, Enum as SQLEnum, Index, Boolean
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
import enum

from app.core.database import Base


class AlertType(str, enum.Enum):
    """报警类型枚举"""
    STRANGER = "stranger"      # 陌生人
    KNOWN = "known"            # 已知人员
    BLACKLIST = "blacklist"    # 黑名单


class AlertLevel(str, enum.Enum):
    """报警级别枚举"""
    INFO = "info"           # 弱提醒 (如: 徘徊)
    WARNING = "warning"     # 一般警告
    CRITICAL = "critical"   # 严重警告 (如: 陌生人闯入)


class AlertStatus(str, enum.Enum):
    """报警状态枚举"""
    PENDING = "pending"        # 待处理
    PROCESSED = "processed"    # 已处理
    IGNORED = "ignored"        # 已忽略


class AlertLog(Base):
    """报警记录表"""
    __tablename__ = "alert_logs"
    
    id = Column(Integer, primary_key=True, index=True)
    track_id = Column(String(64), index=True, nullable=True)  # 追踪ID，用于关联事件
    camera_id = Column(Integer, ForeignKey("cameras.id"), nullable=False)
    alert_type = Column(SQLEnum(AlertType), nullable=False)
    alert_level = Column(SQLEnum(AlertLevel), default=AlertLevel.INFO, nullable=False)
    person_id = Column(Integer, ForeignKey("known_persons.id"), nullable=True)  # 陌生人为 NULL
    confidence = Column(Float, nullable=True)  # 识别置信度 0.0-1.0
    
    # 图片证据
    face_image_path = Column(String(500), nullable=True)  # 最佳人脸
    best_body_image_path = Column(String(500), nullable=True) # 最佳全身(新增)
    full_image_path = Column(String(500), nullable=True)  # 全景(保留)
    image_history = Column(JSON, nullable=True) # 过程图片列表 [{ts, path, score}]
    
    face_bbox = Column(JSON, nullable=True)  # 人脸框坐标 {x, y, w, h}
    
    status = Column(SQLEnum(AlertStatus), default=AlertStatus.PENDING, nullable=False)
    is_reviewed = Column(Boolean, default=False, nullable=False) # 人工是否已修正/查看
    
    processed_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    processed_at = Column(DateTime(timezone=True), nullable=True)
    process_remark = Column(String(500), nullable=True)
    extra_data = Column(JSON, nullable=True)  # Extended fields
    
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False, index=True) # 记录创建时间
    start_time = Column(DateTime(timezone=True), default=func.now(), nullable=True) # 事件开始时间
    end_time = Column(DateTime(timezone=True), nullable=True) # 事件结束/更新时间
    
    # 复合索引
    __table_args__ = (
        Index('idx_alert_logs_query', 'created_at', 'camera_id', 'status'),
    )
