"""
摄像头区域管理接口模块

提供摄像头区域的增删改查功能。

功能列表：
- GET /zones - 获取区域列表（支持分页和筛选）
- GET /zones/all - 获取所有区域（用于下拉选择）
- GET /zones/tree - 获取区域树（按楼栋-楼层分组）
- POST /zones - 创建新区域
- GET /zones/{zone_id} - 获取区域详情
- PUT /zones/{zone_id} - 更新区域信息
- DELETE /zones/{zone_id} - 删除区域
"""
from typing import Optional
from collections import defaultdict
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy import select, func, or_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.deps import get_db, get_current_active_user, require_admin
from app.models.camera import CameraZone, Camera
from app.models.user import User
from app.schemas.zone import (
    ZoneCreate,
    ZoneUpdate,
    ZoneResponse,
    ZoneSimpleResponse,
    ZoneListResponse,
    ZoneTreeNode,
    ZoneTreeResponse,
)

router = APIRouter(prefix="/zones", tags=["区域管理"])


async def get_zone_with_camera_count(zone: CameraZone, db: AsyncSession) -> ZoneResponse:
    """
    获取区域响应，包含摄像头数量
    
    Args:
        zone: 区域对象
        db: 数据库会话
        
    Returns:
        ZoneResponse: 包含摄像头数量的区域响应
    """
    # 查询该区域下的摄像头数量
    count_result = await db.execute(
        select(func.count(Camera.id)).where(Camera.zone_id == zone.id)
    )
    camera_count = count_result.scalar() or 0
    
    return ZoneResponse(
        id=zone.id,
        name=zone.name,
        description=zone.description,
        building=zone.building,
        floor=zone.floor,
        sort_order=zone.sort_order,
        camera_count=camera_count,
        created_at=zone.created_at,
        updated_at=zone.updated_at,
    )


