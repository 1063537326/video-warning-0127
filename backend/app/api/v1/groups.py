"""
人员分组管理接口模块

提供人员分组的增删改查功能。

功能列表：
- GET /person-groups - 获取分组列表（支持分页和筛选）
- GET /person-groups/all - 获取所有分组（用于下拉选择）
- GET /person-groups/stats - 获取分组统计信息
- POST /person-groups - 创建新分组
- GET /person-groups/{group_id} - 获取分组详情
- PUT /person-groups/{group_id} - 更新分组信息
- DELETE /person-groups/{group_id} - 删除分组
"""
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy import select, func, or_
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db, get_current_active_user, require_admin
from app.models.person import PersonGroup, KnownPerson
from app.models.user import User
from app.schemas.group import (
    GroupCreate,
    GroupUpdate,
    GroupResponse,
    GroupSimpleResponse,
    GroupListResponse,
    GroupStatsResponse,
    GroupAlertToggle,
)

router = APIRouter(prefix="/person-groups", tags=["人员分组"])


async def get_group_with_person_count(group: PersonGroup, db: AsyncSession) -> GroupResponse:
    """
    获取分组响应，包含人员数量
    
    Args:
        group: 分组对象
        db: 数据库会话
        
    Returns:
        GroupResponse: 包含人员数量的分组响应
    """
    # 查询该分组下的人员数量
    count_result = await db.execute(
        select(func.count(KnownPerson.id)).where(KnownPerson.group_id == group.id)
    )
    person_count = count_result.scalar() or 0
    
    return GroupResponse(
        id=group.id,
        name=group.name,
        description=group.description,
        color=group.color,
        alert_enabled=group.alert_enabled,
        alert_priority=group.alert_priority,
        sort_order=group.sort_order,
        person_count=person_count,
        created_at=group.created_at,
        updated_at=group.updated_at,
    )


