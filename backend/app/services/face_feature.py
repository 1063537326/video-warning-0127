"""
人脸特征服务模块（CompreFace 适配版）

功能：
- 人脸检测（验证图片可用性）
- 人脸注册到 CompreFace 引擎
- 人脸删除
"""
import logging
from typing import Optional

from app.engine.recognition.client import compreface_client

logger = logging.getLogger(__name__)

class FaceFeatureService:
    """人脸特征服务（通过 CompreFace REST API 实现）"""
    
    async def validate_face(self, image_bytes: bytes) -> bool:
        """
        验证图片中是否包含人脸

        Args:
            image_bytes: 图片字节数据

        Returns:
            是否检测到人脸
        """
        try:
            result = await compreface_client.recognize_face(image_bytes)
            if result and 'result' in result:
                return len(result['result']) > 0
            return False
        except Exception as e:
            logger.error(f"人脸检测验证失败: {e}")
            return False

    async def add_person_face(self, name: str, image_bytes: bytes) -> tuple[bool, Optional[str]]:
        """
        添加人脸到 CompreFace

        Args:
            name: 人员姓名（作为 Subject）
            image_bytes: 图片数据

        Returns:
            (是否成功, CompreFace 返回的图片 ID)
        """
        return await compreface_client.add_subject(image_bytes, name)

    async def remove_person(self, name: str) -> bool:
        """
        从 CompreFace 移除人员（删除该人员所有图片）

        Args:
            name: 人员姓名
        """
        return await compreface_client.delete_subject(name)

    async def remove_face_image(self, image_id: str) -> bool:
        """
        移除指定的人脸图片

        Args:
            image_id: CompreFace 返回的图片 ID
        """
        return await compreface_client.delete_image_by_id(image_id)


# 全局服务实例
_face_feature_service: Optional[FaceFeatureService] = None

def get_face_feature_service() -> FaceFeatureService:
    """获取人脸特征服务单例"""
    global _face_feature_service
    if _face_feature_service is None:
        _face_feature_service = FaceFeatureService()
    return _face_feature_service