@router.get("", response_model=ZoneListResponse)
async def get_zones(
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(10, ge=1, le=100, description="每页数量"),
    keyword: Optional[str] = Query(None, description="搜索关键词（名称/描述）"),
    building: Optional[str] = Query(None, description="楼栋筛选"),
    floor: Optional[str] = Query(None, description="楼层筛选"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """
    获取区域列表

    支持分页和筛选功能。

    Args:
        page: 页码，从 1 开始
        page_size: 每页数量，默认 10，最大 100
        keyword: 搜索关键词，匹配名称或描述
        building: 楼栋筛选
        floor: 楼层筛选

    Returns:
        ZoneListResponse: 包含区域列表和分页信息
    """
    # 构建查询条件
    query = select(CameraZone)
    count_query = select(func.count(CameraZone.id))

    # 关键词搜索
    if keyword:
        search_filter = or_(
            CameraZone.name.ilike(f"%{keyword}%"),
            CameraZone.description.ilike(f"%{keyword}%"),
        )
        query = query.where(search_filter)
        count_query = count_query.where(search_filter)

    # 楼栋筛选
    if building:
        query = query.where(CameraZone.building == building)
        count_query = count_query.where(CameraZone.building == building)

    # 楼层筛选
    if floor:
        query = query.where(CameraZone.floor == floor)
        count_query = count_query.where(CameraZone.floor == floor)

    # 获取总数
    total_result = await db.execute(count_query)
    total = total_result.scalar()

    # 计算总页数
    total_pages = (total + page_size - 1) // page_size

    # 分页查询（按排序顺序和创建时间排序）
    offset = (page - 1) * page_size
    query = query.order_by(CameraZone.sort_order, CameraZone.created_at.desc()).offset(offset).limit(page_size)

    result = await db.execute(query)
    zones = result.scalars().all()

    # 构建响应（包含摄像头数量）
    items = []
    for zone in zones:
        zone_response = await get_zone_with_camera_count(zone, db)
        items.append(zone_response)

    return ZoneListResponse(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
    )


@router.get("/all", response_model=list[ZoneSimpleResponse])
async def get_all_zones(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """
    获取所有区域（简单列表）

    用于下拉选择等场景，返回简化的区域信息。

    Returns:
        list[ZoneSimpleResponse]: 区域简单信息列表
    """
    result = await db.execute(
        select(CameraZone).order_by(CameraZone.sort_order, CameraZone.name)
    )
    zones = result.scalars().all()
    
    return [ZoneSimpleResponse.model_validate(zone) for zone in zones]


@router.get("/tree", response_model=ZoneTreeResponse)
async def get_zones_tree(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """
    获取区域树（按楼栋-楼层分组）

    用于树形展示区域结构。

    Returns:
        ZoneTreeResponse: 按楼栋分组的区域树
    """
    result = await db.execute(
        select(CameraZone).order_by(CameraZone.building, CameraZone.floor, CameraZone.sort_order)
    )
    zones = result.scalars().all()
    
    # 按楼栋-楼层分组
    building_map = defaultdict(lambda: defaultdict(list))
    for zone in zones:
        building = zone.building or "未分类"
        floor = zone.floor or "未分类"
        building_map[building][floor].append(
            ZoneSimpleResponse.model_validate(zone)
        )
    
    # 构建树形结构
    items = []
    for building, floors in building_map.items():
        floor_list = []
        for floor_name, zone_list in floors.items():
            floor_list.append({
                "floor": floor_name,
                "zones": [z.model_dump() for z in zone_list]
            })
        items.append(ZoneTreeNode(building=building, floors=floor_list))
    
    return ZoneTreeResponse(items=items)


@router.get("/buildings", response_model=list[str])
async def get_buildings(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """
    获取所有楼栋列表

    用于筛选下拉框。

    Returns:
        list[str]: 楼栋名称列表
    """
    result = await db.execute(
        select(CameraZone.building)
        .where(CameraZone.building.isnot(None))
        .distinct()
        .order_by(CameraZone.building)
    )
    buildings = result.scalars().all()
    return [b for b in buildings if b]


@router.get("/floors", response_model=list[str])
async def get_floors(
    building: Optional[str] = Query(None, description="楼栋（可选，筛选指定楼栋的楼层）"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """
    获取楼层列表

    可指定楼栋筛选。

    Args:
        building: 楼栋名称（可选）

    Returns:
        list[str]: 楼层名称列表
    """
    query = select(CameraZone.floor).where(CameraZone.floor.isnot(None)).distinct()
    
    if building:
        query = query.where(CameraZone.building == building)
    
    query = query.order_by(CameraZone.floor)
    result = await db.execute(query)
    floors = result.scalars().all()
    return [f for f in floors if f]


@router.post("", response_model=ZoneResponse, status_code=status.HTTP_201_CREATED)
async def create_zone(
    zone_data: ZoneCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    """
    创建新区域

    仅管理员可创建区域。

    Args:
        zone_data: 区域创建数据

    Returns:
        ZoneResponse: 创建成功的区域信息

    Raises:
        HTTPException 400: 区域名称已存在（同一楼栋楼层下）
    """
    # 检查同一楼栋楼层下是否有同名区域
    existing_query = select(CameraZone).where(CameraZone.name == zone_data.name)
    if zone_data.building:
        existing_query = existing_query.where(CameraZone.building == zone_data.building)
    if zone_data.floor:
        existing_query = existing_query.where(CameraZone.floor == zone_data.floor)
    
    existing = await db.execute(existing_query)
    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Zone with same name already exists in this building/floor",
        )

    # 创建区域
    new_zone = CameraZone(
        name=zone_data.name,
        description=zone_data.description,
        building=zone_data.building,
        floor=zone_data.floor,
        sort_order=zone_data.sort_order,
    )

    db.add(new_zone)
    await db.commit()
    await db.refresh(new_zone)

    return await get_zone_with_camera_count(new_zone, db)


@router.get("/{zone_id}", response_model=ZoneResponse)
async def get_zone(
    zone_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """
    获取区域详情

    Args:
        zone_id: 区域 ID

    Returns:
        ZoneResponse: 区域详细信息

    Raises:
        HTTPException 404: 区域不存在
    """
    result = await db.execute(select(CameraZone).where(CameraZone.id == zone_id))
    zone = result.scalar_one_or_none()

    if not zone:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Zone not found",
        )

    return await get_zone_with_camera_count(zone, db)


@router.put("/{zone_id}", response_model=ZoneResponse)
async def update_zone(
    zone_id: int,
    zone_data: ZoneUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    """
    更新区域信息

    仅管理员可更新区域。

    Args:
        zone_id: 区域 ID
        zone_data: 更新数据

    Returns:
        ZoneResponse: 更新后的区域信息

    Raises:
        HTTPException 404: 区域不存在
        HTTPException 400: 区域名称已存在
    """
    result = await db.execute(select(CameraZone).where(CameraZone.id == zone_id))
    zone = result.scalar_one_or_none()

    if not zone:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Zone not found",
        )

    # 如果修改了名称，检查是否重复
    if zone_data.name and zone_data.name != zone.name:
        building = zone_data.building if zone_data.building is not None else zone.building
        floor = zone_data.floor if zone_data.floor is not None else zone.floor
        
        existing_query = select(CameraZone).where(
            CameraZone.name == zone_data.name,
            CameraZone.id != zone_id
        )
        if building:
            existing_query = existing_query.where(CameraZone.building == building)
        if floor:
            existing_query = existing_query.where(CameraZone.floor == floor)
        
        existing = await db.execute(existing_query)
        if existing.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Zone with same name already exists in this building/floor",
            )

    # 更新字段
    if zone_data.name is not None:
        zone.name = zone_data.name
    if zone_data.description is not None:
        zone.description = zone_data.description
    if zone_data.building is not None:
        zone.building = zone_data.building
    if zone_data.floor is not None:
        zone.floor = zone_data.floor
    if zone_data.sort_order is not None:
        zone.sort_order = zone_data.sort_order

    await db.commit()
    await db.refresh(zone)

    return await get_zone_with_camera_count(zone, db)


@router.delete("/{zone_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_zone(
    zone_id: int,
    force: bool = Query(False, description="强制删除（即使有关联摄像头）"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    """
    删除区域

    仅管理员可删除区域。默认情况下，如果区域下有摄像头，不允许删除。
    使用 force=true 可强制删除，关联的摄像头将解除与该区域的关联。

    Args:
        zone_id: 区域 ID
        force: 是否强制删除

    Raises:
        HTTPException 404: 区域不存在
        HTTPException 400: 区域下有摄像头（未使用强制删除）
    """
    result = await db.execute(select(CameraZone).where(CameraZone.id == zone_id))
    zone = result.scalar_one_or_none()

    if not zone:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Zone not found",
        )

    # 检查是否有关联的摄像头
    camera_count_result = await db.execute(
        select(func.count(Camera.id)).where(Camera.zone_id == zone_id)
    )
    camera_count = camera_count_result.scalar() or 0

    if camera_count > 0:
        if not force:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Zone has {camera_count} camera(s). Use force=true to delete anyway.",
            )
        else:
            # 强制删除：解除摄像头与区域的关联
            await db.execute(
                Camera.__table__.update().where(Camera.zone_id == zone_id).values(zone_id=None)
            )

    await db.delete(zone)
    await db.commit()

    return None
