"""
人员管理接口模块

提供已知人员的增删改查功能，包括人脸图片管理。

功能列表：
- GET /persons - 获取人员列表（支持分页和筛选）
- GET /persons/all - 获取所有人员（用于下拉选择）
- POST /persons - 新增人员
- GET /persons/{person_id} - 获取人员详情（包含所有人脸图片）
- PUT /persons/{person_id} - 更新人员信息
- PATCH /persons/{person_id}/status - 更新人员状态（在职/离职）
- DELETE /persons/{person_id} - 删除人员
- POST /persons/{person_id}/faces - 上传人脸图片
- DELETE /persons/{person_id}/faces/{face_id} - 删除人脸图片
- PATCH /persons/{person_id}/faces/{face_id}/primary - 设置主图
- POST /persons/import - 批量导入人员
"""
import os
import uuid
from typing import Optional
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, status, Query, UploadFile, File
from sqlalchemy import select, func, or_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.deps import get_db, get_current_active_user, require_admin
from app.models.person import KnownPerson, PersonGroup, FaceImage
from app.models.user import User
from app.core.config import settings
from app.schemas.person import (
    PersonCreate,
    PersonUpdate,
    PersonStatusUpdate,
    PersonResponse,
    PersonDetailResponse,
    PersonSimpleResponse,
    PersonListResponse,
    FaceImageResponse,
    FaceUploadResponse,
    PersonImportRequest,
    PersonImportResult,
    GroupInfo,
)

router = APIRouter(prefix="/persons", tags=["人员管理"])

# 允许的图片格式
ALLOWED_IMAGE_TYPES = {"image/jpeg", "image/png", "image/jpg"}
MAX_IMAGE_SIZE = 5 * 1024 * 1024  # 5MB


def build_face_image_response(face: FaceImage, base_url: str = "") -> FaceImageResponse:
    """
    构建人脸图片响应对象
    
    Args:
        face: 人脸图片 ORM 对象
        base_url: 基础 URL（用于构建完整访问路径）
        
    Returns:
        FaceImageResponse: 人脸图片响应模型
    """
    image_url = f"{base_url}/static/faces/{os.path.basename(face.image_path)}" if face.image_path else None
    
    return FaceImageResponse(
        id=face.id,
        image_path=face.image_path,
        image_id=face.image_id,
        image_url=image_url,
        quality_score=face.quality_score,
        is_primary=face.is_primary,
        created_at=face.created_at,
    )


# ... (skipping to upload_face_image) 
# I need to use multi_replace for this file because the changes are in different places.
# Retracting this tool call and using multi_replace_file_content.


def build_person_response(person: KnownPerson, base_url: str = "") -> PersonResponse:
    """
    构建人员响应对象
    
    Args:
        person: 人员 ORM 对象
        base_url: 基础 URL
        
    Returns:
        PersonResponse: 人员响应模型
    """
    group_info = None
    if person.group:
        group_info = GroupInfo(
            id=person.group.id,
            name=person.group.name,
            color=person.group.color,
        )
    
    # 获取人脸数量和主图
    face_count = len(person.face_images) if person.face_images else 0
    primary_face = None
    
    if person.face_images:
        for face in person.face_images:
            if face.is_primary:
                primary_face = build_face_image_response(face, base_url)
                break
        # 如果没有设置主图，使用第一张
        if not primary_face and person.face_images:
            primary_face = build_face_image_response(person.face_images[0], base_url)
    
    return PersonResponse(
        id=person.id,
        name=person.name,
        employee_id=person.employee_id,
        group_id=person.group_id,
        group=group_info,
        department=person.department,
        phone=person.phone,
        remark=person.remark,
        is_active=person.is_active,
        face_count=face_count,
        primary_face=primary_face,
        created_at=person.created_at,
        updated_at=person.updated_at,
    )


