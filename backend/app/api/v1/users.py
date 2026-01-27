"""
用户管理接口模块

提供用户的增删改查功能，仅管理员可访问。

功能列表：
- GET /users - 获取用户列表（支持分页和筛选）
- POST /users - 创建新用户
- GET /users/{user_id} - 获取用户详情
- PUT /users/{user_id} - 更新用户信息
- PATCH /users/{user_id}/status - 启用/禁用用户
- POST /users/{user_id}/reset-password - 重置用户密码
- DELETE /users/{user_id} - 删除用户
"""
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy import select, func, or_
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db, require_admin
from app.models.user import User, UserRole
from app.core.security import get_password_hash
from app.schemas.user import (
    UserCreate,
    UserUpdate,
    UserStatusUpdate,
    ResetPasswordRequest,
    UserDetailResponse,
    UserListResponse,
)

router = APIRouter(prefix="/users", tags=["用户管理"])


@router.get("", response_model=UserListResponse)
async def get_users(
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(10, ge=1, le=100, description="每页数量"),
    keyword: Optional[str] = Query(None, description="搜索关键词（用户名/邮箱/手机号）"),
    role: Optional[str] = Query(None, description="角色筛选"),
    is_active: Optional[bool] = Query(None, description="状态筛选"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    """
    获取用户列表

    支持分页和筛选功能，仅管理员可访问。

    Args:
        page: 页码，从 1 开始
        page_size: 每页数量，默认 10，最大 100
        keyword: 搜索关键词，匹配用户名、邮箱或手机号
        role: 角色筛选（admin/operator）
        is_active: 状态筛选（true/false）

    Returns:
        UserListResponse: 包含用户列表和分页信息
    """
    # 构建查询条件
    query = select(User)
    count_query = select(func.count(User.id))

    # 关键词搜索
    if keyword:
        search_filter = or_(
            User.username.ilike(f"%{keyword}%"),
            User.email.ilike(f"%{keyword}%"),
            User.phone.ilike(f"%{keyword}%"),
        )
        query = query.where(search_filter)
        count_query = count_query.where(search_filter)

    # 角色筛选
    if role:
        try:
            role_enum = UserRole(role)
            query = query.where(User.role == role_enum)
            count_query = count_query.where(User.role == role_enum)
        except ValueError:
            pass  # 无效角色，忽略筛选

    # 状态筛选
    if is_active is not None:
        query = query.where(User.is_active == is_active)
        count_query = count_query.where(User.is_active == is_active)

    # 获取总数
    total_result = await db.execute(count_query)
    total = total_result.scalar()

    # 计算总页数
    total_pages = (total + page_size - 1) // page_size

    # 分页查询
    offset = (page - 1) * page_size
    query = query.order_by(User.created_at.desc()).offset(offset).limit(page_size)

    result = await db.execute(query)
    users = result.scalars().all()

    return UserListResponse(
        items=[UserDetailResponse.model_validate(user) for user in users],
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
    )


@router.post("", response_model=UserDetailResponse, status_code=status.HTTP_201_CREATED)
async def create_user(
    user_data: UserCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    """
    创建新用户

    仅管理员可创建用户。用户名必须唯一。

    Args:
        user_data: 用户创建数据

    Returns:
        UserDetailResponse: 创建成功的用户信息

    Raises:
        HTTPException 400: 用户名已存在
    """
    # 检查用户名是否已存在
    existing = await db.execute(
        select(User).where(User.username == user_data.username)
    )
    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username already exists",
        )

    # 创建用户
    new_user = User(
        username=user_data.username,
        password_hash=get_password_hash(user_data.password),
        email=user_data.email,
        phone=user_data.phone,
        role=UserRole(user_data.role.value),
        is_active=True,
    )

    db.add(new_user)
    await db.commit()
    await db.refresh(new_user)

    return UserDetailResponse.model_validate(new_user)


@router.get("/{user_id}", response_model=UserDetailResponse)
async def get_user(
    user_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    """
    获取用户详情

    Args:
        user_id: 用户 ID

    Returns:
        UserDetailResponse: 用户详细信息

    Raises:
        HTTPException 404: 用户不存在
    """
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    return UserDetailResponse.model_validate(user)


@router.put("/{user_id}", response_model=UserDetailResponse)
async def update_user(
    user_id: int,
    user_data: UserUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    """
    更新用户信息

    可更新邮箱、手机号、角色。不能修改用户名和密码。

    Args:
        user_id: 用户 ID
        user_data: 更新数据

    Returns:
        UserDetailResponse: 更新后的用户信息

    Raises:
        HTTPException 404: 用户不存在
        HTTPException 400: 不能修改自己的角色
    """
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    # 不允许管理员修改自己的角色
    if user_id == current_user.id and user_data.role is not None:
        if UserRole(user_data.role.value) != current_user.role:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot change your own role",
            )

    # 更新字段
    if user_data.email is not None:
        user.email = user_data.email
    if user_data.phone is not None:
        user.phone = user_data.phone
    if user_data.role is not None:
        user.role = UserRole(user_data.role.value)

    await db.commit()
    await db.refresh(user)

    return UserDetailResponse.model_validate(user)


@router.patch("/{user_id}/status", response_model=UserDetailResponse)
async def update_user_status(
    user_id: int,
    status_data: UserStatusUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    """
    启用/禁用用户

    Args:
        user_id: 用户 ID
        status_data: 状态更新数据

    Returns:
        UserDetailResponse: 更新后的用户信息

    Raises:
        HTTPException 404: 用户不存在
        HTTPException 400: 不能禁用自己
    """
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    # 不允许禁用自己
    if user_id == current_user.id and not status_data.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot disable yourself",
        )

    user.is_active = status_data.is_active
    await db.commit()
    await db.refresh(user)

    return UserDetailResponse.model_validate(user)


@router.post("/{user_id}/reset-password", response_model=UserDetailResponse)
async def reset_user_password(
    user_id: int,
    password_data: ResetPasswordRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    """
    重置用户密码

    管理员可重置任意用户的密码。

    Args:
        user_id: 用户 ID
        password_data: 新密码数据

    Returns:
        UserDetailResponse: 用户信息

    Raises:
        HTTPException 404: 用户不存在
    """
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    user.password_hash = get_password_hash(password_data.new_password)
    await db.commit()
    await db.refresh(user)

    return UserDetailResponse.model_validate(user)


@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_user(
    user_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    """
    删除用户

    物理删除用户，操作不可恢复。建议使用禁用功能代替删除。

    Args:
        user_id: 用户 ID

    Raises:
        HTTPException 404: 用户不存在
        HTTPException 400: 不能删除自己
    """
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    # 不允许删除自己
    if user_id == current_user.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot delete yourself",
        )

    await db.delete(user)
    await db.commit()

    return None
