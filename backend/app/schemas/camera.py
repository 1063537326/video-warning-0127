"""
摄像头管理 Schemas
- 摄像头创建、更新、查询相关的数据模型
"""
from pydantic import BaseModel, Field, field_validator
from typing import Optional, List, Any
from datetime import datetime
from enum import Enum


class CameraStatusEnum(str, Enum):
    """摄像头状态枚举"""
    ONLINE = "online"
    OFFLINE = "offline"
    ERROR = "error"


class CameraBase(BaseModel):
    """摄像头基础字段"""
    name: str = Field(..., min_length=1, max_length=100, description="摄像头名称")
    zone_id: Optional[int] = Field(None, description="所属区域 ID")
    rtsp_url: str = Field(..., min_length=1, max_length=500, description="RTSP 流地址")
    username: Optional[str] = Field(None, max_length=100, description="认证用户名")
    password: Optional[str] = Field(None, max_length=255, description="认证密码")
    resolution: Optional[str] = Field(None, max_length=20, description="分辨率 (如 1920x1080)")
    fps: int = Field(default=25, ge=1, le=60, description="帧率")
    config: Optional[dict] = Field(None, description="扩展配置 (ROI、灵敏度等)")

    @field_validator('resolution')
    @classmethod
    def validate_resolution(cls, v: Optional[str]) -> Optional[str]:
        """验证分辨率格式"""
        if v is not None and v != "":
            import re
            if not re.match(r'^\d+x\d+$', v):
                raise ValueError('Resolution must be in format WIDTHxHEIGHT (e.g., 1920x1080)')
        return v


class CameraCreate(CameraBase):
    """创建摄像头请求"""
    is_enabled: bool = Field(default=True, description="是否启用分析")


class CameraUpdate(BaseModel):
    """更新摄像头请求"""
    name: Optional[str] = Field(None, min_length=1, max_length=100, description="摄像头名称")
    zone_id: Optional[int] = Field(None, description="所属区域 ID")
    rtsp_url: Optional[str] = Field(None, min_length=1, max_length=500, description="RTSP 流地址")
    username: Optional[str] = Field(None, max_length=100, description="认证用户名")
    password: Optional[str] = Field(None, max_length=255, description="认证密码")
    resolution: Optional[str] = Field(None, max_length=20, description="分辨率")
    fps: Optional[int] = Field(None, ge=1, le=60, description="帧率")
    config: Optional[dict] = Field(None, description="扩展配置")

    @field_validator('resolution')
    @classmethod
    def validate_resolution(cls, v: Optional[str]) -> Optional[str]:
        """验证分辨率格式"""
        if v is not None and v != "":
            import re
            if not re.match(r'^\d+x\d+$', v):
                raise ValueError('Resolution must be in format WIDTHxHEIGHT (e.g., 1920x1080)')
        return v


class CameraToggleRequest(BaseModel):
    """切换摄像头启用状态请求"""
    is_enabled: bool = Field(..., description="是否启用")


class ZoneInfo(BaseModel):
    """区域简要信息（嵌入摄像头响应中）"""
    id: int
    name: str
    building: Optional[str] = None
    floor: Optional[str] = None

    class Config:
        from_attributes = True


class CameraResponse(BaseModel):
    """摄像头响应模型"""
    id: int
    name: str
    zone_id: Optional[int] = None
    zone: Optional[ZoneInfo] = None
    rtsp_url: str
    username: Optional[str] = None
    # 注意：不返回密码
    resolution: Optional[str] = None
    fps: int
    status: str
    is_enabled: bool
    last_heartbeat_at: Optional[datetime] = None
    config: Optional[dict] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class CameraSimpleResponse(BaseModel):
    """摄像头简单响应模型（用于下拉选择等场景）"""
    id: int
    name: str
    zone_id: Optional[int] = None
    status: str
    is_enabled: bool

    class Config:
        from_attributes = True


class CameraListResponse(BaseModel):
    """摄像头列表响应"""
    items: List[CameraResponse]
    total: int
    page: int
    page_size: int
    total_pages: int


class CameraStatusResponse(BaseModel):
    """摄像头状态响应"""
    id: int
    name: str
    status: str
    is_enabled: bool
    last_heartbeat_at: Optional[datetime] = None


class CameraStatusListResponse(BaseModel):
    """摄像头状态列表响应"""
    items: List[CameraStatusResponse]
    online_count: int
    offline_count: int
    error_count: int
    total: int


class CameraTestResult(BaseModel):
    """摄像头连通性测试结果"""
    success: bool
    message: str
    response_time_ms: Optional[float] = None
    resolution_detected: Optional[str] = None
    fps_detected: Optional[int] = None
