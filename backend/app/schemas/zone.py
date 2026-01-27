"""
摄像头区域管理 Schemas
- 区域创建、更新、查询相关的数据模型
"""
from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime


class ZoneBase(BaseModel):
    """区域基础字段"""
    name: str = Field(..., min_length=1, max_length=100, description="区域名称")
    description: Optional[str] = Field(None, max_length=500, description="区域描述")
    building: Optional[str] = Field(None, max_length=100, description="楼栋")
    floor: Optional[str] = Field(None, max_length=50, description="楼层")
    sort_order: int = Field(default=0, ge=0, description="排序顺序")


class ZoneCreate(ZoneBase):
    """创建区域请求"""
    pass


class ZoneUpdate(BaseModel):
    """更新区域请求"""
    name: Optional[str] = Field(None, min_length=1, max_length=100, description="区域名称")
    description: Optional[str] = Field(None, max_length=500, description="区域描述")
    building: Optional[str] = Field(None, max_length=100, description="楼栋")
    floor: Optional[str] = Field(None, max_length=50, description="楼层")
    sort_order: Optional[int] = Field(None, ge=0, description="排序顺序")


class ZoneResponse(BaseModel):
    """区域响应模型"""
    id: int
    name: str
    description: Optional[str] = None
    building: Optional[str] = None
    floor: Optional[str] = None
    sort_order: int
    camera_count: int = 0  # 关联的摄像头数量
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class ZoneSimpleResponse(BaseModel):
    """区域简单响应模型（用于下拉选择等场景）"""
    id: int
    name: str
    building: Optional[str] = None
    floor: Optional[str] = None

    class Config:
        from_attributes = True


class ZoneListResponse(BaseModel):
    """区域列表响应"""
    items: List[ZoneResponse]
    total: int
    page: int
    page_size: int
    total_pages: int


class ZoneTreeNode(BaseModel):
    """区域树节点（按楼栋分组）"""
    building: str
    floors: List[dict]  # [{"floor": "1F", "zones": [ZoneSimpleResponse]}]


class ZoneTreeResponse(BaseModel):
    """区域树响应（按楼栋-楼层分组）"""
    items: List[ZoneTreeNode]
