import asyncio
import logging
import requests
from typing import Optional, Dict, Any, List
from functools import partial

from app.core.config import settings

logger = logging.getLogger(__name__)

class CompreFaceClient:
    """
    CompreFace API 客户端
    
    支持并发控制、重试机制和异常处理。
    """
    
    def __init__(self):
        self.base_url = settings.COMPREFACE_URL
        self.api_key = settings.COMPREFACE_API_KEY
        self.timeout = 10.0 # 秒
        
        # 并发控制信号量
        # 注意: 这是一个全局信号量，应该在事件循环中获取，或者在 process 中独立管理
        # 这里初始化为 None，在 start 时创建
        self._semaphore: Optional[asyncio.Semaphore] = None
        self._concurrent_limit = settings.CONCURRENT_LIMIT_DEFAULT
        
    async def start(self):
        """初始化资源"""
        self._semaphore = asyncio.Semaphore(self._concurrent_limit)
        logger.info(f"CompreFaceClient 初始化完成, 并发限制: {self._concurrent_limit}")

    def update_limit(self, limit: int):
        """动态更新并发限制"""
        if limit > 0:
            self._concurrent_limit = limit
            # 重新创建信号量 (注意: 这可能会影响当前排队的任务，简化处理)
            self._semaphore = asyncio.Semaphore(limit)
            logger.info(f"CompreFaceClient 并发限制更新为: {limit}")

    async def _request(self, method: str, endpoint: str, **kwargs) -> Optional[Dict[str, Any]]:
        """
        发送请求 (带并发控制和线程池执行)
        """
        if self._semaphore is None:
            await self.start()
            
        async with self._semaphore:
            # CompreFace 是同步 HTTP 服务，使用 requests 库
            # 为了不阻塞 asyncio 循环，在 ThreadPool 中运行
            loop = asyncio.get_event_loop()
            
            url = f"{self.base_url}{endpoint}"
            headers = kwargs.pop("headers", {})
            headers["x-api-key"] = self.api_key
            
            func = partial(requests.request, method, url, headers=headers, timeout=self.timeout, **kwargs)
            
            try:
                response = await loop.run_in_executor(None, func)
                response.raise_for_status()
                return response.json()
            except requests.exceptions.RequestException as e:
                logger.error(f"CompreFace API 请求失败 [{endpoint}]: {e}")
                return None
            except Exception as e:
                logger.error(f"CompreFace 客户端未知错误: {e}")
                return None

    async def recognize_face(self, image_data: bytes) -> Optional[Dict[str, Any]]:
        """
        人脸识别
        
        Args:
            image_data: 图片字节数据 (JPEG/PNG)
            
        Returns:
            识别结果字典 或 None
        """
        files = {'file': ('image.jpg', image_data, 'image/jpeg')}
        
        # 重试逻辑 (简单 2 次重试)
        for attempt in range(2):
            result = await self._request("POST", "/api/v1/recognition/recognize", files=files)
            if result:
                return result
            # 失败后简短等待
            if attempt == 0:
                await asyncio.sleep(0.5)
                
        return None

    async def add_subject(self, image_data: bytes, subject: str) -> tuple[bool, Optional[str]]:
        """
        添加人脸到库
        
        Returns:
            (success, image_id)
        """
        files = {'file': ('image.jpg', image_data, 'image/jpeg')}
        data = {'subject': subject}
        
        result = await self._request("POST", "/api/v1/recognition/faces", files=files, data=data)
        if result and 'image_id' in result:
            logger.info(f"成功添加人脸: {subject}, image_id={result['image_id']}")
            return True, result['image_id']
        return False, None

    async def delete_subject(self, subject: str) -> bool:
        """删除人员的所有人脸 (按名称)"""
        result = await self._request("DELETE", f"/api/v1/recognition/faces", params={'subject': subject})
        return result is not None

    async def delete_image_by_id(self, image_id: str) -> bool:
        """删除特定人脸 (按 image_id)"""
        result = await self._request("DELETE", f"/api/v1/recognition/faces/{image_id}")
        return result is not None

    async def delete_image_by_id(self, image_id: str) -> bool:
        """删除指定的人脸图片"""
        result = await self._request("DELETE", f"/api/v1/recognition/faces/{image_id}")
        return result is not None

# 全局单例
compreface_client = CompreFaceClient()
