"""
摄像头管理接口模块

提供摄像头的增删改查功能，包括连通性测试和状态管理。

功能列表：
- GET /cameras - 获取摄像头列表（支持分页和筛选）
- GET /cameras/all - 获取所有摄像头（用于下拉选择）
- GET /cameras/status - 获取所有摄像头实时状态
- POST /cameras - 新增摄像头
- GET /cameras/{camera_id} - 获取摄像头详情
- PUT /cameras/{camera_id} - 更新摄像头配置
- DELETE /cameras/{camera_id} - 删除摄像头
- POST /cameras/{camera_id}/test - 测试摄像头连通性
- PATCH /cameras/{camera_id}/toggle - 启用/停用摄像头分析
"""
import time
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query, BackgroundTasks
from sqlalchemy import select, func, or_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.deps import get_db, get_current_active_user, require_admin
from app.models.camera import Camera, CameraZone, CameraStatus
from app.models.user import User
from app.schemas.camera import (
    CameraCreate,
    CameraUpdate,
    CameraToggleRequest,
    CameraResponse,
    CameraSimpleResponse,
    CameraListResponse,
    CameraStatusResponse,
    CameraStatusListResponse,
    CameraTestResult,
    ZoneInfo,
)

router = APIRouter(prefix="/cameras", tags=["摄像头管理"])


def build_camera_response(camera: Camera) -> CameraResponse:
    """
    构建摄像头响应对象
    
    Args:
        camera: 摄像头 ORM 对象
        
    Returns:
        CameraResponse: 摄像头响应模型
    """
    zone_info = None
    if camera.zone:
        zone_info = ZoneInfo(
            id=camera.zone.id,
            name=camera.zone.name,
            building=camera.zone.building,
            floor=camera.zone.floor,
        )
    
    return CameraResponse(
        id=camera.id,
        name=camera.name,
        zone_id=camera.zone_id,
        zone=zone_info,
        rtsp_url=camera.rtsp_url,
        username=camera.username,
        resolution=camera.resolution,
        fps=camera.fps,
        status=camera.status.value if isinstance(camera.status, CameraStatus) else camera.status,
        is_enabled=camera.is_enabled,
        last_heartbeat_at=camera.last_heartbeat_at,
        config=camera.config,
        created_at=camera.created_at,
        updated_at=camera.updated_at,
    )


