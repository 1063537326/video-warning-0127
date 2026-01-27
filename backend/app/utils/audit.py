"""
操作日志审计工具

提供记录用户操作的工具函数和依赖。
"""
from typing import Optional, Dict, Any
from datetime import datetime, timezone
from fastapi import Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.system import OperationLog


async def log_operation(
    db: AsyncSession,
    action: str,
    user_id: Optional[int] = None,
    target_type: Optional[str] = None,
    target_id: Optional[int] = None,
    details: Optional[Dict[str, Any]] = None,
    ip_address: Optional[str] = None,
    user_agent: Optional[str] = None,
) -> OperationLog:
    """
    记录操作日志
    
    Args:
        db: 数据库会话
        action: 操作类型 (create/update/delete/login/logout/etc.)
        user_id: 用户 ID
        target_type: 目标类型 (camera/person/alert/config/etc.)
        target_id: 目标 ID
        details: 详情（变更前后等）
        ip_address: IP 地址
        user_agent: User-Agent
        
    Returns:
        OperationLog: 创建的日志记录
    """
    log = OperationLog(
        user_id=user_id,
        action=action,
        target_type=target_type,
        target_id=target_id,
        details=details,
        ip_address=ip_address,
        user_agent=user_agent,
    )
    db.add(log)
    await db.commit()
    await db.refresh(log)
    return log


def get_client_ip(request: Request) -> str:
    """
    获取客户端 IP 地址
    
    优先从 X-Forwarded-For 获取（反向代理场景）
    
    Args:
        request: FastAPI 请求对象
        
    Returns:
        str: 客户端 IP 地址
    """
    # 尝试从反向代理头获取
    forwarded_for = request.headers.get("X-Forwarded-For")
    if forwarded_for:
        # X-Forwarded-For 可能包含多个 IP，取第一个
        return forwarded_for.split(",")[0].strip()
    
    # 尝试从 X-Real-IP 获取
    real_ip = request.headers.get("X-Real-IP")
    if real_ip:
        return real_ip
    
    # 直接获取客户端 IP
    if request.client:
        return request.client.host
    
    return "unknown"


def get_user_agent(request: Request) -> str:
    """
    获取 User-Agent
    
    Args:
        request: FastAPI 请求对象
        
    Returns:
        str: User-Agent 字符串
    """
    return request.headers.get("User-Agent", "unknown")


async def log_operation_from_request(
    db: AsyncSession,
    request: Request,
    action: str,
    user_id: Optional[int] = None,
    target_type: Optional[str] = None,
    target_id: Optional[int] = None,
    details: Optional[Dict[str, Any]] = None,
) -> OperationLog:
    """
    从请求对象记录操作日志
    
    自动提取 IP 地址和 User-Agent
    
    Args:
        db: 数据库会话
        request: FastAPI 请求对象
        action: 操作类型
        user_id: 用户 ID
        target_type: 目标类型
        target_id: 目标 ID
        details: 详情
        
    Returns:
        OperationLog: 创建的日志记录
    """
    return await log_operation(
        db=db,
        action=action,
        user_id=user_id,
        target_type=target_type,
        target_id=target_id,
        details=details,
        ip_address=get_client_ip(request),
        user_agent=get_user_agent(request),
    )


def build_change_details(
    before: Optional[Dict[str, Any]] = None,
    after: Optional[Dict[str, Any]] = None,
    changes: Optional[Dict[str, Any]] = None,
    extra: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    构建变更详情
    
    Args:
        before: 变更前的数据
        after: 变更后的数据
        changes: 变更的字段列表
        extra: 额外信息
        
    Returns:
        Dict: 变更详情字典
    """
    details = {}
    
    if before is not None:
        details["before"] = before
    if after is not None:
        details["after"] = after
    if changes is not None:
        details["changes"] = changes
    if extra is not None:
        details.update(extra)
    
    return details if details else None