@router.get("", response_model=GroupListResponse)
async def get_groups(
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(10, ge=1, le=100, description="每页数量"),
    keyword: Optional[str] = Query(None, description="搜索关键词（名称/描述）"),
    alert_enabled: Optional[bool] = Query(None, description="报警启用状态筛选"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """
    获取分组列表

    支持分页和筛选功能。

    Args:
        page: 页码，从 1 开始
        page_size: 每页数量，默认 10，最大 100
        keyword: 搜索关键词，匹配名称或描述
        alert_enabled: 报警启用状态筛选

    Returns:
        GroupListResponse: 包含分组列表和分页信息
    """
    # 构建查询条件
    query = select(PersonGroup)
    count_query = select(func.count(PersonGroup.id))

    # 关键词搜索
    if keyword:
        search_filter = or_(
            PersonGroup.name.ilike(f"%{keyword}%"),
            PersonGroup.description.ilike(f"%{keyword}%"),
        )
        query = query.where(search_filter)
        count_query = count_query.where(search_filter)

    # 报警启用状态筛选
    if alert_enabled is not None:
        query = query.where(PersonGroup.alert_enabled == alert_enabled)
        count_query = count_query.where(PersonGroup.alert_enabled == alert_enabled)

    # 获取总数
    total_result = await db.execute(count_query)
    total = total_result.scalar()

    # 计算总页数
    total_pages = (total + page_size - 1) // page_size

    # 分页查询（按排序顺序和创建时间排序）
    offset = (page - 1) * page_size
    query = query.order_by(PersonGroup.sort_order, PersonGroup.created_at.desc()).offset(offset).limit(page_size)

    result = await db.execute(query)
    groups = result.scalars().all()

    # 构建响应（包含人员数量）
    items = []
    for group in groups:
        group_response = await get_group_with_person_count(group, db)
        items.append(group_response)

    return GroupListResponse(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
    )


@router.get("/all", response_model=list[GroupSimpleResponse])
async def get_all_groups(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """
    获取所有分组（简单列表）

    用于下拉选择等场景，返回简化的分组信息。

    Returns:
        list[GroupSimpleResponse]: 分组简单信息列表
    """
    result = await db.execute(
        select(PersonGroup).order_by(PersonGroup.sort_order, PersonGroup.name)
    )
    groups = result.scalars().all()
    
    return [GroupSimpleResponse.model_validate(group) for group in groups]


@router.get("/stats", response_model=list[GroupStatsResponse])
async def get_groups_stats(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """
    获取分组统计信息

    返回每个分组的人员数量统计。

    Returns:
        list[GroupStatsResponse]: 分组统计列表
    """
    result = await db.execute(
        select(PersonGroup).order_by(PersonGroup.sort_order, PersonGroup.name)
    )
    groups = result.scalars().all()
    
    stats = []
    for group in groups:
        # 查询人员数量
        count_result = await db.execute(
            select(func.count(KnownPerson.id)).where(KnownPerson.group_id == group.id)
        )
        person_count = count_result.scalar() or 0
        
        stats.append(GroupStatsResponse(
            id=group.id,
            name=group.name,
            color=group.color,
            person_count=person_count,
            alert_enabled=group.alert_enabled,
            alert_priority=group.alert_priority,
        ))
    
    return stats


@router.post("", response_model=GroupResponse, status_code=status.HTTP_201_CREATED)
async def create_group(
    group_data: GroupCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    """
    创建新分组

    仅管理员可创建分组。分组名称必须唯一。

    Args:
        group_data: 分组创建数据

    Returns:
        GroupResponse: 创建成功的分组信息

    Raises:
        HTTPException 400: 分组名称已存在
    """
    # 检查名称是否已存在
    existing = await db.execute(
        select(PersonGroup).where(PersonGroup.name == group_data.name)
    )
    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Group with this name already exists",
        )

    # 创建分组
    new_group = PersonGroup(
        name=group_data.name,
        description=group_data.description,
        color=group_data.color,
        alert_enabled=group_data.alert_enabled,
        alert_priority=group_data.alert_priority,
        sort_order=group_data.sort_order,
    )

    db.add(new_group)
    await db.commit()
    await db.refresh(new_group)

    return await get_group_with_person_count(new_group, db)


@router.get("/{group_id}", response_model=GroupResponse)
async def get_group(
    group_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """
    获取分组详情

    Args:
        group_id: 分组 ID

    Returns:
        GroupResponse: 分组详细信息

    Raises:
        HTTPException 404: 分组不存在
    """
    result = await db.execute(select(PersonGroup).where(PersonGroup.id == group_id))
    group = result.scalar_one_or_none()

    if not group:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Group not found",
        )

    return await get_group_with_person_count(group, db)


@router.put("/{group_id}", response_model=GroupResponse)
async def update_group(
    group_id: int,
    group_data: GroupUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    """
    更新分组信息

    仅管理员可更新分组。

    Args:
        group_id: 分组 ID
        group_data: 更新数据

    Returns:
        GroupResponse: 更新后的分组信息

    Raises:
        HTTPException 404: 分组不存在
        HTTPException 400: 分组名称已存在
    """
    result = await db.execute(select(PersonGroup).where(PersonGroup.id == group_id))
    group = result.scalar_one_or_none()

    if not group:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Group not found",
        )

    # 如果修改了名称，检查是否重复
    if group_data.name and group_data.name != group.name:
        existing = await db.execute(
            select(PersonGroup).where(
                PersonGroup.name == group_data.name,
                PersonGroup.id != group_id
            )
        )
        if existing.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Group with this name already exists",
            )

    # 更新字段
    if group_data.name is not None:
        group.name = group_data.name
    if group_data.description is not None:
        group.description = group_data.description
    if group_data.color is not None:
        group.color = group_data.color
    if group_data.alert_enabled is not None:
        group.alert_enabled = group_data.alert_enabled
    if group_data.alert_priority is not None:
        group.alert_priority = group_data.alert_priority
    if group_data.sort_order is not None:
        group.sort_order = group_data.sort_order

    await db.commit()
    await db.refresh(group)

    return await get_group_with_person_count(group, db)


@router.delete("/{group_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_group(
    group_id: int,
    force: bool = Query(False, description="强制删除（即使有关联人员）"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    """
    删除分组

    仅管理员可删除分组。默认情况下，如果分组下有人员，不允许删除。
    使用 force=true 可强制删除，关联的人员将解除与该分组的关联。

    Args:
        group_id: 分组 ID
        force: 是否强制删除

    Raises:
        HTTPException 404: 分组不存在
        HTTPException 400: 分组下有人员（未使用强制删除）
    """
    result = await db.execute(select(PersonGroup).where(PersonGroup.id == group_id))
    group = result.scalar_one_or_none()

    if not group:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Group not found",
        )

    # 检查是否有关联的人员
    person_count_result = await db.execute(
        select(func.count(KnownPerson.id)).where(KnownPerson.group_id == group_id)
    )
    person_count = person_count_result.scalar() or 0

    if person_count > 0:
        if not force:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Group has {person_count} person(s). Use force=true to delete anyway.",
            )
        else:
            # 强制删除：解除人员与分组的关联
            await db.execute(
                KnownPerson.__table__.update().where(KnownPerson.group_id == group_id).values(group_id=None)
            )

    await db.delete(group)
    await db.commit()

    return None


@router.patch("/{group_id}/alert", response_model=GroupResponse)
async def toggle_group_alert(
    group_id: int,
    data: GroupAlertToggle,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    """
    切换分组报警状态

    仅管理员可切换报警状态。

    Args:
        group_id: 分组 ID
        data: 包含 alert_enabled 的请求体

    Returns:
        GroupResponse: 更新后的分组信息

    Raises:
        HTTPException 404: 分组不存在
    """
    result = await db.execute(select(PersonGroup).where(PersonGroup.id == group_id))
    group = result.scalar_one_or_none()

    if not group:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Group not found",
        )

    group.alert_enabled = data.alert_enabled
    await db.commit()
    await db.refresh(group)

    return await get_group_with_person_count(group, db)
