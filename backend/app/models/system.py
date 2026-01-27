"""
系统配置与日志模型
"""
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, JSON, BigInteger
from sqlalchemy.sql import func

from app.core.database import Base


class SystemConfig(Base):
    """系统配置表"""
    __tablename__ = "system_configs"
    
    id = Column(Integer, primary_key=True, index=True)
    config_key = Column(String(100), unique=True, nullable=False, index=True)
    config_value = Column(String(1000), nullable=True)
    value_type = Column(String(20), nullable=False)  # string/number/boolean/json
    description = Column(String(500), nullable=True)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    updated_by = Column(Integer, ForeignKey("users.id"), nullable=True)


class OperationLog(Base):
    """操作日志表"""
    __tablename__ = "operation_logs"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    action = Column(String(50), nullable=False)  # create/update/delete/login/logout
    target_type = Column(String(50), nullable=True)  # camera/person/alert/config
    target_id = Column(Integer, nullable=True)
    details = Column(JSON, nullable=True)  # 变更详情 before/after
    ip_address = Column(String(50), nullable=True)
    user_agent = Column(String(500), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False, index=True)


class CleanupLog(Base):
    """数据清理日志表"""
    __tablename__ = "cleanup_logs"
    
    id = Column(Integer, primary_key=True, index=True)
    cleanup_type = Column(String(50), nullable=False)  # alert/capture
    records_deleted = Column(Integer, default=0)
    files_deleted = Column(Integer, default=0)
    bytes_freed = Column(BigInteger, default=0)
    started_at = Column(DateTime(timezone=True), nullable=False)
    finished_at = Column(DateTime(timezone=True), nullable=True)
    status = Column(String(20), nullable=False)  # success/failed
    error_message = Column(String(1000), nullable=True)