@router.get("", response_model=PersonListResponse)
async def get_persons(
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(10, ge=1, le=100, description="每页数量"),
    keyword: Optional[str] = Query(None, description="搜索关键词（姓名/工号/部门）"),
    group_id: Optional[int] = Query(None, description="分组 ID 筛选"),
    is_active: Optional[bool] = Query(None, description="在职状态筛选"),
    has_face: Optional[bool] = Query(None, description="是否有人脸图片"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """
    获取人员列表

    支持分页和多条件筛选。

    Args:
        page: 页码，从 1 开始
        page_size: 每页数量，默认 10，最大 100
        keyword: 搜索关键词，匹配姓名、工号或部门
        group_id: 分组 ID 筛选
        is_active: 在职状态筛选
        has_face: 是否有人脸图片筛选

    Returns:
        PersonListResponse: 包含人员列表和分页信息
    """
    # 构建查询（预加载分组和人脸图片）
    query = select(KnownPerson).options(
        selectinload(KnownPerson.group),
        selectinload(KnownPerson.face_images)
    )
    count_query = select(func.count(KnownPerson.id))

    # 关键词搜索
    if keyword:
        search_filter = or_(
            KnownPerson.name.ilike(f"%{keyword}%"),
            KnownPerson.employee_id.ilike(f"%{keyword}%"),
            KnownPerson.department.ilike(f"%{keyword}%"),
        )
        query = query.where(search_filter)
        count_query = count_query.where(search_filter)

    # 分组筛选
    if group_id is not None:
        query = query.where(KnownPerson.group_id == group_id)
        count_query = count_query.where(KnownPerson.group_id == group_id)

    # 在职状态筛选
    if is_active is not None:
        query = query.where(KnownPerson.is_active == is_active)
        count_query = count_query.where(KnownPerson.is_active == is_active)

    # 获取总数
    total_result = await db.execute(count_query)
    total = total_result.scalar()

    # 计算总页数
    total_pages = (total + page_size - 1) // page_size

    # 分页查询，按 ID 降序保持稳定排序
    offset = (page - 1) * page_size
    query = query.order_by(KnownPerson.id.desc()).offset(offset).limit(page_size)

    result = await db.execute(query)
    persons = result.scalars().all()

    # 如果需要筛选有/无人脸图片，在内存中过滤
    if has_face is not None:
        if has_face:
            persons = [p for p in persons if p.face_images and len(p.face_images) > 0]
        else:
            persons = [p for p in persons if not p.face_images or len(p.face_images) == 0]

    # 构建响应
    items = [build_person_response(person) for person in persons]

    return PersonListResponse(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
    )


@router.get("/all", response_model=list[PersonSimpleResponse])
async def get_all_persons(
    group_id: Optional[int] = Query(None, description="分组 ID 筛选"),
    is_active: Optional[bool] = Query(True, description="在职状态筛选"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """
    获取所有人员（简单列表）

    用于下拉选择等场景，返回简化的人员信息。

    Returns:
        list[PersonSimpleResponse]: 人员简单信息列表
    """
    query = select(KnownPerson)
    
    if group_id is not None:
        query = query.where(KnownPerson.group_id == group_id)
    
    if is_active is not None:
        query = query.where(KnownPerson.is_active == is_active)
    
    query = query.order_by(KnownPerson.name)
    
    result = await db.execute(query)
    persons = result.scalars().all()
    
    return [PersonSimpleResponse.model_validate(person) for person in persons]


@router.post("", response_model=PersonResponse, status_code=status.HTTP_201_CREATED)
async def create_person(
    person_data: PersonCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    """
    创建新人员

    仅管理员可创建人员。

    Args:
        person_data: 人员创建数据

    Returns:
        PersonResponse: 创建成功的人员信息

    Raises:
        HTTPException 400: 工号已存在
        HTTPException 404: 指定的分组不存在
    """
    # 检查工号是否已存在（如果提供了工号）
    if person_data.employee_id:
        existing = await db.execute(
            select(KnownPerson).where(KnownPerson.employee_id == person_data.employee_id)
        )
        if existing.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Employee ID already exists",
            )

    # 检查分组是否存在
    if person_data.group_id:
        group_result = await db.execute(
            select(PersonGroup).where(PersonGroup.id == person_data.group_id)
        )
        if not group_result.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Group not found",
            )

    # 创建人员
    new_person = KnownPerson(
        name=person_data.name,
        employee_id=person_data.employee_id,
        group_id=person_data.group_id,
        department=person_data.department,
        phone=person_data.phone,
        remark=person_data.remark,
        is_active=person_data.is_active,
    )

    db.add(new_person)
    await db.commit()
    
    # 重新查询以获取关联信息
    result = await db.execute(
        select(KnownPerson)
        .options(selectinload(KnownPerson.group), selectinload(KnownPerson.face_images))
        .where(KnownPerson.id == new_person.id)
    )
    person = result.scalar_one()

    return build_person_response(person)


@router.get("/{person_id}", response_model=PersonDetailResponse)
async def get_person(
    person_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """
    获取人员详情

    包含所有人脸图片信息。

    Args:
        person_id: 人员 ID

    Returns:
        PersonDetailResponse: 人员详细信息

    Raises:
        HTTPException 404: 人员不存在
    """
    result = await db.execute(
        select(KnownPerson)
        .options(selectinload(KnownPerson.group), selectinload(KnownPerson.face_images))
        .where(KnownPerson.id == person_id)
    )
    person = result.scalar_one_or_none()

    if not person:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Person not found",
        )

    # 构建基础响应
    base_response = build_person_response(person)
    
    # 添加所有人脸图片
    face_images = [build_face_image_response(face) for face in person.face_images]
    
    return PersonDetailResponse(
        **base_response.model_dump(),
        face_images=face_images,
    )


@router.put("/{person_id}", response_model=PersonResponse)
async def update_person(
    person_id: int,
    person_data: PersonUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    """
    更新人员信息

    仅管理员可更新人员。

    Args:
        person_id: 人员 ID
        person_data: 更新数据

    Returns:
        PersonResponse: 更新后的人员信息

    Raises:
        HTTPException 404: 人员不存在
        HTTPException 400: 工号已存在
    """
    result = await db.execute(
        select(KnownPerson)
        .options(selectinload(KnownPerson.group), selectinload(KnownPerson.face_images))
        .where(KnownPerson.id == person_id)
    )
    person = result.scalar_one_or_none()

    if not person:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Person not found",
        )

    # 如果修改了工号，检查是否重复
    if person_data.employee_id and person_data.employee_id != person.employee_id:
        existing = await db.execute(
            select(KnownPerson).where(
                KnownPerson.employee_id == person_data.employee_id,
                KnownPerson.id != person_id
            )
        )
        if existing.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Employee ID already exists",
            )

    # 如果修改了分组，检查分组是否存在
    if person_data.group_id is not None and person_data.group_id != person.group_id:
        if person_data.group_id > 0:
            group_result = await db.execute(
                select(PersonGroup).where(PersonGroup.id == person_data.group_id)
            )
            if not group_result.scalar_one_or_none():
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Group not found",
                )

    # 更新字段
    if person_data.name is not None:
        person.name = person_data.name
    if person_data.employee_id is not None:
        person.employee_id = person_data.employee_id
    if person_data.group_id is not None:
        person.group_id = person_data.group_id if person_data.group_id > 0 else None
    if person_data.department is not None:
        person.department = person_data.department
    if person_data.phone is not None:
        person.phone = person_data.phone
    if person_data.remark is not None:
        person.remark = person_data.remark
    if person_data.is_active is not None:
        person.is_active = person_data.is_active

    await db.commit()
    
    # 重新查询
    result = await db.execute(
        select(KnownPerson)
        .options(selectinload(KnownPerson.group), selectinload(KnownPerson.face_images))
        .where(KnownPerson.id == person_id)
    )
    person = result.scalar_one()

    return build_person_response(person)


@router.patch("/{person_id}/status", response_model=PersonResponse)
async def update_person_status(
    person_id: int,
    status_data: PersonStatusUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    """
    更新人员状态（在职/离职）

    仅管理员可更新状态。

    Args:
        person_id: 人员 ID
        status_data: 状态更新数据

    Returns:
        PersonResponse: 更新后的人员信息

    Raises:
        HTTPException 404: 人员不存在
    """
    result = await db.execute(
        select(KnownPerson)
        .options(selectinload(KnownPerson.group), selectinload(KnownPerson.face_images))
        .where(KnownPerson.id == person_id)
    )
    person = result.scalar_one_or_none()

    if not person:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Person not found",
        )

    person.is_active = status_data.is_active
    await db.commit()
    await db.refresh(person)

    return build_person_response(person)


@router.delete("/{person_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_person(
    person_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    """
    删除人员

    仅管理员可删除人员。删除人员时会同时删除关联的人脸图片，
    并从视频分析引擎中移除特征。

    Args:
        person_id: 人员 ID

    Raises:
        HTTPException 404: 人员不存在
    """
    result = await db.execute(
        select(KnownPerson)
        .options(selectinload(KnownPerson.face_images))
        .where(KnownPerson.id == person_id)
    )
    person = result.scalar_one_or_none()

    if not person:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Person not found",
        )

    # 从引擎移除特征
    try:
        from app.services.face_feature import get_face_feature_service
        feature_service = get_face_feature_service()
        # CompreFace use name as subject
        await feature_service.remove_person(person.name)
    except Exception as e:
        import logging
        logging.getLogger(__name__).warning(f"从引擎移除人员失败: {e}")

    # 删除关联的人脸图片文件
    for face in person.face_images:
        if face.image_path and os.path.exists(face.image_path):
            try:
                os.remove(face.image_path)
            except Exception:
                pass  # 忽略文件删除错误

    await db.delete(person)
    await db.commit()

    return None


@router.post("/{person_id}/faces", response_model=FaceUploadResponse)
async def upload_face_image(
    person_id: int,
    file: UploadFile = File(..., description="人脸图片文件"),
    is_primary: bool = Query(False, description="是否设置为主图"),
    sync_to_engine: bool = Query(True, description="是否同步特征到引擎"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    """
    上传人脸图片

    仅管理员可上传人脸图片。支持 JPEG、PNG 格式，最大 5MB。
    上传成功后会自动提取人脸特征并同步到视频分析引擎。

    Args:
        person_id: 人员 ID
        file: 图片文件
        is_primary: 是否设置为主图
        sync_to_engine: 是否同步特征到引擎（默认 True）

    Returns:
        FaceUploadResponse: 上传成功的图片信息

    Raises:
        HTTPException 404: 人员不存在
        HTTPException 400: 文件格式或大小不符合要求
    """
    # 检查人员是否存在
    result = await db.execute(
        select(KnownPerson)
        .options(selectinload(KnownPerson.face_images), selectinload(KnownPerson.group))
        .where(KnownPerson.id == person_id)
    )
    person = result.scalar_one_or_none()

    if not person:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Person not found",
        )

    # 检查文件类型
    if file.content_type not in ALLOWED_IMAGE_TYPES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid file type. Allowed types: {', '.join(ALLOWED_IMAGE_TYPES)}",
        )

    # 读取文件内容
    content = await file.read()
    
    # 检查文件大小
    if len(content) > MAX_IMAGE_SIZE:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"File too large. Maximum size: {MAX_IMAGE_SIZE // 1024 // 1024}MB",
        )

    # 提取人脸特征（验证图片有效性）
    has_face = False
    
    try:
        from app.services.face_feature import get_face_feature_service
        feature_service = get_face_feature_service()
        # 验证是否有人脸
        has_face = await feature_service.validate_face(content)
        
        if not has_face:
            import logging
            logging.getLogger(__name__).warning(f"图片中未检测到人脸: person_id={person_id}")
    except Exception as e:
        import logging
        logging.getLogger(__name__).warning(f"人脸检测失败: {e}")

    # 生成文件名和路径
    file_ext = os.path.splitext(file.filename)[1] if file.filename else ".jpg"
    file_name = f"{person_id}_{uuid.uuid4().hex}{file_ext}"
    
    # 确保目录存在
    faces_dir = getattr(settings, 'FACES_DIR', './data/faces')
    os.makedirs(faces_dir, exist_ok=True)
    
    file_path = os.path.join(faces_dir, file_name)

    # 保存文件
    with open(file_path, "wb") as f:
        f.write(content)

    # 如果设置为主图，先取消其他主图
    if is_primary:
        for face in person.face_images:
            if face.is_primary:
                face.is_primary = False

    # 如果是第一张图片，自动设为主图
    if not person.face_images:
        is_primary = True

    # 计算质量分数
    quality_score = 0.8 if has_face else 0.3

    # 创建数据库记录
    new_face = FaceImage(
        person_id=person_id,
        image_path=file_path,
        is_primary=is_primary,
        quality_score=quality_score,
    )

    db.add(new_face)
    await db.commit()
    await db.refresh(new_face)

    # 同步人员到引擎
    image_id_from_engine = None
    if sync_to_engine and has_face:
        try:
            # 添加到 CompreFace (Subject = Person Name)
            # add_person_face 返回 (success, image_id)
            success, image_id_from_engine = await feature_service.add_person_face(person.name, content)
            
            if success and image_id_from_engine:
                 # 更新数据库中的 image_id
                 new_face.image_id = image_id_from_engine
                 await db.commit()
                 await db.refresh(new_face)
            
        except Exception as e:
            import logging
            logging.getLogger(__name__).warning(f"同步特征到引擎失败: {e}")

    return FaceUploadResponse(
        id=new_face.id,
        image_path=new_face.image_path,
        image_id=new_face.image_id,
        image_url=f"/static/faces/{file_name}",
        quality_score=new_face.quality_score,
        is_primary=new_face.is_primary,
        created_at=new_face.created_at,
        feature_extracted=feature_extracted,
    )


