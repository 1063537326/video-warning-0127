"""
操作日志接口模块

提供操作日志的查询、统计功能。

功能列表：
- GET /operation-logs - 操作日志列表（支持多维度筛选）
- GET /operation-logs/statistics - 操作日志统计
- GET /operation-logs/{log_id} - 操作日志详情
- POST /operation-logs - 创建操作日志（内部接口）
- DELETE /operation-logs - 批量删除旧日志（管理员）
"""
from typing import Optional
from datetime import datetime, timezone, timedelta
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy import select, func, delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db, get_current_active_user, require_admin
from app.models.system import OperationLog
from app.models.user import User
from app.schemas.log import (
    OperationLogResponse,
    OperationLogListResponse,
    OperationLogCreateRequest,
    OperationLogStatistics,
    UserSimpleInfo,
    ACTION_LABELS,
    TARGET_TYPE_LABELS,
)

router = APIRouter(prefix="/operation-logs", tags=["操作日志"])


def build_log_response(log: OperationLog, user: User = None) -> OperationLogResponse:
    """
    构建操作日志响应对象
    
    Args:
        log: 操作日志 ORM 对象
        user: 用户对象
        
    Returns:
        OperationLogResponse: 操作日志响应模型
    """
    user_info = None
    if user:
        user_info = UserSimpleInfo(id=user.id, username=user.username)
    
    return OperationLogResponse(
        id=log.id,
        user_id=log.user_id,
        user=user_info,
        action=log.action,
        action_label=ACTION_LABELS.get(log.action, log.action),
        target_type=log.target_type,
        target_type_label=TARGET_TYPE_LABELS.get(log.target_type, log.target_type or ""),
        target_id=log.target_id,
        details=log.details,
        ip_address=log.ip_address,
        user_agent=log.user_agent,
        created_at=log.created_at,
    )