@router.get("", response_model=CameraListResponse)
async def get_cameras(
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(10, ge=1, le=100, description="每页数量"),
    keyword: Optional[str] = Query(None, description="搜索关键词（名称/RTSP地址）"),
    zone_id: Optional[int] = Query(None, description="区域 ID 筛选"),
    status: Optional[str] = Query(None, description="状态筛选 (online/offline/error)"),
    is_enabled: Optional[bool] = Query(None, description="启用状态筛选"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """
    获取摄像头列表

    支持分页和多条件筛选。

    Args:
        page: 页码，从 1 开始
        page_size: 每页数量，默认 10，最大 100
        keyword: 搜索关键词，匹配名称或 RTSP 地址
        zone_id: 区域 ID 筛选
        status: 状态筛选
        is_enabled: 启用状态筛选

    Returns:
        CameraListResponse: 包含摄像头列表和分页信息
    """
    # 构建查询（预加载区域信息）
    query = select(Camera).options(selectinload(Camera.zone))
    count_query = select(func.count(Camera.id))

    # 关键词搜索
    if keyword:
        search_filter = or_(
            Camera.name.ilike(f"%{keyword}%"),
            Camera.rtsp_url.ilike(f"%{keyword}%"),
        )
        query = query.where(search_filter)
        count_query = count_query.where(search_filter)

    # 区域筛选
    if zone_id is not None:
        query = query.where(Camera.zone_id == zone_id)
        count_query = count_query.where(Camera.zone_id == zone_id)

    # 状态筛选
    if status:
        try:
            status_enum = CameraStatus(status)
            query = query.where(Camera.status == status_enum)
            count_query = count_query.where(Camera.status == status_enum)
        except ValueError:
            pass  # 无效状态，忽略筛选

    # 启用状态筛选
    if is_enabled is not None:
        query = query.where(Camera.is_enabled == is_enabled)
        count_query = count_query.where(Camera.is_enabled == is_enabled)

    # 获取总数
    total_result = await db.execute(count_query)
    total = total_result.scalar()

    # 计算总页数
    total_pages = (total + page_size - 1) // page_size

    # 分页查询
    offset = (page - 1) * page_size
    query = query.order_by(Camera.created_at.desc()).offset(offset).limit(page_size)

    result = await db.execute(query)
    cameras = result.scalars().all()

    # 构建响应
    items = [build_camera_response(camera) for camera in cameras]

    return CameraListResponse(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
    )


@router.get("/all", response_model=list[CameraSimpleResponse])
async def get_all_cameras(
    zone_id: Optional[int] = Query(None, description="区域 ID 筛选"),
    is_enabled: Optional[bool] = Query(None, description="启用状态筛选"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """
    获取所有摄像头（简单列表）

    用于下拉选择等场景，返回简化的摄像头信息。

    Returns:
        list[CameraSimpleResponse]: 摄像头简单信息列表
    """
    query = select(Camera)
    
    if zone_id is not None:
        query = query.where(Camera.zone_id == zone_id)
    
    if is_enabled is not None:
        query = query.where(Camera.is_enabled == is_enabled)
    
    query = query.order_by(Camera.name)
    
    result = await db.execute(query)
    cameras = result.scalars().all()
    
    return [
        CameraSimpleResponse(
            id=c.id,
            name=c.name,
            zone_id=c.zone_id,
            status=c.status.value if isinstance(c.status, CameraStatus) else c.status,
            is_enabled=c.is_enabled,
        )
        for c in cameras
    ]


@router.get("/status", response_model=CameraStatusListResponse)
async def get_cameras_status(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """
    获取所有摄像头实时状态

    返回所有摄像头的状态信息及统计数据。

    Returns:
        CameraStatusListResponse: 摄像头状态列表及统计
    """
    result = await db.execute(select(Camera).order_by(Camera.name))
    cameras = result.scalars().all()
    
    items = []
    online_count = 0
    offline_count = 0
    error_count = 0
    
    for camera in cameras:
        status_value = camera.status.value if isinstance(camera.status, CameraStatus) else camera.status
        
        if status_value == CameraStatus.ONLINE.value:
            online_count += 1
        elif status_value == CameraStatus.OFFLINE.value:
            offline_count += 1
        else:
            error_count += 1
        
        items.append(CameraStatusResponse(
            id=camera.id,
            name=camera.name,
            status=status_value,
            is_enabled=camera.is_enabled,
            last_heartbeat_at=camera.last_heartbeat_at,
        ))
    
    return CameraStatusListResponse(
        items=items,
        online_count=online_count,
        offline_count=offline_count,
        error_count=error_count,
        total=len(items),
    )


@router.post("", response_model=CameraResponse, status_code=status.HTTP_201_CREATED)
async def create_camera(
    camera_data: CameraCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    """
    创建新摄像头

    仅管理员可创建摄像头。

    Args:
        camera_data: 摄像头创建数据

    Returns:
        CameraResponse: 创建成功的摄像头信息

    Raises:
        HTTPException 400: 摄像头名称已存在
        HTTPException 404: 指定的区域不存在
    """
    # 检查名称是否已存在
    existing = await db.execute(
        select(Camera).where(Camera.name == camera_data.name)
    )
    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Camera with this name already exists",
        )

    # 检查区域是否存在
    if camera_data.zone_id:
        zone_result = await db.execute(
            select(CameraZone).where(CameraZone.id == camera_data.zone_id)
        )
        if not zone_result.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Zone not found",
            )

    # 创建摄像头
    new_camera = Camera(
        name=camera_data.name,
        zone_id=camera_data.zone_id,
        rtsp_url=camera_data.rtsp_url,
        username=camera_data.username,
        password=camera_data.password,  # TODO: 加密存储
        resolution=camera_data.resolution,
        fps=camera_data.fps,
        status=CameraStatus.OFFLINE,
        is_enabled=camera_data.is_enabled,
        config=camera_data.config,
    )

    db.add(new_camera)
    await db.commit()
    
    # 重新查询以获取关联的区域信息
    result = await db.execute(
        select(Camera)
        .options(selectinload(Camera.zone))
        .where(Camera.id == new_camera.id)
    )
    camera = result.scalar_one()

    return build_camera_response(camera)


@router.get("/{camera_id}", response_model=CameraResponse)
async def get_camera(
    camera_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """
    获取摄像头详情

    Args:
        camera_id: 摄像头 ID

    Returns:
        CameraResponse: 摄像头详细信息

    Raises:
        HTTPException 404: 摄像头不存在
    """
    result = await db.execute(
        select(Camera)
        .options(selectinload(Camera.zone))
        .where(Camera.id == camera_id)
    )
    camera = result.scalar_one_or_none()

    if not camera:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Camera not found",
        )

    return build_camera_response(camera)


@router.put("/{camera_id}", response_model=CameraResponse)
async def update_camera(
    camera_id: int,
    camera_data: CameraUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    """
    更新摄像头配置

    仅管理员可更新摄像头。

    Args:
        camera_id: 摄像头 ID
        camera_data: 更新数据

    Returns:
        CameraResponse: 更新后的摄像头信息

    Raises:
        HTTPException 404: 摄像头不存在
        HTTPException 400: 摄像头名称已存在
    """
    result = await db.execute(
        select(Camera)
        .options(selectinload(Camera.zone))
        .where(Camera.id == camera_id)
    )
    camera = result.scalar_one_or_none()

    if not camera:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Camera not found",
        )

    # 如果修改了名称，检查是否重复
    if camera_data.name and camera_data.name != camera.name:
        existing = await db.execute(
            select(Camera).where(
                Camera.name == camera_data.name,
                Camera.id != camera_id
            )
        )
        if existing.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Camera with this name already exists",
            )

    # 如果修改了区域，检查区域是否存在
    if camera_data.zone_id is not None and camera_data.zone_id != camera.zone_id:
        if camera_data.zone_id > 0:
            zone_result = await db.execute(
                select(CameraZone).where(CameraZone.id == camera_data.zone_id)
            )
            if not zone_result.scalar_one_or_none():
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Zone not found",
                )

    # 更新字段
    if camera_data.name is not None:
        camera.name = camera_data.name
    if camera_data.zone_id is not None:
        camera.zone_id = camera_data.zone_id if camera_data.zone_id > 0 else None
    if camera_data.rtsp_url is not None:
        camera.rtsp_url = camera_data.rtsp_url
    if camera_data.username is not None:
        camera.username = camera_data.username
    if camera_data.password is not None:
        camera.password = camera_data.password  # TODO: 加密存储
    if camera_data.resolution is not None:
        camera.resolution = camera_data.resolution
    if camera_data.fps is not None:
        camera.fps = camera_data.fps
    if camera_data.config is not None:
        camera.config = camera_data.config

    await db.commit()
    
    # 重新查询以获取最新数据
    result = await db.execute(
        select(Camera)
        .options(selectinload(Camera.zone))
        .where(Camera.id == camera_id)
    )
    camera = result.scalar_one()

    return build_camera_response(camera)


@router.delete("/{camera_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_camera(
    camera_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    """
    删除摄像头

    仅管理员可删除摄像头。

    Args:
        camera_id: 摄像头 ID

    Raises:
        HTTPException 404: 摄像头不存在
    """
    result = await db.execute(select(Camera).where(Camera.id == camera_id))
    camera = result.scalar_one_or_none()

    if not camera:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Camera not found",
        )

    await db.delete(camera)
    await db.commit()

    return None


@router.get("/{camera_id}/stream")
async def get_camera_stream(
    camera_id: int,
    token: Optional[str] = Query(None, description="JWT Token（用于 img 标签认证）"),
    db: AsyncSession = Depends(get_db),
):
    """
    获取摄像头 MJPEG 视频流

    将 RTSP 流转换为 MJPEG 格式，供浏览器直接显示。
    支持通过 URL 参数传递 token 进行认证（因为 img 标签无法设置 Header）。

    Args:
        camera_id: 摄像头 ID
        token: JWT Token

    Returns:
        StreamingResponse: MJPEG 视频流
    """
    from fastapi.responses import StreamingResponse
    import cv2
    from jose import jwt, JWTError
    from app.core.config import settings
    
    # 验证 token
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
        )
    
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=["HS256"])
        username = payload.get("sub")
        if not username:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")
    except JWTError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")
    
    result = await db.execute(select(Camera).where(Camera.id == camera_id))
    camera = result.scalar_one_or_none()

    if not camera:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Camera not found",
        )

    # 构建带认证的 RTSP URL
    rtsp_url = camera.rtsp_url
    if camera.username and camera.password:
        if "://" in rtsp_url:
            protocol, rest = rtsp_url.split("://", 1)
            rtsp_url = f"{protocol}://{camera.username}:{camera.password}@{rest}"

    def generate_frames():
        """生成 MJPEG 帧"""
        cap = cv2.VideoCapture(rtsp_url)
        cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
        
        try:
            while True:
                ret, frame = cap.read()
                if not ret:
                    # 尝试重连
                    cap.release()
                    cap = cv2.VideoCapture(rtsp_url)
                    cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
                    continue
                
                # 缩放到合理尺寸以减少带宽
                height, width = frame.shape[:2]
                if width > 800:
                    scale = 800 / width
                    frame = cv2.resize(frame, (800, int(height * scale)))
                
                # 编码为 JPEG
                _, buffer = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 70])
                frame_bytes = buffer.tobytes()
                
                yield (
                    b'--frame\r\n'
                    b'Content-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n'
                )
        finally:
            cap.release()

    return StreamingResponse(
        generate_frames(),
        media_type='multipart/x-mixed-replace; boundary=frame'
    )


