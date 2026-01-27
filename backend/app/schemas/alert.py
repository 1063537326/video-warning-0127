"""
报警记录 Schemas
- 报警查询、处理、统计相关的数据模型
"""
from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime
from enum import Enum


class AlertTypeEnum(str, Enum):
    """报警类型枚举"""
    STRANGER = "stranger"      # 陌生人
    KNOWN = "known"            # 已知人员
    BLACKLIST = "blacklist"    # 黑名单


class AlertStatusEnum(str, Enum):
    """报警状态枚举"""
    PENDING = "pending"        # 待处理
    PROCESSED = "processed"    # 已处理
    IGNORED = "ignored"        # 已忽略


class CameraInfo(BaseModel):
    """摄像头简要信息（嵌入报警响应中）"""
    id: int
    name: str
    zone_id: Optional[int] = None
    zone_name: Optional[str] = None

    class Config:
        from_attributes = True


class PersonInfo(BaseModel):
    """人员简要信息（嵌入报警响应中）"""
    id: int
    name: str
    employee_id: Optional[str] = None
    group_id: Optional[int] = None
    group_name: Optional[str] = None
    group_color: Optional[str] = None

    class Config:
        from_attributes = True


class ProcessorInfo(BaseModel):
    """处理人简要信息"""
    id: int
    username: str

    class Config:
        from_attributes = True


class FaceBbox(BaseModel):
    """人脸框坐标"""
    x: int
    y: int
    w: int
    h: int


class AlertResponse(BaseModel):
    """报警响应模型"""
    id: int
    camera_id: int
    camera: Optional[CameraInfo] = None
    alert_type: str
    person_id: Optional[int] = None
    person: Optional[PersonInfo] = None
    confidence: Optional[float] = None
    face_image_path: Optional[str] = None
    face_image_url: Optional[str] = None
    body_image_path: Optional[str] = None
    body_image_url: Optional[str] = None
    full_image_path: Optional[str] = None
    full_image_url: Optional[str] = None
    face_bbox: Optional[dict] = None
    status: str
    processed_by: Optional[int] = None
    processor: Optional[ProcessorInfo] = None
    processed_at: Optional[datetime] = None
    process_remark: Optional[str] = None
    extra_data: Optional[dict] = None
    created_at: datetime

    class Config:
        from_attributes = True


class AlertListResponse(BaseModel):
    """报警列表响应"""
    items: List[AlertResponse]
    total: int
    page: int
    page_size: int
    total_pages: int


class AlertProcessRequest(BaseModel):
    """处理报警请求"""
    remark: Optional[str] = Field(None, max_length=500, description="处理备注")


class AlertIgnoreRequest(BaseModel):
    """忽略报警请求"""
    remark: Optional[str] = Field(None, max_length=500, description="忽略原因")


class AlertFeedbackRequest(BaseModel):
    """人工反馈请求 (注册陌生人)"""
    person_name: str = Field(..., min_length=1, max_length=50, description="人员姓名")
    group_id: int = Field(..., description="所属人员组 ID")
    remark: Optional[str] = Field(None, description="备注")


class AlertBatchProcessRequest(BaseModel):
    """批量处理报警请求"""
    alert_ids: List[int] = Field(..., min_length=1, max_length=100, description="报警 ID 列表")
    action: str = Field(..., description="操作类型 (process/ignore)")
    remark: Optional[str] = Field(None, max_length=500, description="处理备注")


class AlertBatchProcessResult(BaseModel):
    """批量处理结果"""
    success_count: int
    failed_count: int
    failed_ids: List[int] = []


class AlertStatistics(BaseModel):
    """报警统计数据"""
    total: int = 0
    pending: int = 0
    processed: int = 0
    ignored: int = 0
    by_type: dict = {}  # {"stranger": 10, "known": 5, "blacklist": 2}
    by_camera: List[dict] = []  # [{"camera_id": 1, "camera_name": "xxx", "count": 10}]
    today_count: int = 0
    week_count: int = 0
    month_count: int = 0


class AlertTrendItem(BaseModel):
    """报警趋势数据项"""
    date: str
    count: int
    stranger_count: int = 0
    known_count: int = 0
    blacklist_count: int = 0


class AlertTrendResponse(BaseModel):
    """报警趋势响应"""
    items: List[AlertTrendItem]
    period: str  # day/week/month


class AlertCreateRequest(BaseModel):
    """创建报警请求（内部使用，由视频分析引擎调用）"""
    camera_id: int = Field(..., description="摄像头 ID")
    alert_type: AlertTypeEnum = Field(..., description="报警类型")
    person_id: Optional[int] = Field(None, description="人员 ID（已知人员/黑名单时）")
    confidence: Optional[float] = Field(None, ge=0, le=1, description="识别置信度")
    face_image_path: Optional[str] = Field(None, description="人脸截图路径")
    full_image_path: Optional[str] = Field(None, description="全景截图路径")
    face_bbox: Optional[FaceBbox] = Field(None, description="人脸框坐标")
    extra_data: Optional[dict] = Field(None, description="扩展数据")
