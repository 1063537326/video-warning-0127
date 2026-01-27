"""
报警记录接口模块

提供报警记录的查询、处理、统计等功能。

功能列表：
- GET /alerts - 历史报警查询（多维度筛选）
- GET /alerts/statistics - 报警统计数据
- GET /alerts/trend - 报警趋势数据
- GET /alerts/{alert_id} - 报警详情
- PATCH /alerts/{alert_id}/process - 处理报警
- PATCH /alerts/{alert_id}/ignore - 忽略报警
- POST /alerts/batch-process - 批量处理报警
- POST /alerts - 创建报警（内部接口）
- GET /alerts/export - 导出报警记录
"""
import os
import csv
import io
from typing import Optional
from datetime import datetime, timezone, timedelta
from fastapi import APIRouter, Depends, HTTPException, status, Query
from fastapi.responses import StreamingResponse
from sqlalchemy import select, func, or_, and_, case
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.deps import get_db, get_current_active_user, require_admin
from app.models.alert import AlertLog, AlertType, AlertStatus
from app.models.camera import Camera, CameraZone
from app.models.person import KnownPerson, PersonGroup
from app.models.user import User
from app.schemas.alert import (
    AlertResponse,
    AlertListResponse,
    AlertProcessRequest,
    AlertIgnoreRequest,
    AlertBatchProcessRequest,
    AlertBatchProcessResult,
    AlertStatistics,
    AlertTrendItem,
    AlertTrendResponse,
    AlertCreateRequest,
    CameraInfo,
    PersonInfo,
    ProcessorInfo,
    AlertFeedbackRequest, # need to define this or use inline body
)
from app.engine.recognition.client import compreface_client

router = APIRouter(prefix="/alerts", tags=["报警记录"])


def build_alert_response(alert: AlertLog, camera: Camera = None, person: KnownPerson = None, processor: User = None) -> AlertResponse:
    """
    构建报警响应对象
    
    Args:
        alert: 报警 ORM 对象
        camera: 摄像头对象
        person: 人员对象
        processor: 处理人对象
        
    Returns:
        AlertResponse: 报警响应模型
    """
    camera_info = None
    if camera:
        camera_info = CameraInfo(
            id=camera.id,
            name=camera.name,
            zone_id=camera.zone_id,
            zone_name=camera.zone.name if camera.zone else None,
        )
    
    person_info = None
    if person:
        person_info = PersonInfo(
            id=person.id,
            name=person.name,
            employee_id=person.employee_id,
            group_id=person.group_id,
            group_name=person.group.name if person.group else None,
            group_color=person.group.color if person.group else None,
        )
    
    processor_info = None
    if processor:
        processor_info = ProcessorInfo(
            id=processor.id,
            username=processor.username,
        )
    
    # 构建图片 URL
    # 修正逻辑：如果已经是 /static/ 开头的路径，直接使用；否则尝试构建
    face_image_url = None
    body_image_url = None
    full_image_url = None
    
    def get_url(path):
        if not path: return None
        if path.startswith("/static/"): return path
        # 兼容旧数据或绝对路径：尝试提取 uploads/captures 之后的部分
        if "captures" in path:
            # 假设 path 形如 .../captures/20230101/...
            try:
                rel = path.split("captures", 1)[1]
                # rel might start with path separator
                rel = rel.lstrip(os.sep).lstrip("/")
                return f"/static/captures/{rel.replace(os.sep, '/')}"
            except:
                pass
        return f"/static/captures/{os.path.basename(path)}"

    face_image_url = get_url(alert.face_image_path)
    body_image_url = get_url(alert.best_body_image_path)
    full_image_url = get_url(alert.full_image_path)
    
    return AlertResponse(
        id=alert.id,
        camera_id=alert.camera_id,
        camera=camera_info,
        alert_type=alert.alert_type.value if isinstance(alert.alert_type, AlertType) else alert.alert_type,
        person_id=alert.person_id,
        person=person_info,
        confidence=alert.confidence,
        face_image_path=alert.face_image_path,
        face_image_url=face_image_url,
        body_image_path=alert.best_body_image_path, # Need to add this to schema first? Yes.
        body_image_url=body_image_url,            # Need to add this to schema first? Yes.
        full_image_path=alert.full_image_path,
        full_image_url=full_image_url,
        face_bbox=alert.face_bbox,
        status=alert.status.value if isinstance(alert.status, AlertStatus) else alert.status,
        processed_by=alert.processed_by,
        processor=processor_info,
        processed_at=alert.processed_at,
        process_remark=alert.process_remark,
        extra_data=alert.extra_data,
        created_at=alert.created_at,
    )


