"""
Authentication schemas
"""
from pydantic import BaseModel, EmailStr
from typing import Optional


class LoginRequest(BaseModel):
    """Login request"""
    username: str
    password: str


class TokenResponse(BaseModel):
    """Token response"""
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class RefreshTokenRequest(BaseModel):
    """Refresh token request"""
    refresh_token: str


class ChangePasswordRequest(BaseModel):
    """Change password request"""
    old_password: str
    new_password: str


class UserResponse(BaseModel):
    """User response"""
    id: int
    username: str
    email: Optional[str] = None
    phone: Optional[str] = None
    role: str
    is_active: bool

    class Config:
        from_attributes = True