@router.post("/{camera_id}/test", response_model=CameraTestResult)
async def test_camera_connection(
    camera_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """
    测试摄像头连通性

    尝试连接摄像头的 RTSP 流，检测是否可以正常访问。

    Args:
        camera_id: 摄像头 ID

    Returns:
        CameraTestResult: 测试结果

    Raises:
        HTTPException 404: 摄像头不存在
    """
    result = await db.execute(select(Camera).where(Camera.id == camera_id))
    camera = result.scalar_one_or_none()

    if not camera:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Camera not found",
        )

    # 构建带认证的 RTSP URL
    rtsp_url = camera.rtsp_url
    if camera.username and camera.password:
        # 将认证信息嵌入 URL
        # rtsp://username:password@ip:port/path
        if "://" in rtsp_url:
            protocol, rest = rtsp_url.split("://", 1)
            rtsp_url = f"{protocol}://{camera.username}:{camera.password}@{rest}"

    # 尝试连接 RTSP 流
    start_time = time.time()
    try:
        import cv2
        
        # 设置超时（OpenCV 没有直接的超时参数，使用环境变量或其他方式）
        cap = cv2.VideoCapture(rtsp_url)
        cap.set(cv2.CAP_PROP_OPEN_TIMEOUT_MSEC, 5000)  # 5 秒超时
        
        if not cap.isOpened():
            return CameraTestResult(
                success=False,
                message="Failed to open RTSP stream",
            )
        
        # 尝试读取一帧
        ret, frame = cap.read()
        response_time = (time.time() - start_time) * 1000  # 转换为毫秒
        
        if not ret:
            cap.release()
            return CameraTestResult(
                success=False,
                message="Failed to read frame from stream",
                response_time_ms=response_time,
            )
        
        # 获取视频属性
        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        fps = int(cap.get(cv2.CAP_PROP_FPS))
        
        cap.release()
        
        # 更新摄像头状态
        camera.status = CameraStatus.ONLINE
        await db.commit()
        
        return CameraTestResult(
            success=True,
            message="Connection successful",
            response_time_ms=round(response_time, 2),
            resolution_detected=f"{width}x{height}" if width > 0 and height > 0 else None,
            fps_detected=fps if fps > 0 else None,
        )
        
    except ImportError:
        return CameraTestResult(
            success=False,
            message="OpenCV not installed. Cannot test RTSP connection.",
        )
    except Exception as e:
        return CameraTestResult(
            success=False,
            message=f"Connection failed: {str(e)}",
        )


@router.patch("/{camera_id}/toggle", response_model=CameraResponse)
async def toggle_camera(
    camera_id: int,
    toggle_data: CameraToggleRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    """
    启用/停用摄像头分析

    仅管理员可切换摄像头状态。启用时会自动将摄像头添加到视频分析引擎，
    停用时会从引擎中移除。

    Args:
        camera_id: 摄像头 ID
        toggle_data: 切换请求数据

    Returns:
        CameraResponse: 更新后的摄像头信息

    Raises:
        HTTPException 404: 摄像头不存在
    """
    result = await db.execute(
        select(Camera)
        .options(selectinload(Camera.zone))
        .where(Camera.id == camera_id)
    )
    camera = result.scalar_one_or_none()

    if not camera:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Camera not found",
        )

    camera.is_enabled = toggle_data.is_enabled
    await db.commit()
    await db.refresh(camera)

    # 与视频分析引擎联动
    try:
        from main import get_engine
        engine = get_engine()
        
        if engine is not None:
            if toggle_data.is_enabled:
                # 启用分析：添加摄像头到引擎
                # 构建带认证的 RTSP URL
                rtsp_url = camera.rtsp_url
                if camera.username and camera.password:
                    if "://" in rtsp_url:
                        protocol, rest = rtsp_url.split("://", 1)
                        rtsp_url = f"{protocol}://{camera.username}:{camera.password}@{rest}"
                
                zone_name = camera.zone.name if camera.zone else None
                await engine.add_camera(
                    camera_id=camera.id,
                    camera_name=camera.name,
                    rtsp_url=rtsp_url,
                    zone_name=zone_name,
                )
            else:
                # 停用分析：从引擎移除摄像头
                await engine.remove_camera(camera.id)
    except ImportError:
        pass  # 引擎未初始化，忽略
    except Exception as e:
        import logging
        logging.getLogger(__name__).warning(f"引擎联动失败: {e}")

    return build_camera_response(camera)


@router.post("/{camera_id}/start-analysis")
async def start_camera_analysis(
    camera_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    """
    启动摄像头视频分析

    将摄像头添加到视频分析引擎开始人脸识别。

    Args:
        camera_id: 摄像头 ID

    Returns:
        dict: 操作结果

    Raises:
        HTTPException 404: 摄像头不存在
        HTTPException 503: 引擎不可用
    """
    result = await db.execute(
        select(Camera)
        .options(selectinload(Camera.zone))
        .where(Camera.id == camera_id)
    )
    camera = result.scalar_one_or_none()

    if not camera:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Camera not found",
        )

    # 获取引擎实例
    try:
        from main import get_engine
        engine = get_engine()
    except ImportError:
        engine = None

    if engine is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="视频分析引擎不可用",
        )

    # 构建带认证的 RTSP URL
    rtsp_url = camera.rtsp_url
    if camera.username and camera.password:
        if "://" in rtsp_url:
            protocol, rest = rtsp_url.split("://", 1)
            rtsp_url = f"{protocol}://{camera.username}:{camera.password}@{rest}"

    zone_name = camera.zone.name if camera.zone else None

    try:
        success = await engine.add_camera(
            camera_id=camera.id,
            name=camera.name,
            rtsp_url=rtsp_url,
            zone_name=zone_name,
        )

        if success:
            # 更新数据库状态
            camera.is_enabled = True
            await db.commit()
            
            return {
                "success": True,
                "message": f"摄像头 {camera.name} 已开始分析",
                "camera_id": camera.id,
            }
        else:
            return {
                "success": False,
                "message": "启动分析失败，可能摄像头已在分析中",
                "camera_id": camera.id,
            }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"启动分析失败: {str(e)}",
        )


