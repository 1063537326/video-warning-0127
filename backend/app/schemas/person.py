"""
人员管理 Schemas
- 人员创建、更新、查询相关的数据模型
- 人脸图片相关的数据模型
"""
from pydantic import BaseModel, Field, field_validator
from typing import Optional, List
from datetime import datetime
import re


class GroupInfo(BaseModel):
    """分组简要信息（嵌入人员响应中）"""
    id: int
    name: str
    color: Optional[str] = None

    class Config:
        from_attributes = True


class FaceImageResponse(BaseModel):
    """人脸图片响应模型"""
    id: int
    image_path: str
    image_id: Optional[str] = None  # CompreFace image_id
    image_url: Optional[str] = None  # 完整访问 URL
    quality_score: Optional[float] = None
    is_primary: bool
    created_at: datetime

    class Config:
        from_attributes = True


class PersonBase(BaseModel):
    """人员基础字段"""
    name: str = Field(..., min_length=1, max_length=100, description="姓名")
    employee_id: Optional[str] = Field(None, max_length=50, description="工号")
    group_id: Optional[int] = Field(None, description="分组 ID")
    department: Optional[str] = Field(None, max_length=100, description="部门")
    phone: Optional[str] = Field(None, max_length=20, description="电话")
    remark: Optional[str] = Field(None, max_length=500, description="备注")

    @field_validator('phone')
    @classmethod
    def validate_phone(cls, v: Optional[str]) -> Optional[str]:
        """验证电话格式"""
        if v is not None and v != "":
            # 简单验证：数字和常见符号
            if not re.match(r'^[\d\-\+\s\(\)]+$', v):
                raise ValueError('Invalid phone number format')
        return v


class PersonBase(BaseModel):
    """人员基础字段"""
    name: str = Field(..., min_length=1, max_length=100, description="姓名")
    employee_id: Optional[str] = Field(None, max_length=50, description="工号")
    group_id: Optional[int] = Field(None, description="分组 ID")
    department: Optional[str] = Field(None, max_length=100, description="部门")
    phone: Optional[str] = Field(None, max_length=20, description="电话")
    remark: Optional[str] = Field(None, max_length=500, description="备注")

    @field_validator('phone')
    @classmethod
    def validate_phone(cls, v: Optional[str]) -> Optional[str]:
        """验证电话格式"""
        if v is not None and v != "":
            # 简单验证：数字和常见符号
            if not re.match(r'^[\d\-\+\s\(\)]+$', v):
                raise ValueError('Invalid phone number format')
        return v


class PersonCreate(PersonBase):
    """创建人员请求"""
    is_active: bool = Field(default=True, description="是否在职")


class PersonUpdate(BaseModel):
    """更新人员请求"""
    name: Optional[str] = Field(None, min_length=1, max_length=100, description="姓名")
    employee_id: Optional[str] = Field(None, max_length=50, description="工号")
    group_id: Optional[int] = Field(None, description="分组 ID")
    department: Optional[str] = Field(None, max_length=100, description="部门")
    phone: Optional[str] = Field(None, max_length=20, description="电话")
    remark: Optional[str] = Field(None, max_length=500, description="备注")
    is_active: Optional[bool] = Field(None, description="是否在职")

    @field_validator('phone')
    @classmethod
    def validate_phone(cls, v: Optional[str]) -> Optional[str]:
        """验证电话格式"""
        if v is not None and v != "":
            if not re.match(r'^[\d\-\+\s\(\)]+$', v):
                raise ValueError('Invalid phone number format')
        return v


class PersonStatusUpdate(BaseModel):
    """更新人员状态请求"""
    is_active: bool = Field(..., description="是否在职")


class PersonResponse(BaseModel):
    """人员响应模型"""
    id: int
    name: str
    employee_id: Optional[str] = None
    group_id: Optional[int] = None
    group: Optional[GroupInfo] = None
    department: Optional[str] = None
    phone: Optional[str] = None
    remark: Optional[str] = None
    is_active: bool
    face_count: int = 0  # 人脸图片数量
    primary_face: Optional[FaceImageResponse] = None  # 主图
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class PersonDetailResponse(PersonResponse):
    """人员详情响应模型（包含所有人脸图片）"""
    face_images: List[FaceImageResponse] = []


class PersonSimpleResponse(BaseModel):
    """人员简单响应模型（用于下拉选择等场景）"""
    id: int
    name: str
    employee_id: Optional[str] = None
    group_id: Optional[int] = None
    is_active: bool

    class Config:
        from_attributes = True


class PersonListResponse(BaseModel):
    """人员列表响应"""
    items: List[PersonResponse]
    total: int
    page: int
    page_size: int
    total_pages: int


class FaceUploadResponse(BaseModel):
    """人脸图片上传响应"""
    id: int
    image_path: str
    image_id: Optional[str] = None  # CompreFace image_id
    image_url: Optional[str] = None
    quality_score: Optional[float] = None
    is_primary: bool
    created_at: datetime
    feature_extracted: bool = False  # 是否成功提取并同步特征


class PersonImportItem(BaseModel):
    """批量导入人员单条数据"""
    name: str = Field(..., min_length=1, max_length=100, description="姓名")
    employee_id: Optional[str] = Field(None, max_length=50, description="工号")
    group_id: Optional[int] = Field(None, description="分组 ID")
    department: Optional[str] = Field(None, max_length=100, description="部门")
    phone: Optional[str] = Field(None, max_length=20, description="电话")
    remark: Optional[str] = Field(None, max_length=500, description="备注")


class PersonImportRequest(BaseModel):
    """批量导入人员请求"""
    items: List[PersonImportItem] = Field(..., min_length=1, max_length=100, description="人员列表")


class PersonImportResult(BaseModel):
    """批量导入结果"""
    success_count: int
    failed_count: int
    failed_items: List[dict] = []  # 失败的条目及原因