@router.get("", response_model=AlertListResponse)
async def get_alerts(
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=100, description="每页数量"),
    start_date: Optional[datetime] = Query(None, description="开始时间"),
    end_date: Optional[datetime] = Query(None, description="结束时间"),
    camera_id: Optional[int] = Query(None, description="摄像头 ID"),
    zone_id: Optional[int] = Query(None, description="区域 ID"),
    alert_type: Optional[str] = Query(None, description="报警类型 (stranger/known/blacklist)"),
    person_id: Optional[int] = Query(None, description="人员 ID"),
    alert_status: Optional[str] = Query(None, description="报警状态 (pending/processed/ignored)"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """
    获取报警记录列表

    支持多维度筛选。

    Args:
        page: 页码
        page_size: 每页数量
        start_date: 开始时间
        end_date: 结束时间
        camera_id: 摄像头 ID
        zone_id: 区域 ID（筛选该区域下所有摄像头的报警）
        alert_type: 报警类型
        person_id: 人员 ID
        alert_status: 报警状态

    Returns:
        AlertListResponse: 报警列表和分页信息
    """
    # 构建查询
    query = select(AlertLog)
    count_query = select(func.count(AlertLog.id))

    # 时间范围筛选
    if start_date:
        query = query.where(AlertLog.created_at >= start_date)
        count_query = count_query.where(AlertLog.created_at >= start_date)
    if end_date:
        query = query.where(AlertLog.created_at <= end_date)
        count_query = count_query.where(AlertLog.created_at <= end_date)

    # 摄像头筛选
    if camera_id is not None:
        query = query.where(AlertLog.camera_id == camera_id)
        count_query = count_query.where(AlertLog.camera_id == camera_id)

    # 区域筛选（需要先查询该区域下的摄像头）
    if zone_id is not None:
        camera_ids_result = await db.execute(
            select(Camera.id).where(Camera.zone_id == zone_id)
        )
        camera_ids = [row[0] for row in camera_ids_result.fetchall()]
        if camera_ids:
            query = query.where(AlertLog.camera_id.in_(camera_ids))
            count_query = count_query.where(AlertLog.camera_id.in_(camera_ids))
        else:
            # 该区域没有摄像头，返回空结果
            return AlertListResponse(items=[], total=0, page=page, page_size=page_size, total_pages=0)

    # 报警类型筛选
    if alert_type:
        try:
            type_enum = AlertType(alert_type)
            query = query.where(AlertLog.alert_type == type_enum)
            count_query = count_query.where(AlertLog.alert_type == type_enum)
        except ValueError:
            pass

    # 人员筛选
    if person_id is not None:
        query = query.where(AlertLog.person_id == person_id)
        count_query = count_query.where(AlertLog.person_id == person_id)

    # 状态筛选
    if alert_status:
        try:
            status_enum = AlertStatus(alert_status)
            query = query.where(AlertLog.status == status_enum)
            count_query = count_query.where(AlertLog.status == status_enum)
        except ValueError:
            pass

    # 获取总数
    total_result = await db.execute(count_query)
    total = total_result.scalar()

    # 计算总页数
    total_pages = (total + page_size - 1) // page_size

    # 分页查询
    offset = (page - 1) * page_size
    query = query.order_by(AlertLog.created_at.desc()).offset(offset).limit(page_size)

    result = await db.execute(query)
    alerts = result.scalars().all()

    # 批量获取关联数据
    camera_ids = list(set(a.camera_id for a in alerts if a.camera_id))
    person_ids = list(set(a.person_id for a in alerts if a.person_id))
    processor_ids = list(set(a.processed_by for a in alerts if a.processed_by))

    # 获取摄像头
    cameras_map = {}
    if camera_ids:
        cameras_result = await db.execute(
            select(Camera).options(selectinload(Camera.zone)).where(Camera.id.in_(camera_ids))
        )
        for camera in cameras_result.scalars().all():
            cameras_map[camera.id] = camera

    # 获取人员
    persons_map = {}
    if person_ids:
        persons_result = await db.execute(
            select(KnownPerson).options(selectinload(KnownPerson.group)).where(KnownPerson.id.in_(person_ids))
        )
        for person in persons_result.scalars().all():
            persons_map[person.id] = person

    # 获取处理人
    processors_map = {}
    if processor_ids:
        processors_result = await db.execute(
            select(User).where(User.id.in_(processor_ids))
        )
        for processor in processors_result.scalars().all():
            processors_map[processor.id] = processor

    # 构建响应
    items = []
    for alert in alerts:
        camera = cameras_map.get(alert.camera_id)
        person = persons_map.get(alert.person_id) if alert.person_id else None
        processor = processors_map.get(alert.processed_by) if alert.processed_by else None
        items.append(build_alert_response(alert, camera, person, processor))

    return AlertListResponse(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
    )


@router.get("/statistics", response_model=AlertStatistics)
async def get_alert_statistics(
    start_date: Optional[datetime] = Query(None, description="开始时间"),
    end_date: Optional[datetime] = Query(None, description="结束时间"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """
    获取报警统计数据

    用于仪表盘展示。

    Args:
        start_date: 开始时间
        end_date: 结束时间

    Returns:
        AlertStatistics: 报警统计数据
    """
    now = datetime.now(timezone.utc)
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    week_start = today_start - timedelta(days=today_start.weekday())
    month_start = today_start.replace(day=1)

    # 基础查询条件
    base_filter = []
    if start_date:
        base_filter.append(AlertLog.created_at >= start_date)
    if end_date:
        base_filter.append(AlertLog.created_at <= end_date)

    # 总数统计
    total_result = await db.execute(
        select(func.count(AlertLog.id)).where(*base_filter) if base_filter else select(func.count(AlertLog.id))
    )
    total = total_result.scalar() or 0

    # 按状态统计
    status_query = select(AlertLog.status, func.count(AlertLog.id)).group_by(AlertLog.status)
    if base_filter:
        status_query = status_query.where(*base_filter)
    status_result = await db.execute(status_query)
    status_counts = {row[0].value if hasattr(row[0], 'value') else row[0]: row[1] for row in status_result.fetchall()}

    # 按类型统计
    type_query = select(AlertLog.alert_type, func.count(AlertLog.id)).group_by(AlertLog.alert_type)
    if base_filter:
        type_query = type_query.where(*base_filter)
    type_result = await db.execute(type_query)
    type_counts = {row[0].value if hasattr(row[0], 'value') else row[0]: row[1] for row in type_result.fetchall()}

    # 按摄像头统计（前 10）
    camera_query = (
        select(AlertLog.camera_id, func.count(AlertLog.id).label('count'))
        .group_by(AlertLog.camera_id)
        .order_by(func.count(AlertLog.id).desc())
        .limit(10)
    )
    if base_filter:
        camera_query = camera_query.where(*base_filter)
    camera_result = await db.execute(camera_query)
    camera_counts = camera_result.fetchall()

    # 获取摄像头名称
    camera_ids = [row[0] for row in camera_counts]
    cameras_map = {}
    if camera_ids:
        cameras_result = await db.execute(
            select(Camera).where(Camera.id.in_(camera_ids))
        )
        cameras_map = {c.id: c.name for c in cameras_result.scalars().all()}

    by_camera = [
        {"camera_id": row[0], "camera_name": cameras_map.get(row[0], "Unknown"), "count": row[1]}
        for row in camera_counts
    ]

    # 今日统计
    today_result = await db.execute(
        select(func.count(AlertLog.id)).where(AlertLog.created_at >= today_start)
    )
    today_count = today_result.scalar() or 0

    # 本周统计
    week_result = await db.execute(
        select(func.count(AlertLog.id)).where(AlertLog.created_at >= week_start)
    )
    week_count = week_result.scalar() or 0

    # 本月统计
    month_result = await db.execute(
        select(func.count(AlertLog.id)).where(AlertLog.created_at >= month_start)
    )
    month_count = month_result.scalar() or 0

    return AlertStatistics(
        total=total,
        pending=status_counts.get('pending', 0),
        processed=status_counts.get('processed', 0),
        ignored=status_counts.get('ignored', 0),
        by_type=type_counts,
        by_camera=by_camera,
        today_count=today_count,
        week_count=week_count,
        month_count=month_count,
    )


@router.get("/trend", response_model=AlertTrendResponse)
async def get_alert_trend(
    period: str = Query("week", description="时间周期 (day/week/month)"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """
    获取报警趋势数据

    用于图表展示。

    Args:
        period: 时间周期（day: 24小时, week: 7天, month: 30天）

    Returns:
        AlertTrendResponse: 报警趋势数据
    """
    now = datetime.now(timezone.utc)
    
    if period == "day":
        # 过去 24 小时，按小时统计
        start_time = now - timedelta(hours=24)
        # 使用原生 SQL 函数进行时间截断
        # PostgreSQL: date_trunc('hour', created_at)
    elif period == "month":
        # 过去 30 天，按天统计
        start_time = now - timedelta(days=30)
    else:  # week
        # 过去 7 天，按天统计
        start_time = now - timedelta(days=7)

    # 查询报警数据
    result = await db.execute(
        select(AlertLog).where(AlertLog.created_at >= start_time).order_by(AlertLog.created_at)
    )
    alerts = result.scalars().all()

    # 按日期聚合
    date_counts = {}
    for alert in alerts:
        if period == "day":
            date_key = alert.created_at.strftime("%Y-%m-%d %H:00")
        else:
            date_key = alert.created_at.strftime("%Y-%m-%d")
        
        if date_key not in date_counts:
            date_counts[date_key] = {"count": 0, "stranger": 0, "known": 0, "blacklist": 0}
        
        date_counts[date_key]["count"] += 1
        alert_type = alert.alert_type.value if hasattr(alert.alert_type, 'value') else alert.alert_type
        if alert_type in date_counts[date_key]:
            date_counts[date_key][alert_type] += 1

    # 构建趋势数据
    items = [
        AlertTrendItem(
            date=date,
            count=data["count"],
            stranger_count=data["stranger"],
            known_count=data["known"],
            blacklist_count=data["blacklist"],
        )
        for date, data in sorted(date_counts.items())
    ]

    return AlertTrendResponse(items=items, period=period)


@router.get("/{alert_id}", response_model=AlertResponse)
async def get_alert(
    alert_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """
    获取报警详情

    Args:
        alert_id: 报警 ID

    Returns:
        AlertResponse: 报警详细信息

    Raises:
        HTTPException 404: 报警不存在
    """
    result = await db.execute(select(AlertLog).where(AlertLog.id == alert_id))
    alert = result.scalar_one_or_none()

    if not alert:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Alert not found",
        )

    # 获取关联数据
    camera = None
    if alert.camera_id:
        camera_result = await db.execute(
            select(Camera).options(selectinload(Camera.zone)).where(Camera.id == alert.camera_id)
        )
        camera = camera_result.scalar_one_or_none()

    person = None
    if alert.person_id:
        person_result = await db.execute(
            select(KnownPerson).options(selectinload(KnownPerson.group)).where(KnownPerson.id == alert.person_id)
        )
        person = person_result.scalar_one_or_none()

    processor = None
    if alert.processed_by:
        processor_result = await db.execute(
            select(User).where(User.id == alert.processed_by)
        )
        processor = processor_result.scalar_one_or_none()

    return build_alert_response(alert, camera, person, processor)


@router.patch("/{alert_id}/process", response_model=AlertResponse)
async def process_alert(
    alert_id: int,
    request: AlertProcessRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """
    处理报警

    将报警状态设置为"已处理"。

    Args:
        alert_id: 报警 ID
        request: 处理请求

    Returns:
        AlertResponse: 更新后的报警信息

    Raises:
        HTTPException 404: 报警不存在
        HTTPException 400: 报警已处理
    """
    result = await db.execute(select(AlertLog).where(AlertLog.id == alert_id))
    alert = result.scalar_one_or_none()

    if not alert:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Alert not found",
        )

    if alert.status != AlertStatus.PENDING:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Alert already {alert.status.value}",
        )

    alert.status = AlertStatus.PROCESSED
    alert.processed_by = current_user.id
    alert.processed_at = datetime.now(timezone.utc)
    alert.process_remark = request.remark

    await db.commit()
    await db.refresh(alert)

    # 获取关联数据并返回
    # 获取关联数据并返回
    return await get_alert(alert_id, db, current_user)


@router.post("/{alert_id}/feedback", response_model=AlertResponse)
async def submit_alert_feedback(
    alert_id: int,
    request: AlertFeedbackRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """
    提交人工反馈 (将陌生人注册为已知人员)
    
    1. 在 CompreFace 中注册人脸
    2. 创建 KnownPerson 记录
    3. 更新 AlertLog 为已处理/已知
    """
    # 1. 获取报警
    result = await db.execute(select(AlertLog).where(AlertLog.id == alert_id))
    alert = result.scalar_one_or_none()
    
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")
        
    if not alert.face_image_path:
        raise HTTPException(status_code=400, detail="No face image available for registration")
        
    # 2. 读取图片文件
    # 路径通常是 relative to backend root or absolute? 
    # stored as "data/..." in DB? or "/static/..."
    # Config says CAPTURES_DIR is absolute. 
    # AlertLog path might be relative or absolute. Manager saves as full path or relative?
    # Manager: return f"/static/{rel_path}" which is web path. 
    # We need to map it back to file system path.
    
    # 假设路径以 /static/ 开头，映射到 DATA_DIR
    file_path = None
    if alert.face_image_path.startswith("/static/"):
         from app.core.config import settings
         rel_path = alert.face_image_path.replace("/static/", "").replace("/", os.sep)
         file_path = os.path.join(settings.DATA_DIR, rel_path)
    else:
         file_path = alert.face_image_path # assume absolute if no prefix
         
    if not os.path.exists(file_path):
         raise HTTPException(status_code=400, detail=f"Image file missing: {file_path}")
         
    with open(file_path, "rb") as f:
        image_data = f.read()
        
    # 3. 注册到 CompreFace
    success = await compreface_client.add_subject(image_data, request.person_name)
    if not success:
         raise HTTPException(status_code=500, detail="Failed to register face in engine")
         
    # 4. 创建/更新 KnownPerson
    # 简单起见，总是创建新的一条，或者根据 name 查重
    # (省略查重逻辑，直接创建)
    new_person = KnownPerson(
        name=request.person_name,
        group_id=request.group_id,
        remark="From alert feedback"
    )
    db.add(new_person)
    await db.flush() # get ID
    
    # 5. 更新 Alert
    alert.alert_type = AlertType.KNOWN
    alert.alert_level = AlertLevel.INFO
    alert.person_id = new_person.id
    alert.status = AlertStatus.PROCESSED
    alert.processed_by = current_user.id
    alert.processed_at = datetime.now(timezone.utc)
    alert.process_remark = "Manual Feedback: Registered as " + request.person_name
    alert.is_reviewed = True
    
    await db.commit()
    await db.refresh(alert)
    
    return await get_alert(alert_id, db, current_user)


@router.patch("/{alert_id}/ignore", response_model=AlertResponse)
async def ignore_alert(
    alert_id: int,
    request: AlertIgnoreRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """
    忽略报警

    将报警状态设置为"已忽略"。

    Args:
        alert_id: 报警 ID
        request: 忽略请求

    Returns:
        AlertResponse: 更新后的报警信息

    Raises:
        HTTPException 404: 报警不存在
        HTTPException 400: 报警已处理
    """
    result = await db.execute(select(AlertLog).where(AlertLog.id == alert_id))
    alert = result.scalar_one_or_none()

    if not alert:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Alert not found",
        )

    if alert.status != AlertStatus.PENDING:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Alert already {alert.status.value}",
        )

    alert.status = AlertStatus.IGNORED
    alert.processed_by = current_user.id
    alert.processed_at = datetime.now(timezone.utc)
    alert.process_remark = request.remark

    await db.commit()
    await db.refresh(alert)

    return await get_alert(alert_id, db, current_user)


@router.post("/batch-process", response_model=AlertBatchProcessResult)
async def batch_process_alerts(
    request: AlertBatchProcessRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """
    批量处理报警

    批量将报警设置为"已处理"或"已忽略"。

    Args:
        request: 批量处理请求

    Returns:
        AlertBatchProcessResult: 处理结果
    """
    if request.action not in ["process", "ignore"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Action must be 'process' or 'ignore'",
        )

    new_status = AlertStatus.PROCESSED if request.action == "process" else AlertStatus.IGNORED
    now = datetime.now(timezone.utc)

    success_count = 0
    failed_ids = []

    for alert_id in request.alert_ids:
        result = await db.execute(select(AlertLog).where(AlertLog.id == alert_id))
        alert = result.scalar_one_or_none()

        if not alert:
            failed_ids.append(alert_id)
            continue

        if alert.status != AlertStatus.PENDING:
            failed_ids.append(alert_id)
            continue

        alert.status = new_status
        alert.processed_by = current_user.id
        alert.processed_at = now
        alert.process_remark = request.remark
        success_count += 1

    await db.commit()

    return AlertBatchProcessResult(
        success_count=success_count,
        failed_count=len(failed_ids),
        failed_ids=failed_ids,
    )


@router.post("", response_model=AlertResponse, status_code=status.HTTP_201_CREATED)
async def create_alert(
    alert_data: AlertCreateRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """
    创建报警记录（内部接口）

    由视频分析引擎调用，用于创建新的报警记录。

    Args:
        alert_data: 报警数据

    Returns:
        AlertResponse: 创建的报警信息
    """
    # 验证摄像头存在
    camera_result = await db.execute(
        select(Camera).where(Camera.id == alert_data.camera_id)
    )
    if not camera_result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Camera not found",
        )

    # 验证人员存在（如果提供）
    if alert_data.person_id:
        person_result = await db.execute(
            select(KnownPerson).where(KnownPerson.id == alert_data.person_id)
        )
        if not person_result.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Person not found",
            )

    # 创建报警记录
    new_alert = AlertLog(
        camera_id=alert_data.camera_id,
        alert_type=AlertType(alert_data.alert_type.value),
        person_id=alert_data.person_id,
        confidence=alert_data.confidence,
        face_image_path=alert_data.face_image_path,
        full_image_path=alert_data.full_image_path,
        face_bbox=alert_data.face_bbox.model_dump() if alert_data.face_bbox else None,
        status=AlertStatus.PENDING,
        extra_data=alert_data.extra_data,
    )

    db.add(new_alert)
    await db.commit()
    await db.refresh(new_alert)

    return await get_alert(new_alert.id, db, current_user)


@router.get("/export/csv")
async def export_alerts_csv(
    start_date: Optional[datetime] = Query(None, description="开始时间"),
    end_date: Optional[datetime] = Query(None, description="结束时间"),
    camera_id: Optional[int] = Query(None, description="摄像头 ID"),
    alert_type: Optional[str] = Query(None, description="报警类型"),
    alert_status: Optional[str] = Query(None, description="报警状态"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    """
    导出报警记录为 CSV

    仅管理员可导出。

    Args:
        start_date: 开始时间
        end_date: 结束时间
        camera_id: 摄像头 ID
        alert_type: 报警类型
        alert_status: 报警状态

    Returns:
        CSV 文件流
    """
    # 构建查询
    query = select(AlertLog)

    if start_date:
        query = query.where(AlertLog.created_at >= start_date)
    if end_date:
        query = query.where(AlertLog.created_at <= end_date)
    if camera_id:
        query = query.where(AlertLog.camera_id == camera_id)
    if alert_type:
        try:
            query = query.where(AlertLog.alert_type == AlertType(alert_type))
        except ValueError:
            pass
    if alert_status:
        try:
            query = query.where(AlertLog.status == AlertStatus(alert_status))
        except ValueError:
            pass

    query = query.order_by(AlertLog.created_at.desc()).limit(10000)  # 限制导出数量

    result = await db.execute(query)
    alerts = result.scalars().all()

    # 获取摄像头名称
    camera_ids = list(set(a.camera_id for a in alerts if a.camera_id))
    cameras_map = {}
    if camera_ids:
        cameras_result = await db.execute(
            select(Camera).where(Camera.id.in_(camera_ids))
        )
        cameras_map = {c.id: c.name for c in cameras_result.scalars().all()}

    # 获取人员名称
    person_ids = list(set(a.person_id for a in alerts if a.person_id))
    persons_map = {}
    if person_ids:
        persons_result = await db.execute(
            select(KnownPerson).where(KnownPerson.id.in_(person_ids))
        )
        persons_map = {p.id: p.name for p in persons_result.scalars().all()}

    # 生成 CSV
    output = io.StringIO()
    writer = csv.writer(output)
    
    # 写入表头
    writer.writerow([
        "ID", "Time", "Camera", "Alert Type", "Person", 
        "Confidence", "Status", "Processed At", "Remark"
    ])
    
    # 写入数据
    for alert in alerts:
        writer.writerow([
            alert.id,
            alert.created_at.strftime("%Y-%m-%d %H:%M:%S") if alert.created_at else "",
            cameras_map.get(alert.camera_id, ""),
            alert.alert_type.value if hasattr(alert.alert_type, 'value') else alert.alert_type,
            persons_map.get(alert.person_id, "") if alert.person_id else "",
            f"{alert.confidence:.2f}" if alert.confidence else "",
            alert.status.value if hasattr(alert.status, 'value') else alert.status,
            alert.processed_at.strftime("%Y-%m-%d %H:%M:%S") if alert.processed_at else "",
            alert.process_remark or "",
        ])

    output.seek(0)
    
    filename = f"alerts_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
    
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )
