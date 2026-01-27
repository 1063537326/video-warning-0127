"""
系统配置接口模块

提供系统配置的查询、更新、数据清理、系统状态等功能。

功能列表：
- GET /settings - 获取系统配置
- PUT /settings - 更新系统配置
- POST /settings/cleanup - 手动触发数据清理
- GET /settings/cleanup-logs - 获取清理日志
- GET /settings/status - 获取系统状态
"""
import os
import shutil
import platform
import psutil
import time
from typing import Optional
from datetime import datetime, timezone, timedelta
from fastapi import APIRouter, Depends, HTTPException, status, Query, BackgroundTasks
from sqlalchemy import select, func, delete, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db, get_current_active_user, require_admin
from app.models.system import SystemConfig, OperationLog, CleanupLog
from app.models.alert import AlertLog
from app.models.user import User
from app.models.camera import Camera, CameraZone
from app.models.person import KnownPerson, PersonGroup, FaceImage
from app.core.config import settings
from app.schemas.settings import (
    ConfigItemResponse,
    ConfigGroupResponse,
    SystemConfigResponse,
    ConfigUpdateRequest,
    ConfigUpdateResult,
    CleanupRequest,
    CleanupResult,
    CleanupLogResponse,
    CleanupLogListResponse,
    DiskUsage,
    ServiceStatus,
    DatabaseStatus,
    SystemStatusResponse,
)

router = APIRouter(prefix="/settings", tags=["系统配置"])

# 应用启动时间
APP_START_TIME = time.time()

# 配置项分组定义
CONFIG_GROUPS = {
    "face_recognition": {
        "label": "人脸识别配置",
        "keys": [
            "face_similarity_threshold",
            "face_detection_min_size",
            "face_detection_confidence",
            "concurrent_limit",
        ]
    },
    "alert": {
        "label": "报警配置",
        "keys": [
            "alert_cooldown_seconds",
            "alert_sound_enabled",
            "alert_push_enabled",
        ]
    },
    "storage": {
        "label": "存储配置",
        "keys": [
            "data_retention_days",
            "capture_quality",
            "max_face_images_per_person",
        ]
    },
    "system": {
        "label": "系统配置",
        "keys": [
            # "system_name",  # 系统名称，已隐藏
            "enable_operation_log",
            "auto_cleanup_enabled",
            "auto_cleanup_hour",
        ]
    },
}


def format_bytes(size_bytes: int) -> str:
    """
    格式化字节数为可读字符串
    
    Args:
        size_bytes: 字节数
        
    Returns:
        格式化后的字符串（如 "1.5 GB"）
    """
    if size_bytes == 0:
        return "0 B"
    
    units = ["B", "KB", "MB", "GB", "TB"]
    unit_index = 0
    size = float(size_bytes)
    
    while size >= 1024 and unit_index < len(units) - 1:
        size /= 1024
        unit_index += 1
    
    return f"{size:.2f} {units[unit_index]}"