@router.get("", response_model=OperationLogListResponse, summary="获取操作日志列表")
async def get_operation_logs(
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=100, description="每页数量"),
    user_id: Optional[int] = Query(None, description="用户 ID"),
    action: Optional[str] = Query(None, description="操作类型"),
    target_type: Optional[str] = Query(None, description="目标类型"),
    target_id: Optional[int] = Query(None, description="目标 ID"),
    start_date: Optional[datetime] = Query(None, description="开始时间"),
    end_date: Optional[datetime] = Query(None, description="结束时间"),
    keyword: Optional[str] = Query(None, description="关键词搜索（IP地址）"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    """
    获取操作日志列表

    支持多维度筛选，仅管理员可访问。

    Args:
        page: 页码
        page_size: 每页数量
        user_id: 用户 ID 筛选
        action: 操作类型筛选
        target_type: 目标类型筛选
        target_id: 目标 ID 筛选
        start_date: 开始时间
        end_date: 结束时间
        keyword: 关键词（IP 地址）

    Returns:
        OperationLogListResponse: 操作日志列表和分页信息
    """
    # 构建查询
    query = select(OperationLog)
    count_query = select(func.count(OperationLog.id))

    # 用户筛选
    if user_id is not None:
        query = query.where(OperationLog.user_id == user_id)
        count_query = count_query.where(OperationLog.user_id == user_id)

    # 操作类型筛选
    if action:
        query = query.where(OperationLog.action == action)
        count_query = count_query.where(OperationLog.action == action)

    # 目标类型筛选
    if target_type:
        query = query.where(OperationLog.target_type == target_type)
        count_query = count_query.where(OperationLog.target_type == target_type)

    # 目标 ID 筛选
    if target_id is not None:
        query = query.where(OperationLog.target_id == target_id)
        count_query = count_query.where(OperationLog.target_id == target_id)

    # 时间范围筛选
    if start_date:
        query = query.where(OperationLog.created_at >= start_date)
        count_query = count_query.where(OperationLog.created_at >= start_date)
    if end_date:
        query = query.where(OperationLog.created_at <= end_date)
        count_query = count_query.where(OperationLog.created_at <= end_date)

    # 关键词搜索（IP 地址）
    if keyword:
        query = query.where(OperationLog.ip_address.ilike(f"%{keyword}%"))
        count_query = count_query.where(OperationLog.ip_address.ilike(f"%{keyword}%"))

    # 获取总数
    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0

    # 计算总页数
    total_pages = (total + page_size - 1) // page_size

    # 分页查询
    offset = (page - 1) * page_size
    query = query.order_by(OperationLog.created_at.desc()).offset(offset).limit(page_size)

    result = await db.execute(query)
    logs = result.scalars().all()

    # 批量获取用户信息
    user_ids = list(set(log.user_id for log in logs if log.user_id))
    users_map = {}
    if user_ids:
        users_result = await db.execute(
            select(User).where(User.id.in_(user_ids))
        )
        for user in users_result.scalars().all():
            users_map[user.id] = user

    # 构建响应
    items = [
        build_log_response(log, users_map.get(log.user_id))
        for log in logs
    ]

    return OperationLogListResponse(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
    )


@router.get("/statistics", response_model=OperationLogStatistics, summary="获取操作日志统计")
async def get_log_statistics(
    start_date: Optional[datetime] = Query(None, description="开始时间"),
    end_date: Optional[datetime] = Query(None, description="结束时间"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    """
    获取操作日志统计数据

    仅管理员可访问。

    Args:
        start_date: 开始时间
        end_date: 结束时间

    Returns:
        OperationLogStatistics: 操作日志统计
    """
    now = datetime.now(timezone.utc)
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    week_start = today_start - timedelta(days=today_start.weekday())

    # 基础查询条件
    base_filter = []
    if start_date:
        base_filter.append(OperationLog.created_at >= start_date)
    if end_date:
        base_filter.append(OperationLog.created_at <= end_date)

    # 总数统计
    if base_filter:
        total_result = await db.execute(
            select(func.count(OperationLog.id)).where(*base_filter)
        )
    else:
        total_result = await db.execute(select(func.count(OperationLog.id)))
    total = total_result.scalar() or 0

    # 按操作类型统计
    action_query = select(OperationLog.action, func.count(OperationLog.id)).group_by(OperationLog.action)
    if base_filter:
        action_query = action_query.where(*base_filter)
    action_result = await db.execute(action_query)
    by_action = {row[0]: row[1] for row in action_result.fetchall()}

    # 按目标类型统计
    target_query = (
        select(OperationLog.target_type, func.count(OperationLog.id))
        .where(OperationLog.target_type.isnot(None))
        .group_by(OperationLog.target_type)
    )
    if base_filter:
        target_query = target_query.where(*base_filter)
    target_result = await db.execute(target_query)
    by_target_type = {row[0]: row[1] for row in target_result.fetchall()}

    # 按用户统计（前 10）
    user_query = (
        select(OperationLog.user_id, func.count(OperationLog.id).label('count'))
        .where(OperationLog.user_id.isnot(None))
        .group_by(OperationLog.user_id)
        .order_by(func.count(OperationLog.id).desc())
        .limit(10)
    )
    if base_filter:
        user_query = user_query.where(*base_filter)
    user_result = await db.execute(user_query)
    user_counts = user_result.fetchall()

    # 获取用户名
    user_ids = [row[0] for row in user_counts]
    users_map = {}
    if user_ids:
        users_result = await db.execute(
            select(User).where(User.id.in_(user_ids))
        )
        users_map = {u.id: u.username for u in users_result.scalars().all()}

    by_user = [
        {"user_id": row[0], "username": users_map.get(row[0], "unknown"), "count": row[1]}
        for row in user_counts
    ]

    # 今日统计
    today_result = await db.execute(
        select(func.count(OperationLog.id)).where(OperationLog.created_at >= today_start)
    )
    today_count = today_result.scalar() or 0

    # 本周统计
    week_result = await db.execute(
        select(func.count(OperationLog.id)).where(OperationLog.created_at >= week_start)
    )
    week_count = week_result.scalar() or 0

    return OperationLogStatistics(
        total=total,
        by_action=by_action,
        by_target_type=by_target_type,
        by_user=by_user,
        today_count=today_count,
        week_count=week_count,
    )


@router.get("/actions", summary="获取操作类型列表")
async def get_action_types(current_user: User = Depends(require_admin)):
    """
    获取所有操作类型及其标签

    Returns:
        dict: 操作类型列表
    """
    return {
        "items": [
            {"value": k, "label": v}
            for k, v in ACTION_LABELS.items()
        ]
    }


@router.get("/target-types", summary="获取目标类型列表")
async def get_target_types(current_user: User = Depends(require_admin)):
    """
    获取所有目标类型及其标签

    Returns:
        dict: 目标类型列表
    """
    return {
        "items": [
            {"value": k, "label": v}
            for k, v in TARGET_TYPE_LABELS.items()
        ]
    }


@router.get("/{log_id}", response_model=OperationLogResponse, summary="获取操作日志详情")
async def get_operation_log(
    log_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    """
    获取操作日志详情

    Args:
        log_id: 日志 ID

    Returns:
        OperationLogResponse: 操作日志详情

    Raises:
        HTTPException 404: 日志不存在
    """
    result = await db.execute(
        select(OperationLog).where(OperationLog.id == log_id)
    )
    log = result.scalar_one_or_none()

    if not log:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Operation log not found",
        )

    # 获取用户信息
    user = None
    if log.user_id:
        user_result = await db.execute(
            select(User).where(User.id == log.user_id)
        )
        user = user_result.scalar_one_or_none()

    return build_log_response(log, user)


@router.post("", response_model=OperationLogResponse, status_code=status.HTTP_201_CREATED,
             summary="创建操作日志（内部接口）")
async def create_operation_log(
    log_data: OperationLogCreateRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """
    创建操作日志（内部接口）

    用于手动记录操作日志。

    Args:
        log_data: 日志数据

    Returns:
        OperationLogResponse: 创建的日志
    """
    new_log = OperationLog(
        user_id=log_data.user_id or current_user.id,
        action=log_data.action.value,
        target_type=log_data.target_type.value if log_data.target_type else None,
        target_id=log_data.target_id,
        details=log_data.details,
        ip_address=log_data.ip_address,
        user_agent=log_data.user_agent,
    )

    db.add(new_log)
    await db.commit()
    await db.refresh(new_log)

    # 获取用户信息
    user = None
    if new_log.user_id:
        user_result = await db.execute(
            select(User).where(User.id == new_log.user_id)
        )
        user = user_result.scalar_one_or_none()

    return build_log_response(new_log, user)


@router.delete("", summary="批量删除旧日志",
               dependencies=[Depends(require_admin)])
async def delete_old_logs(
    days_to_keep: int = Query(90, ge=1, le=365, description="保留最近几天的日志"),
    db: AsyncSession = Depends(get_db),
):
    """
    批量删除旧日志

    仅管理员可操作。

    Args:
        days_to_keep: 保留天数

    Returns:
        dict: 删除结果
    """
    cutoff_date = datetime.now(timezone.utc) - timedelta(days=days_to_keep)
    
    # 查询要删除的数量
    count_result = await db.execute(
        select(func.count(OperationLog.id)).where(OperationLog.created_at < cutoff_date)
    )
    count = count_result.scalar() or 0
    
    if count == 0:
        return {"message": "No logs to delete", "deleted_count": 0}
    
    # 删除旧日志
    await db.execute(
        delete(OperationLog).where(OperationLog.created_at < cutoff_date)
    )
    await db.commit()
    
    return {"message": f"Deleted {count} old logs", "deleted_count": count}