@router.delete("/{person_id}/faces/{face_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_face_image(
    person_id: int,
    face_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    """
    删除人脸图片

    仅管理员可删除人脸图片。

    Args:
        person_id: 人员 ID
        face_id: 人脸图片 ID

    Raises:
        HTTPException 404: 人员或图片不存在
    """
    # 检查人员是否存在
    person_result = await db.execute(
        select(KnownPerson).where(KnownPerson.id == person_id)
    )
    if not person_result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Person not found",
        )

    # 检查图片是否存在
    face_result = await db.execute(
        select(FaceImage).where(
            FaceImage.id == face_id,
            FaceImage.person_id == person_id
        )
    )
    face = face_result.scalar_one_or_none()

    if not face:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Face image not found",
        )

    # 删除文件
    if face.image_path and os.path.exists(face.image_path):
        try:
            os.remove(face.image_path)
        except Exception:
            pass
            
    # 从引擎移除特征 (如果存在 image_id)
    if face.image_id:
        try:
            from app.services.face_feature import get_face_feature_service
            feature_service = get_face_feature_service()
            await feature_service.remove_face_image(face.image_id)
        except Exception as e:
            import logging
            logging.getLogger(__name__).warning(f"从引擎移除人脸图片失败: {e}")

    # 删除数据库记录
    await db.delete(face)
    await db.commit()

    return None


