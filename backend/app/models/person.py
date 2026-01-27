"""
人员相关模型
"""
from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, Float
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship

from app.core.database import Base


class PersonGroup(Base):
    """人员分组表"""
    __tablename__ = "person_groups"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    description = Column(String(500), nullable=True)
    color = Column(String(20), nullable=True)  # 前端标签颜色
    alert_enabled = Column(Boolean, default=True, nullable=False)
    alert_priority = Column(Integer, default=0)
    sort_order = Column(Integer, default=0)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    
    # 关联
    persons = relationship("KnownPerson", back_populates="group")


class KnownPerson(Base):
    """已知人员表"""
    __tablename__ = "known_persons"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    employee_id = Column(String(50), nullable=True, index=True)
    group_id = Column(Integer, ForeignKey("person_groups.id"), nullable=True)
    department = Column(String(100), nullable=True)
    phone = Column(String(20), nullable=True)
    remark = Column(String(500), nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    
    # 关联
    group = relationship("PersonGroup", back_populates="persons")
    face_images = relationship("FaceImage", back_populates="person", cascade="all, delete-orphan")


class FaceImage(Base):
    """人脸图片表"""
    __tablename__ = "face_images"
    
    id = Column(Integer, primary_key=True, index=True)
    person_id = Column(Integer, ForeignKey("known_persons.id", ondelete="CASCADE"), nullable=False)
    image_path = Column(String(500), nullable=False)
    image_id = Column(String(100), nullable=True, index=True)  # CompreFace image_id
    # feature_vector: 预留 pgvector 扩展，暂用 JSON 或 BYTEA 存储
    quality_score = Column(Float, nullable=True)
    is_primary = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    
    # 关联
    person = relationship("KnownPerson", back_populates="face_images")
