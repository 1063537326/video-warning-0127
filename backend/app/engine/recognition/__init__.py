"""
人脸识别模块

提供 CompreFace 远程人脸识别功能：
- CompreFace REST API 客户端
- 人脸注册与删除
- 人脸识别与比对
"""
from .client import CompreFaceClient, compreface_client

__all__ = [
    "CompreFaceClient",
    "compreface_client",
]