@router.patch("/{person_id}/faces/{face_id}/primary", response_model=FaceImageResponse)
async def set_primary_face(
    person_id: int,
    face_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    """
    设置主图

    将指定的人脸图片设置为主图。

    Args:
        person_id: 人员 ID
        face_id: 人脸图片 ID

    Returns:
        FaceImageResponse: 设置为主图的图片信息

    Raises:
        HTTPException 404: 人员或图片不存在
    """
    # 检查人员是否存在
    person_result = await db.execute(
        select(KnownPerson)
        .options(selectinload(KnownPerson.face_images))
        .where(KnownPerson.id == person_id)
    )
    person = person_result.scalar_one_or_none()

    if not person:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Person not found",
        )

    # 查找目标图片
    target_face = None
    for face in person.face_images:
        if face.id == face_id:
            target_face = face
        else:
            face.is_primary = False  # 取消其他主图

    if not target_face:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Face image not found",
        )

    target_face.is_primary = True
    await db.commit()
    await db.refresh(target_face)

    return build_face_image_response(target_face)


@router.post("/import", response_model=PersonImportResult)
async def import_persons(
    import_data: PersonImportRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    """
    批量导入人员

    仅管理员可批量导入。单次最多导入 100 条。

    Args:
        import_data: 导入数据

    Returns:
        PersonImportResult: 导入结果
    """
    success_count = 0
    failed_count = 0
    failed_items = []

    for idx, item in enumerate(import_data.items):
        try:
            # 检查工号是否已存在
            if item.employee_id:
                existing = await db.execute(
                    select(KnownPerson).where(KnownPerson.employee_id == item.employee_id)
                )
                if existing.scalar_one_or_none():
                    raise ValueError(f"Employee ID '{item.employee_id}' already exists")

            # 检查分组是否存在
            if item.group_id:
                group_result = await db.execute(
                    select(PersonGroup).where(PersonGroup.id == item.group_id)
                )
                if not group_result.scalar_one_or_none():
                    raise ValueError(f"Group ID '{item.group_id}' not found")

            # 创建人员
            new_person = KnownPerson(
                name=item.name,
                employee_id=item.employee_id,
                group_id=item.group_id,
                department=item.department,
                phone=item.phone,
                remark=item.remark,
                is_active=True,
            )
            db.add(new_person)
            success_count += 1

        except Exception as e:
            failed_count += 1
            failed_items.append({
                "index": idx,
                "name": item.name,
                "error": str(e),
            })

    # 提交成功的记录
    if success_count > 0:
        await db.commit()

    return PersonImportResult(
        success_count=success_count,
        failed_count=failed_count,
        failed_items=failed_items,
    )


@router.post("/sync-to-engine")
async def sync_all_persons_to_engine(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    """
    批量同步所有人员特征到引擎

    从数据库加载所有有人脸图片的人员，提取特征并同步到视频分析引擎。
    适用于引擎重启后重建人脸库。

    Returns:
        dict: 同步结果统计

    Raises:
        HTTPException 503: 引擎不可用
    """
    import logging
    logger = logging.getLogger(__name__)
    
    # 获取特征服务
    try:
        from app.services.face_feature import get_face_feature_service
        feature_service = get_face_feature_service()
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"特征服务不可用: {e}",
        )
    
    # 查询所有有人脸图片的人员
    result = await db.execute(
        select(KnownPerson)
        .options(selectinload(KnownPerson.group), selectinload(KnownPerson.face_images))
        .where(KnownPerson.is_active == True)
    )
    persons = result.scalars().all()
    
    success_count = 0
    failed_count = 0
    skipped_count = 0
    total_embeddings = 0
    
    for person in persons:
        if not person.face_images:
            skipped_count += 1
            continue
        
        try:
            # 提取该人员所有人脸的特征
            embeddings = []
            for face in person.face_images:
                if face.image_path and os.path.exists(face.image_path):
                    embedding = feature_service.extract_embedding_from_file(face.image_path)
                    if embedding is not None:
                        embeddings.append(embedding)
            
            if not embeddings:
                logger.warning(f"人员 {person.name} (ID: {person.id}) 没有有效的人脸特征")
                skipped_count += 1
                continue
            
            # 同步到引擎
            group_name = person.group.name if person.group else None
            success = feature_service.sync_person_to_engine(
                person_id=person.id,
                name=person.name,
                embeddings=embeddings,
                group_id=person.group_id,
                group_name=group_name
            )
            
            if success:
                success_count += 1
                total_embeddings += len(embeddings)
            else:
                failed_count += 1
                
        except Exception as e:
            logger.error(f"同步人员 {person.name} 失败: {e}")
            failed_count += 1
    
    # 获取数据库统计
    db_stats = feature_service.get_database_stats()
    
    return {
        "success": True,
        "message": f"同步完成: {success_count} 成功, {failed_count} 失败, {skipped_count} 跳过",
        "details": {
            "total_persons": len(persons),
            "success_count": success_count,
            "failed_count": failed_count,
            "skipped_count": skipped_count,
            "total_embeddings": total_embeddings,
        },
        "database_stats": db_stats,
    }


@router.post("/{person_id}/sync-to-engine")
async def sync_person_to_engine(
    person_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    """
    同步单个人员特征到引擎

    Args:
        person_id: 人员 ID

    Returns:
        dict: 同步结果

    Raises:
        HTTPException 404: 人员不存在
        HTTPException 400: 没有有效的人脸图片
    """
    # 查询人员
    result = await db.execute(
        select(KnownPerson)
        .options(selectinload(KnownPerson.group), selectinload(KnownPerson.face_images))
        .where(KnownPerson.id == person_id)
    )
    person = result.scalar_one_or_none()

    if not person:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Person not found",
        )

    if not person.face_images:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="该人员没有人脸图片",
        )

    # 获取特征服务
    try:
        from app.services.face_feature import get_face_feature_service
        feature_service = get_face_feature_service()
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"特征服务不可用: {e}",
        )

    # 提取所有人脸的特征
    embeddings = []
    for face in person.face_images:
        if face.image_path and os.path.exists(face.image_path):
            embedding = feature_service.extract_embedding_from_file(face.image_path)
            if embedding is not None:
                embeddings.append(embedding)

    if not embeddings:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="没有检测到有效的人脸图片",
        )

    # 同步到引擎
    group_name = person.group.name if person.group else None
    success = feature_service.sync_person_to_engine(
        person_id=person.id,
        name=person.name,
        embeddings=embeddings,
        group_id=person.group_id,
        group_name=group_name
    )

    if success:
        return {
            "success": True,
            "message": f"人员 {person.name} 特征已同步到引擎",
            "person_id": person.id,
            "embedding_count": len(embeddings),
        }
    else:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="同步失败",
        )


@router.get("/engine-database/stats")
async def get_engine_database_stats(
    current_user: User = Depends(get_current_active_user),
):
    """
    获取引擎人脸数据库统计信息

    Returns:
        dict: 数据库统计信息
    """
    try:
        from app.services.face_feature import get_face_feature_service
        feature_service = get_face_feature_service()
        return feature_service.get_database_stats()
    except Exception as e:
        return {
            "available": False,
            "message": str(e)
        }
