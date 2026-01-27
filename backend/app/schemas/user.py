"""
用户管理 Schemas
- 用户创建、更新、查询相关的数据模型
"""
from pydantic import BaseModel, EmailStr, Field
from typing import Optional, List
from datetime import datetime
from enum import Enum


class UserRoleEnum(str, Enum):
    """用户角色枚举"""
    ADMIN = "admin"
    OPERATOR = "operator"


class UserBase(BaseModel):
    """用户基础字段"""
    username: str = Field(..., min_length=3, max_length=50, description="用户名")
    email: Optional[EmailStr] = Field(None, description="邮箱")
    phone: Optional[str] = Field(None, max_length=20, description="手机号")
    role: UserRoleEnum = Field(default=UserRoleEnum.OPERATOR, description="角色")


class UserCreate(UserBase):
    """创建用户请求"""
    password: str = Field(..., min_length=6, max_length=50, description="密码")


class UserUpdate(BaseModel):
    """更新用户请求"""
    email: Optional[EmailStr] = Field(None, description="邮箱")
    phone: Optional[str] = Field(None, max_length=20, description="手机号")
    role: Optional[UserRoleEnum] = Field(None, description="角色")


class UserStatusUpdate(BaseModel):
    """更新用户状态请求"""
    is_active: bool = Field(..., description="是否启用")


class ResetPasswordRequest(BaseModel):
    """重置密码请求"""
    new_password: str = Field(..., min_length=6, max_length=50, description="新密码")


class UserResponse(BaseModel):
    """用户响应模型"""
    id: int
    username: str
    email: Optional[str] = None
    phone: Optional[str] = None
    role: str
    is_active: bool

    class Config:
        from_attributes = True


class UserDetailResponse(BaseModel):
    """用户详情响应模型"""
    id: int
    username: str
    email: Optional[str] = None
    phone: Optional[str] = None
    role: str
    is_active: bool
    last_login_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class UserListResponse(BaseModel):
    """用户列表响应"""
    items: List[UserDetailResponse]
    total: int
    page: int
    page_size: int
    total_pages: int