@router.post("/{camera_id}/stop-analysis")
async def stop_camera_analysis(
    camera_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    """
    停止摄像头视频分析

    从视频分析引擎中移除摄像头。

    Args:
        camera_id: 摄像头 ID

    Returns:
        dict: 操作结果

    Raises:
        HTTPException 404: 摄像头不存在
        HTTPException 503: 引擎不可用
    """
    result = await db.execute(select(Camera).where(Camera.id == camera_id))
    camera = result.scalar_one_or_none()

    if not camera:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Camera not found",
        )

    # 获取引擎实例
    try:
        from main import get_engine
        engine = get_engine()
    except ImportError:
        engine = None

    if engine is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="视频分析引擎不可用",
        )

    try:
        success = await engine.remove_camera(camera_id)

        if success:
            # 更新数据库状态
            camera.is_enabled = False
            await db.commit()
            
            return {
                "success": True,
                "message": f"摄像头 {camera.name} 已停止分析",
                "camera_id": camera.id,
            }
        else:
            return {
                "success": False,
                "message": "停止分析失败，可能摄像头未在分析中",
                "camera_id": camera.id,
            }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"停止分析失败: {str(e)}",
        )


@router.get("/{camera_id}/analysis-status")
async def get_camera_analysis_status(
    camera_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """
    获取摄像头分析状态

    返回摄像头在视频分析引擎中的实时状态。

    Args:
        camera_id: 摄像头 ID

    Returns:
        dict: 分析状态信息
    """
    result = await db.execute(select(Camera).where(Camera.id == camera_id))
    camera = result.scalar_one_or_none()

    if not camera:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Camera not found",
        )

    # 获取引擎实例
    try:
        from main import get_engine
        engine = get_engine()
    except ImportError:
        engine = None

    if engine is None:
        return {
            "camera_id": camera_id,
            "camera_name": camera.name,
            "is_enabled": camera.is_enabled,
            "engine_status": "unavailable",
            "message": "视频分析引擎不可用",
        }

    # 获取引擎中的摄像头状态
    camera_status = engine.get_camera_status(camera_id)

    if camera_status is None:
        return {
            "camera_id": camera_id,
            "camera_name": camera.name,
            "is_enabled": camera.is_enabled,
            "engine_status": "not_running",
            "message": "摄像头未在引擎中运行",
        }

    return {
        "camera_id": camera_id,
        "camera_name": camera.name,
        "is_enabled": camera.is_enabled,
        "engine_status": camera_status.get("status", "unknown"),
        "fps": camera_status.get("fps", 0),
        "queue_size": camera_status.get("queue_size", 0),
        "total_frames": camera_status.get("total_frames", 0),
        "processed_frames": camera_status.get("processed_frames", 0),
        "last_frame_time": camera_status.get("last_frame_time"),
    }


@router.patch("/{camera_id}/status")
async def update_camera_status(
    camera_id: int,
    new_status: str = Query(..., description="新状态 (online/offline/error)"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """
    更新摄像头状态（内部使用）

    用于视频分析引擎更新摄像头状态。

    Args:
        camera_id: 摄像头 ID
        new_status: 新状态

    Returns:
        dict: 更新结果
    """
    result = await db.execute(select(Camera).where(Camera.id == camera_id))
    camera = result.scalar_one_or_none()

    if not camera:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Camera not found",
        )

    try:
        status_enum = CameraStatus(new_status)
        camera.status = status_enum
        
        # 如果是在线状态，更新心跳时间
        if status_enum == CameraStatus.ONLINE:
            from datetime import datetime, timezone
            camera.last_heartbeat_at = datetime.now(timezone.utc)
        
        await db.commit()
        
        return {"success": True, "message": f"Status updated to {new_status}"}
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid status: {new_status}. Must be one of: online, offline, error",
        )
