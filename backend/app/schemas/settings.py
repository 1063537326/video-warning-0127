"""
系统配置 Schemas
- 系统参数、系统状态、数据清理相关的数据模型
"""
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum


class ConfigValueType(str, Enum):
    """配置值类型枚举"""
    STRING = "string"
    NUMBER = "number"
    BOOLEAN = "boolean"
    JSON = "json"


class ConfigItemResponse(BaseModel):
    """单个配置项响应"""
    id: int
    config_key: str
    config_value: Optional[str] = None
    value_type: str
    description: Optional[str] = None
    updated_at: datetime
    updated_by: Optional[int] = None

    class Config:
        from_attributes = True


class ConfigGroupResponse(BaseModel):
    """配置项分组响应"""
    group_name: str
    group_label: str
    items: List[ConfigItemResponse]


class SystemConfigResponse(BaseModel):
    """系统配置响应（按分组）"""
    groups: List[ConfigGroupResponse]
    

class ConfigUpdateItem(BaseModel):
    """配置更新项"""
    config_key: str = Field(..., description="配置键名")
    config_value: str = Field(..., description="配置值")


class ConfigUpdateRequest(BaseModel):
    """配置更新请求"""
    items: List[ConfigUpdateItem] = Field(..., min_length=1, max_length=50, description="要更新的配置项列表")


class ConfigUpdateResult(BaseModel):
    """配置更新结果"""
    success_count: int
    failed_count: int
    failed_keys: List[str] = []


class CleanupTypeEnum(str, Enum):
    """清理类型枚举"""
    ALERT = "alert"      # 清理报警记录
    CAPTURE = "capture"  # 清理截图文件
    ALL = "all"          # 清理所有


class CleanupRequest(BaseModel):
    """数据清理请求"""
    cleanup_type: CleanupTypeEnum = Field(CleanupTypeEnum.ALL, description="清理类型")
    days_to_keep: int = Field(30, ge=1, le=365, description="保留最近几天的数据")
    dry_run: bool = Field(False, description="模拟运行（不实际删除）")


class CleanupResult(BaseModel):
    """数据清理结果"""
    cleanup_type: str
    dry_run: bool
    records_deleted: int = 0
    files_deleted: int = 0
    bytes_freed: int = 0
    bytes_freed_formatted: str = "0 B"
    started_at: datetime
    finished_at: datetime
    duration_seconds: float
    status: str  # success/failed
    error_message: Optional[str] = None


class CleanupLogResponse(BaseModel):
    """清理日志响应"""
    id: int
    cleanup_type: str
    records_deleted: int
    files_deleted: int
    bytes_freed: int
    bytes_freed_formatted: str
    started_at: datetime
    finished_at: Optional[datetime] = None
    status: str
    error_message: Optional[str] = None

    class Config:
        from_attributes = True


class CleanupLogListResponse(BaseModel):
    """清理日志列表响应"""
    items: List[CleanupLogResponse]
    total: int
    page: int
    page_size: int
    total_pages: int


class DiskUsage(BaseModel):
    """磁盘使用情况"""
    path: str
    total_bytes: int
    used_bytes: int
    free_bytes: int
    usage_percent: float
    total_formatted: str
    used_formatted: str
    free_formatted: str


class ServiceStatus(BaseModel):
    """服务状态"""
    name: str
    status: str  # running/stopped/error
    uptime_seconds: Optional[float] = None
    uptime_formatted: Optional[str] = None
    details: Optional[Dict[str, Any]] = None


class DatabaseStatus(BaseModel):
    """数据库状态"""
    connected: bool
    version: Optional[str] = None
    tables_count: int = 0
    total_records: Dict[str, int] = {}  # {"users": 10, "cameras": 5, ...}


class SystemStatusResponse(BaseModel):
    """系统状态响应"""
    app_name: str
    app_version: str
    environment: str  # development/production
    uptime_seconds: float
    uptime_formatted: str
    current_time: datetime
    disk_usage: List[DiskUsage]
    database: DatabaseStatus
    services: List[ServiceStatus]
    system_info: Dict[str, Any]  # CPU、内存等
