"""
操作日志 Schemas
- 操作日志查询、记录相关的数据模型
"""
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum


class ActionTypeEnum(str, Enum):
    """操作类型枚举"""
    CREATE = "create"
    UPDATE = "update"
    DELETE = "delete"
    LOGIN = "login"
    LOGOUT = "logout"
    EXPORT = "export"
    IMPORT = "import"
    PROCESS = "process"  # 处理报警
    IGNORE = "ignore"    # 忽略报警
    UPLOAD = "upload"    # 上传文件
    CLEANUP = "cleanup"  # 数据清理


class TargetTypeEnum(str, Enum):
    """目标类型枚举"""
    USER = "user"
    CAMERA = "camera"
    ZONE = "zone"
    PERSON = "person"
    GROUP = "group"
    ALERT = "alert"
    CONFIG = "config"
    FACE = "face"
    SYSTEM = "system"


class UserSimpleInfo(BaseModel):
    """用户简要信息"""
    id: int
    username: str

    class Config:
        from_attributes = True


class OperationLogResponse(BaseModel):
    """操作日志响应"""
    id: int
    user_id: Optional[int] = None
    user: Optional[UserSimpleInfo] = None
    action: str
    action_label: str = ""  # 操作类型的中文标签
    target_type: Optional[str] = None
    target_type_label: str = ""  # 目标类型的中文标签
    target_id: Optional[int] = None
    details: Optional[Dict[str, Any]] = None
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True


class OperationLogListResponse(BaseModel):
    """操作日志列表响应"""
    items: List[OperationLogResponse]
    total: int
    page: int
    page_size: int
    total_pages: int


class OperationLogCreateRequest(BaseModel):
    """创建操作日志请求（内部使用）"""
    user_id: Optional[int] = Field(None, description="用户 ID")
    action: ActionTypeEnum = Field(..., description="操作类型")
    target_type: Optional[TargetTypeEnum] = Field(None, description="目标类型")
    target_id: Optional[int] = Field(None, description="目标 ID")
    details: Optional[Dict[str, Any]] = Field(None, description="详情")
    ip_address: Optional[str] = Field(None, description="IP 地址")
    user_agent: Optional[str] = Field(None, description="User-Agent")


class OperationLogStatistics(BaseModel):
    """操作日志统计"""
    total: int = 0
    by_action: Dict[str, int] = {}  # {"create": 10, "update": 5, ...}
    by_target_type: Dict[str, int] = {}  # {"camera": 10, "person": 5, ...}
    by_user: List[Dict[str, Any]] = []  # [{"user_id": 1, "username": "admin", "count": 50}]
    today_count: int = 0
    week_count: int = 0


# 操作类型标签映射
ACTION_LABELS = {
    "create": "创建",
    "update": "更新",
    "delete": "删除",
    "login": "登录",
    "logout": "登出",
    "export": "导出",
    "import": "导入",
    "process": "处理",
    "ignore": "忽略",
    "upload": "上传",
    "cleanup": "清理",
}

# 目标类型标签映射
TARGET_TYPE_LABELS = {
    "user": "用户",
    "camera": "摄像头",
    "zone": "区域",
    "person": "人员",
    "group": "分组",
    "alert": "报警",
    "config": "配置",
    "face": "人脸",
    "system": "系统",
}
