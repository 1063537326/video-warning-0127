"""
Common schemas
"""
from pydantic import BaseModel
from typing import Optional, Generic, TypeVar, List

T = TypeVar('T')


class ResponseBase(BaseModel):
    """Base response"""
    success: bool = True
    message: str = "OK"


class ErrorResponse(BaseModel):
    """Error response"""
    success: bool = False
    message: str
    detail: Optional[str] = None


class PaginatedResponse(BaseModel, Generic[T]):
    """Paginated response"""
    items: List[T]
    total: int
    page: int
    page_size: int
    total_pages: int
