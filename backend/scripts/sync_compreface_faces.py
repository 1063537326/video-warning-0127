"""
CompreFace 人脸数据同步脚本

从 CompreFace 拉取所有已注册 subject 的人脸图片，
同步到本地 face_images 表和 data/faces/ 目录。

用法：
    cd backend
    .\venv\Scripts\python.exe scripts/sync_compreface_faces.py

功能：
    1. 查询 CompreFace 中所有 subject（对应 known_persons.name）
    2. 对每个 subject，下载其所有人脸图片
    3. 保存图片到 data/faces/ 目录
    4. 在 face_images 表中创建记录（第一张设为主图）
    5. 跳过已有 face_images 记录的人员
"""
import os
import sys
import asyncio
import logging
import requests

# 将 backend 目录加入 sys.path，使 app 包可被导入
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import select
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import selectinload, sessionmaker

from app.core.config import settings
from app.models.person import KnownPerson, FaceImage

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

# CompreFace API 配置
COMPREFACE_URL = settings.COMPREFACE_URL
COMPREFACE_API_KEY = settings.COMPREFACE_API_KEY
FACES_DIR = getattr(settings, 'FACES_DIR', './data/faces')


def get_subjects() -> list[str]:
    """
    获取 CompreFace 中所有已注册的 subject（人名）列表。

    Returns:
        subject 名称列表
    """
    url = f"{COMPREFACE_URL}/api/v1/recognition/subjects"
    headers = {"x-api-key": COMPREFACE_API_KEY}
    try:
        resp = requests.get(url, headers=headers, timeout=10)
        resp.raise_for_status()
        data = resp.json()
        return data.get("subjects", [])
    except Exception as e:
        logger.error(f"获取 subject 列表失败: {e}")
        return []


def get_subject_faces(subject: str) -> list[dict]:
    """
    获取指定 subject 在 CompreFace 中的所有人脸记录。

    Args:
        subject: CompreFace 中的 subject 名称

    Returns:
        包含 image_id 等信息的人脸记录列表
    """
    url = f"{COMPREFACE_URL}/api/v1/recognition/faces"
    headers = {"x-api-key": COMPREFACE_API_KEY}
    params = {"subject": subject}
    try:
        resp = requests.get(url, headers=headers, params=params, timeout=10)
        resp.raise_for_status()
        data = resp.json()
        return data.get("faces", [])
    except Exception as e:
        logger.error(f"获取 {subject} 的人脸列表失败: {e}")
        return []


def download_face_image(image_id: str) -> bytes | None:
    """
    从 CompreFace 下载指定 image_id 的人脸图片。

    Args:
        image_id: CompreFace 中的图片 ID

    Returns:
        图片字节数据，失败返回 None
    """
    url = f"{COMPREFACE_URL}/api/v1/recognition/faces/{image_id}/img"
    headers = {"x-api-key": COMPREFACE_API_KEY}
    try:
        resp = requests.get(url, headers=headers, timeout=15)
        resp.raise_for_status()
        return resp.content
    except Exception as e:
        logger.error(f"下载图片 {image_id} 失败: {e}")
        return None


async def sync_faces():
    """
    主同步逻辑。

    遍历 CompreFace 中的所有 subject，匹配本地 known_persons 表，
    下载人脸图片并创建 face_images 记录。
    """
    # 创建数据库连接
    engine = create_async_engine(settings.DATABASE_URL)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    # 确保 faces 目录存在
    os.makedirs(FACES_DIR, exist_ok=True)

    # 获取 CompreFace 所有 subject
    subjects = get_subjects()
    logger.info(f"CompreFace 中共有 {len(subjects)} 个 subject")

    if not subjects:
        logger.warning("CompreFace 中没有 subject，退出")
        return

    async with async_session() as session:
        # 查询所有本地人员（预加载 face_images）
        result = await session.execute(
            select(KnownPerson).options(selectinload(KnownPerson.face_images))
        )
        persons = result.scalars().all()

        # 构建 name -> person 映射
        person_map = {p.name: p for p in persons}
        logger.info(f"本地数据库中共有 {len(persons)} 个人员")

        synced_count = 0
        skipped_count = 0
        error_count = 0

        for subject in subjects:
            person = person_map.get(subject)
            if not person:
                logger.warning(f"  跳过 subject '{subject}': 本地数据库中无匹配人员")
                skipped_count += 1
                continue

            # 如果该人员已有 face_images 记录，跳过
            if person.face_images and len(person.face_images) > 0:
                logger.info(f"  跳过 '{subject}': 已有 {len(person.face_images)} 张人脸图片")
                skipped_count += 1
                continue

            # 获取 CompreFace 中的人脸列表
            faces = get_subject_faces(subject)
            if not faces:
                logger.warning(f"  '{subject}' 在 CompreFace 中没有人脸数据")
                continue

            logger.info(f"  正在同步 '{subject}': {len(faces)} 张图片")

            for idx, face_info in enumerate(faces):
                image_id = face_info.get("image_id")
                if not image_id:
                    continue

                # 下载图片
                image_data = download_face_image(image_id)
                if not image_data:
                    error_count += 1
                    continue

                # 保存到本地文件
                file_name = f"{person.id}_{image_id}.jpg"
                file_path = os.path.join(FACES_DIR, file_name)

                with open(file_path, "wb") as f:
                    f.write(image_data)

                # 创建数据库记录（第一张设为主图）
                is_primary = (idx == 0)
                new_face = FaceImage(
                    person_id=person.id,
                    image_path=file_path,
                    image_id=image_id,
                    is_primary=is_primary,
                    quality_score=0.8,
                )
                session.add(new_face)

                logger.info(f"    保存图片: {file_name} (主图={is_primary})")

            synced_count += 1

        await session.commit()

    logger.info("=" * 50)
    logger.info(f"同步完成: 成功={synced_count}, 跳过={skipped_count}, 错误={error_count}")
    logger.info("=" * 50)

    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(sync_faces())
