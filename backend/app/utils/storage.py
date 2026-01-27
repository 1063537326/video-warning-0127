"""
文件存储工具
- 图片保存
- 路径生成
- 文件删除
"""
import os
import uuid
from datetime import datetime
from pathlib import Path

from app.core.config import settings


def get_capture_path(date: datetime = None) -> Path:
    """获取截图存储路径（按日期分目录）"""
    if date is None:
        date = datetime.now()
    path = Path(settings.CAPTURES_DIR) / date.strftime("%Y/%m/%d")
    path.mkdir(parents=True, exist_ok=True)
    return path


def get_face_path(person_id: int) -> Path:
    """获取人脸图片存储路径（按人员ID分目录）"""
    path = Path(settings.FACES_DIR) / str(person_id)
    path.mkdir(parents=True, exist_ok=True)
    return path


def generate_filename(extension: str = "jpg") -> str:
    """生成唯一文件名"""
    return f"{uuid.uuid4().hex}.{extension}"


def save_image(image_bytes: bytes, path: Path, filename: str = None) -> str:
    """保存图片并返回相对路径"""
    if filename is None:
        filename = generate_filename()
    
    filepath = path / filename
    with open(filepath, "wb") as f:
        f.write(image_bytes)
    
    # 返回相对于 data 目录的路径
    return str(filepath.relative_to(settings.DATA_DIR))
