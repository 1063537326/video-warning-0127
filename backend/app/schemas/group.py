"""
人员分组管理 Schemas
- 分组创建、更新、查询相关的数据模型
"""
from pydantic import BaseModel, Field, field_validator
from typing import Optional, List
from datetime import datetime
import re


class GroupBase(BaseModel):
    """分组基础字段"""
    name: str = Field(..., min_length=1, max_length=100, description="分组名称")
    description: Optional[str] = Field(None, max_length=500, description="分组描述")
    color: Optional[str] = Field(None, max_length=20, description="标签颜色 (如 #FF5733)")
    alert_enabled: bool = Field(default=True, description="是否启用报警")
    alert_priority: int = Field(default=0, ge=0, le=10, description="报警优先级 (0-10)")
    sort_order: int = Field(default=0, ge=0, description="排序顺序")

    @field_validator('color')
    @classmethod
    def validate_color(cls, v: Optional[str]) -> Optional[str]:
        """验证颜色格式"""
        if v is not None and v != "":
            # 支持十六进制颜色和常见颜色名
            hex_pattern = r'^#([A-Fa-f0-9]{6}|[A-Fa-f0-9]{3})$'
            color_names = ['red', 'green', 'blue', 'yellow', 'orange', 'purple', 
                          'pink', 'black', 'white', 'gray', 'grey', 'cyan', 'magenta']
            if not re.match(hex_pattern, v) and v.lower() not in color_names:
                raise ValueError('Color must be hex format (#RRGGBB or #RGB) or valid color name')
        return v


class GroupCreate(GroupBase):
    """创建分组请求"""
    pass


class GroupUpdate(BaseModel):
    """更新分组请求"""
    name: Optional[str] = Field(None, min_length=1, max_length=100, description="分组名称")
    description: Optional[str] = Field(None, max_length=500, description="分组描述")
    color: Optional[str] = Field(None, max_length=20, description="标签颜色")
    alert_enabled: Optional[bool] = Field(None, description="是否启用报警")
    alert_priority: Optional[int] = Field(None, ge=0, le=10, description="报警优先级")
    sort_order: Optional[int] = Field(None, ge=0, description="排序顺序")

    @field_validator('color')
    @classmethod
    def validate_color(cls, v: Optional[str]) -> Optional[str]:
        """验证颜色格式"""
        if v is not None and v != "":
            hex_pattern = r'^#([A-Fa-f0-9]{6}|[A-Fa-f0-9]{3})$'
            color_names = ['red', 'green', 'blue', 'yellow', 'orange', 'purple', 
                          'pink', 'black', 'white', 'gray', 'grey', 'cyan', 'magenta']
            if not re.match(hex_pattern, v) and v.lower() not in color_names:
                raise ValueError('Color must be hex format (#RRGGBB or #RGB) or valid color name')
        return v


class GroupResponse(BaseModel):
    """分组响应模型"""
    id: int
    name: str
    description: Optional[str] = None
    color: Optional[str] = None
    alert_enabled: bool
    alert_priority: int
    sort_order: int
    person_count: int = 0  # 关联的人员数量
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class GroupSimpleResponse(BaseModel):
    """分组简单响应模型（用于下拉选择等场景）"""
    id: int
    name: str
    color: Optional[str] = None
    alert_enabled: bool

    class Config:
        from_attributes = True


class GroupListResponse(BaseModel):
    """分组列表响应"""
    items: List[GroupResponse]
    total: int
    page: int
    page_size: int
    total_pages: int


class GroupStatsResponse(BaseModel):
    """分组统计响应"""
    id: int
    name: str
    color: Optional[str] = None
    person_count: int
    alert_enabled: bool
    alert_priority: int


class GroupAlertToggle(BaseModel):
    """切换报警状态请求"""
    alert_enabled: bool = Field(..., description="是否启用报警")