def format_duration(seconds: float) -> str:
    """
    格式化时间长度为可读字符串
    
    Args:
        seconds: 秒数
        
    Returns:
        格式化后的字符串（如 "2d 3h 15m"）
    """
    if seconds < 60:
        return f"{int(seconds)}s"
    
    minutes = int(seconds // 60)
    if minutes < 60:
        return f"{minutes}m {int(seconds % 60)}s"
    
    hours = minutes // 60
    if hours < 24:
        return f"{hours}h {minutes % 60}m"
    
    days = hours // 24
    return f"{days}d {hours % 24}h {minutes % 60}m"


@router.get("", response_model=SystemConfigResponse, summary="获取系统配置",
            dependencies=[Depends(require_admin)])
async def get_system_config(db: AsyncSession = Depends(get_db)):
    """
    获取系统配置

    按分组返回所有系统配置项。

    Returns:
        SystemConfigResponse: 按分组组织的配置列表
    """
    # 获取所有配置项
    result = await db.execute(select(SystemConfig))
    configs = result.scalars().all()
    
    # 转换为字典便于查找
    config_dict = {c.config_key: c for c in configs}
    
    # 按分组组织
    groups = []
    for group_name, group_info in CONFIG_GROUPS.items():
        items = []
        for key in group_info["keys"]:
            if key in config_dict:
                config = config_dict[key]
                items.append(ConfigItemResponse(
                    id=config.id,
                    config_key=config.config_key,
                    config_value=config.config_value,
                    value_type=config.value_type,
                    description=config.description,
                    updated_at=config.updated_at,
                    updated_by=config.updated_by,
                ))
        
        if items:
            groups.append(ConfigGroupResponse(
                group_name=group_name,
                group_label=group_info["label"],
                items=items,
            ))
    
    return SystemConfigResponse(groups=groups)


@router.put("", response_model=ConfigUpdateResult, summary="更新系统配置",
            dependencies=[Depends(require_admin)])
async def update_system_config(
    request: ConfigUpdateRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """
    更新系统配置

    批量更新配置项。

    Args:
        request: 配置更新请求

    Returns:
        ConfigUpdateResult: 更新结果
    """
    failed_keys = []
    
    # 标记是否需要重载引擎配置
    need_reload = False
    engine_related_groups = ["face_recognition", "alert", "storage"] # 简化判断，只要有改动就重载
    
    for item in request.items:
        result = await db.execute(
            select(SystemConfig).where(SystemConfig.config_key == item.config_key)
        )
        config = result.scalar_one_or_none()
        
        if not config:
            failed_keys.append(item.config_key)
            continue
        
        # 更新配置
        config.config_value = item.config_value
        config.updated_by = current_user.id
        success_count += 1
        need_reload = True
    
    await db.commit()
    
    # 重载引擎配置
    if need_reload:
        try:
            from main import get_engine
            engine = get_engine()
            if engine:
                # 逐个通知引擎更新配置
                for item in request.items:
                    engine.update_config(item.config_key, item.config_value)
        except Exception as e:
             print(f"Failed to reload engine config: {e}")

    return ConfigUpdateResult(
        success_count=success_count,
        failed_count=len(failed_keys),
        failed_keys=failed_keys,
    )


@router.get("/item/{config_key}", response_model=ConfigItemResponse, summary="获取单个配置项",
            dependencies=[Depends(require_admin)])
async def get_config_item(config_key: str, db: AsyncSession = Depends(get_db)):
    """
    获取单个配置项

    Args:
        config_key: 配置键名

    Returns:
        ConfigItemResponse: 配置项详情

    Raises:
        HTTPException 404: 配置项不存在
    """
    result = await db.execute(
        select(SystemConfig).where(SystemConfig.config_key == config_key)
    )
    config = result.scalar_one_or_none()
    
    if not config:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Config item not found",
        )
    
    return ConfigItemResponse(
        id=config.id,
        config_key=config.config_key,
        config_value=config.config_value,
        value_type=config.value_type,
        description=config.description,
        updated_at=config.updated_at,
        updated_by=config.updated_by,
    )


async def perform_cleanup(
    db: AsyncSession,
    cleanup_type: str,
    days_to_keep: int,
    dry_run: bool,
) -> CleanupResult:
    """
    执行数据清理
    
    Args:
        db: 数据库会话
        cleanup_type: 清理类型
        days_to_keep: 保留天数
        dry_run: 是否模拟运行
        
    Returns:
        CleanupResult: 清理结果
    """
    started_at = datetime.now(timezone.utc)
    cutoff_date = started_at - timedelta(days=days_to_keep)
    
    records_deleted = 0
    files_deleted = 0
    bytes_freed = 0
    error_message = None
    status_str = "success"
    
    try:
        # 清理报警记录
        if cleanup_type in ["alert", "all"]:
            # 查询要删除的记录
            result = await db.execute(
                select(AlertLog).where(AlertLog.created_at < cutoff_date)
            )
            alerts_to_delete = result.scalars().all()
            
            # 收集要删除的图片路径
            image_paths = []
            for alert in alerts_to_delete:
                if alert.face_image_path:
                    image_paths.append(alert.face_image_path)
                if alert.full_image_path:
                    image_paths.append(alert.full_image_path)
            
            if not dry_run:
                # 删除记录
                await db.execute(
                    delete(AlertLog).where(AlertLog.created_at < cutoff_date)
                )
                records_deleted += len(alerts_to_delete)
                
                # 删除图片文件
                for path in image_paths:
                    try:
                        if os.path.exists(path):
                            file_size = os.path.getsize(path)
                            os.remove(path)
                            files_deleted += 1
                            bytes_freed += file_size
                    except Exception:
                        pass
            else:
                records_deleted += len(alerts_to_delete)
                for path in image_paths:
                    if os.path.exists(path):
                        bytes_freed += os.path.getsize(path)
                        files_deleted += 1
        
        # 清理截图文件（不在数据库中的孤立文件）
        if cleanup_type in ["capture", "all"]:
            captures_dir = settings.CAPTURES_DIR
            if os.path.exists(captures_dir):
                for filename in os.listdir(captures_dir):
                    file_path = os.path.join(captures_dir, filename)
                    if os.path.isfile(file_path):
                        file_mtime = datetime.fromtimestamp(
                            os.path.getmtime(file_path), tz=timezone.utc
                        )
                        if file_mtime < cutoff_date:
                            if not dry_run:
                                try:
                                    file_size = os.path.getsize(file_path)
                                    os.remove(file_path)
                                    files_deleted += 1
                                    bytes_freed += file_size
                                except Exception:
                                    pass
                            else:
                                bytes_freed += os.path.getsize(file_path)
                                files_deleted += 1
        
        if not dry_run:
            await db.commit()
            
    except Exception as e:
        status_str = "failed"
        error_message = str(e)
        if not dry_run:
            await db.rollback()
    
    finished_at = datetime.now(timezone.utc)
    duration = (finished_at - started_at).total_seconds()
    
    # 记录清理日志（非模拟运行时）
    if not dry_run:
        cleanup_log = CleanupLog(
            cleanup_type=cleanup_type,
            records_deleted=records_deleted,
            files_deleted=files_deleted,
            bytes_freed=bytes_freed,
            started_at=started_at,
            finished_at=finished_at,
            status=status_str,
            error_message=error_message,
        )
        db.add(cleanup_log)
        await db.commit()
    
    return CleanupResult(
        cleanup_type=cleanup_type,
        dry_run=dry_run,
        records_deleted=records_deleted,
        files_deleted=files_deleted,
        bytes_freed=bytes_freed,
        bytes_freed_formatted=format_bytes(bytes_freed),
        started_at=started_at,
        finished_at=finished_at,
        duration_seconds=duration,
        status=status_str,
        error_message=error_message,
    )


@router.post("/cleanup", response_model=CleanupResult, summary="手动触发数据清理",
             dependencies=[Depends(require_admin)])
async def trigger_cleanup(
    request: CleanupRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    手动触发数据清理

    清理过期的报警记录和截图文件。

    Args:
        request: 清理请求

    Returns:
        CleanupResult: 清理结果
    """
    return await perform_cleanup(
        db=db,
        cleanup_type=request.cleanup_type.value,
        days_to_keep=request.days_to_keep,
        dry_run=request.dry_run,
    )


@router.get("/cleanup-logs", response_model=CleanupLogListResponse, summary="获取清理日志",
            dependencies=[Depends(require_admin)])
async def get_cleanup_logs(
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=100, description="每页数量"),
    db: AsyncSession = Depends(get_db),
):
    """
    获取数据清理日志

    Args:
        page: 页码
        page_size: 每页数量

    Returns:
        CleanupLogListResponse: 清理日志列表
    """
    # 获取总数
    count_result = await db.execute(select(func.count(CleanupLog.id)))
    total = count_result.scalar() or 0
    
    # 计算总页数
    total_pages = (total + page_size - 1) // page_size
    
    # 分页查询
    offset = (page - 1) * page_size
    result = await db.execute(
        select(CleanupLog)
        .order_by(CleanupLog.started_at.desc())
        .offset(offset)
        .limit(page_size)
    )
    logs = result.scalars().all()
    
    items = [
        CleanupLogResponse(
            id=log.id,
            cleanup_type=log.cleanup_type,
            records_deleted=log.records_deleted,
            files_deleted=log.files_deleted,
            bytes_freed=log.bytes_freed,
            bytes_freed_formatted=format_bytes(log.bytes_freed),
            started_at=log.started_at,
            finished_at=log.finished_at,
            status=log.status,
            error_message=log.error_message,
        )
        for log in logs
    ]
    
    return CleanupLogListResponse(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
    )


@router.get("/status", response_model=SystemStatusResponse, summary="获取系统状态",
            dependencies=[Depends(require_admin)])
async def get_system_status(db: AsyncSession = Depends(get_db)):
    """
    获取系统状态

    返回系统运行状态、磁盘空间、数据库状态等信息。

    Returns:
        SystemStatusResponse: 系统状态信息
    """
    now = datetime.now(timezone.utc)
    uptime = time.time() - APP_START_TIME
    
    # 磁盘使用情况
    disk_usages = []
    
    # 数据目录 - 检查配置的数据目录
    data_dir = getattr(settings, 'DATA_DIR', './data')
    
    # 如果数据目录不存在，使用当前工作目录
    if not os.path.exists(data_dir):
        data_dir = os.getcwd()
    
    try:
        disk = shutil.disk_usage(data_dir)
        disk_usages.append(DiskUsage(
            path=data_dir,
            total_bytes=disk.total,
            used_bytes=disk.used,
            free_bytes=disk.free,
            usage_percent=round((disk.used / disk.total) * 100, 2),
            total_formatted=format_bytes(disk.total),
            used_formatted=format_bytes(disk.used),
            free_formatted=format_bytes(disk.free),
        ))
    except Exception as e:
        print(f"[WARNING] Failed to get disk usage for {data_dir}: {e}")
    
    # 数据库状态
    db_connected = True
    db_version = None
    tables_count = 0
    total_records = {}
    
    try:
        # 获取 PostgreSQL 版本
        version_result = await db.execute(text("SELECT version()"))
        db_version = version_result.scalar()
        
        # 统计各表记录数
        models_to_count = [
            (User, "users"),
            (Camera, "cameras"),
            (CameraZone, "zones"),
            (KnownPerson, "persons"),
            (PersonGroup, "groups"),
            (AlertLog, "alerts"),
            (SystemConfig, "configs"),
            (OperationLog, "operation_logs"),
            (CleanupLog, "cleanup_logs"),
        ]
        
        for model, name in models_to_count:
            try:
                count_result = await db.execute(select(func.count()).select_from(model))
                total_records[name] = count_result.scalar() or 0
                tables_count += 1
            except Exception:
                total_records[name] = -1  # 表示无法获取
            
    except Exception as e:
        db_connected = False
        print(f"[ERROR] Database status check failed: {e}")
    
    database_status = DatabaseStatus(
        connected=db_connected,
        version=db_version,
        tables_count=tables_count,
        total_records=total_records,
    )
    
    # 服务状态
    services = [
        ServiceStatus(
            name="FastAPI Server",
            status="running",
            uptime_seconds=uptime,
            uptime_formatted=format_duration(uptime),
        ),
        ServiceStatus(
            name="Database (PostgreSQL)",
            status="running" if db_connected else "error",
        ),
    ]
    
    # 系统信息
    system_info = {
        "platform": platform.system(),
        "platform_version": platform.version(),
        "python_version": platform.python_version(),
        "processor": platform.processor(),
        "cpu_count": psutil.cpu_count(),
        "cpu_percent": psutil.cpu_percent(interval=0.1),
        "memory_total": format_bytes(psutil.virtual_memory().total),
        "memory_used": format_bytes(psutil.virtual_memory().used),
        "memory_percent": psutil.virtual_memory().percent,
    }
    
    # 环境判断
    environment = "development" if settings.DEBUG else "production"
    
    return SystemStatusResponse(
        app_name=settings.APP_NAME,
        app_version=settings.APP_VERSION,
        environment=environment,
        uptime_seconds=uptime,
        uptime_formatted=format_duration(uptime),
        current_time=now,
        disk_usage=disk_usages,
        database=database_status,
        services=services,
        system_info=system_info,
    )


@router.post("/init-configs", summary="初始化或补充系统配置",
             dependencies=[Depends(require_admin)])
async def init_system_configs(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
    force: bool = Query(False, description="强制补充缺失的配置项"),
):
    """
    初始化或补充系统配置

    创建默认配置项。如果 force=True，会补充所有缺失的配置项。

    Args:
        force: 是否强制补充缺失的配置项

    Returns:
        dict: 初始化结果
    """
    # 默认配置
    default_configs = [
        # 人脸识别配置
        ("face_similarity_threshold", "0.6", "number", "人脸相似度阈值 (0.0-1.0)"),
        ("face_detection_min_size", "30", "number", "人脸检测最小尺寸 (像素)"),
        ("face_detection_confidence", "0.9", "number", "人脸检测置信度阈值"),
        ("concurrent_limit", "5", "number", "人脸识别并发限制"),
        # 报警配置
        ("alert_cooldown_seconds", "60", "number", "同一人员报警冷却时间 (秒)"),
        ("alert_sound_enabled", "true", "boolean", "是否启用报警声音"),
        ("alert_push_enabled", "true", "boolean", "是否启用报警推送"),
        # 存储配置
        ("data_retention_days", "30", "number", "数据保留天数"),
        ("capture_quality", "85", "number", "截图质量 (1-100)"),
        ("max_face_images_per_person", "5", "number", "每人最大人脸图片数"),
        # 系统配置
        ("system_name", "Video Warning System", "string", "系统名称"),
        ("enable_operation_log", "true", "boolean", "是否记录操作日志"),
        ("auto_cleanup_enabled", "true", "boolean", "是否启用自动清理"),
        ("auto_cleanup_hour", "3", "number", "自动清理执行时间 (小时, 0-23)"),
    ]
    
    # 获取现有配置键
    result = await db.execute(select(SystemConfig.config_key))
    existing_keys = set(r[0] for r in result.fetchall())
    
    # 如果不是强制模式且已有配置，只返回统计
    if not force and existing_keys:
        missing_count = len([k for k, _, _, _ in default_configs if k not in existing_keys])
        if missing_count == 0:
            return {
                "message": "All configs already initialized",
                "existing_count": len(existing_keys),
                "missing_count": 0,
            }
        return {
            "message": f"Found {missing_count} missing configs. Use force=true to add them.",
            "existing_count": len(existing_keys),
            "missing_count": missing_count,
        }
    
    # 添加缺失的配置
    added_count = 0
    for key, value, value_type, description in default_configs:
        if key not in existing_keys:
            config = SystemConfig(
                config_key=key,
                config_value=value,
                value_type=value_type,
                description=description,
                updated_by=current_user.id,
            )
            db.add(config)
            added_count += 1
    
    if added_count > 0:
        await db.commit()
    
    return {
        "message": f"Configs initialized successfully. Added {added_count} new configs.",
        "existing_count": len(existing_keys),
        "added_count": added_count,
        "total_count": len(existing_keys) + added_count,
    }
