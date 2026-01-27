"""
人脸识别服务模块

功能：
- 整合人脸检测与特征比对
- 提供完整的人脸识别流程
- 管理识别结果与报警冷却
"""
import logging
import time
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, field
from datetime import datetime

import numpy as np

from .face_detector import FaceDetector, FaceInfo, DetectorConfig
from .face_database import FaceDatabase, MatchResult

logger = logging.getLogger(__name__)


@dataclass
class RecognitionResult:
    """识别结果"""
    face_info: FaceInfo                     # 人脸检测信息
    match_result: MatchResult               # 匹配结果
    camera_id: int                          # 摄像头 ID
    timestamp: datetime                     # 时间戳
    should_alert: bool = False              # 是否应该报警
    alert_type: str = "stranger"            # 报警类型：stranger, known, blacklist
    
    def to_dict(self) -> dict:
        """转换为字典"""
        return {
            "face": self.face_info.to_dict(),
            "match": self.match_result.to_dict(),
            "camera_id": self.camera_id,
            "timestamp": self.timestamp.isoformat(),
            "should_alert": self.should_alert,
            "alert_type": self.alert_type,
        }


@dataclass
class RecognizerConfig:
    """识别器配置"""
    # 检测器配置
    detector_config: DetectorConfig = field(default_factory=DetectorConfig)
    
    # 识别配置
    similarity_threshold: float = 0.6       # 识别阈值
    
    # 报警配置
    alert_on_stranger: bool = True          # 陌生人是否报警
    alert_cooldown: float = 60.0            # 报警冷却时间（秒）
    
    # 黑名单配置
    blacklist_group_ids: List[int] = field(default_factory=list)  # 黑名单分组 ID


class AlertCooldownManager:
    """
    报警冷却管理器
    
    防止同一人员在短时间内重复报警
    """
    
    def __init__(self, cooldown_seconds: float = 60.0):
        """
        初始化冷却管理器
        
        Args:
            cooldown_seconds: 冷却时间（秒）
        """
        self.cooldown_seconds = cooldown_seconds
        # key: (camera_id, person_id 或 "stranger"), value: 上次报警时间
        self._last_alert_time: Dict[Tuple[int, str], float] = {}
    
    def can_alert(self, camera_id: int, person_id: Optional[int]) -> bool:
        """
        检查是否可以报警
        
        Args:
            camera_id: 摄像头 ID
            person_id: 人员 ID，陌生人为 None
            
        Returns:
            是否可以报警
        """
        key = (camera_id, str(person_id) if person_id else "stranger")
        current_time = time.time()
        
        last_time = self._last_alert_time.get(key, 0)
        if current_time - last_time < self.cooldown_seconds:
            return False
        
        return True
    
    def record_alert(self, camera_id: int, person_id: Optional[int]) -> None:
        """
        记录报警时间
        
        Args:
            camera_id: 摄像头 ID
            person_id: 人员 ID
        """
        key = (camera_id, str(person_id) if person_id else "stranger")
        self._last_alert_time[key] = time.time()
    
    def clear(self) -> None:
        """清空记录"""
        self._last_alert_time.clear()
    
    def cleanup_expired(self) -> int:
        """
        清理过期的记录
        
        Returns:
            清理的记录数
        """
        current_time = time.time()
        expired_keys = [
            key for key, last_time in self._last_alert_time.items()
            if current_time - last_time > self.cooldown_seconds * 2
        ]
        
        for key in expired_keys:
            del self._last_alert_time[key]
        
        return len(expired_keys)


class FaceRecognizer:
    """
    人脸识别服务
    
    整合人脸检测、特征提取、人脸库比对的完整识别流程
    
    使用示例：
        config = RecognizerConfig(similarity_threshold=0.6)
        recognizer = FaceRecognizer(config)
        recognizer.load_model()
        
        # 加载人脸库
        recognizer.load_person(person_id=1, name="张三", embeddings=[...])
        
        # 识别
        results = recognizer.recognize(image, camera_id=1)
        for result in results:
            if result.should_alert:
                send_alert(result)
    """
    
    def __init__(self, config: Optional[RecognizerConfig] = None):
        """
        初始化识别器
        
        Args:
            config: 识别器配置
        """
        self.config = config or RecognizerConfig()
        
        # 人脸检测器
        self._detector = FaceDetector(self.config.detector_config)
        
        # 人脸特征数据库
        self._database = FaceDatabase(self.config.similarity_threshold)
        
        # 报警冷却管理
        self._cooldown_manager = AlertCooldownManager(self.config.alert_cooldown)
        
        # 状态
        self._is_loaded = False
    
    @property
    def is_loaded(self) -> bool:
        """模型是否已加载"""
        return self._is_loaded
    
    @property
    def database(self) -> FaceDatabase:
        """获取人脸数据库"""
        return self._database
    
    def load_model(self) -> bool:
        """
        加载模型
        
        Returns:
            是否加载成功
        """
        if self._is_loaded:
            return True
        
        success = self._detector.load_model()
        self._is_loaded = success
        return success
    
    def unload_model(self) -> None:
        """卸载模型"""
        self._detector.unload_model()
        self._is_loaded = False
    
    def load_person(
        self,
        person_id: int,
        name: str,
        embeddings: List[np.ndarray],
        group_id: Optional[int] = None,
        group_name: Optional[str] = None
    ) -> bool:
        """
        加载人员到人脸库
        
        Args:
            person_id: 人员 ID
            name: 姓名
            embeddings: 特征向量列表
            group_id: 分组 ID
            group_name: 分组名称
            
        Returns:
            是否加载成功
        """
        return self._database.add_person(
            person_id=person_id,
            name=name,
            embeddings=embeddings,
            group_id=group_id,
            group_name=group_name
        )
    
    def remove_person(self, person_id: int) -> bool:
        """
        从人脸库移除人员
        
        Args:
            person_id: 人员 ID
            
        Returns:
            是否移除成功
        """
        return self._database.remove_person(person_id)
    
    def clear_database(self) -> None:
        """清空人脸库"""
        self._database.clear()
    
    def extract_embedding(self, image: np.ndarray) -> Optional[np.ndarray]:
        """
        从图像提取人脸特征向量
        
        用于注册新人员时提取照片的特征
        
        Args:
            image: BGR 格式图像
            
        Returns:
            特征向量，提取失败返回 None
        """
        if not self._is_loaded:
            raise RuntimeError("模型未加载")
        
        face = self._detector.detect_largest(image, extract_embedding=True)
        if face is None or face.embedding is None:
            return None
        
        return face.embedding
    
    def _determine_alert_type(self, match_result: MatchResult) -> Tuple[bool, str]:
        """
        判断报警类型
        
        Args:
            match_result: 匹配结果
            
        Returns:
            (是否报警, 报警类型)
        """
        # 陌生人
        if match_result.is_stranger:
            return self.config.alert_on_stranger, "stranger"
        
        # 黑名单
        if match_result.group_id in self.config.blacklist_group_ids:
            return True, "blacklist"
        
        # 已知人员（不报警）
        return False, "known"
    
    def recognize(
        self,
        image: np.ndarray,
        camera_id: int,
        check_cooldown: bool = True
    ) -> List[RecognitionResult]:
        """
        识别图像中的人脸
        
        Args:
            image: BGR 格式图像
            camera_id: 摄像头 ID
            check_cooldown: 是否检查报警冷却
            
        Returns:
            识别结果列表
        """
        if not self._is_loaded:
            raise RuntimeError("模型未加载")
        
        results = []
        timestamp = datetime.now()
        
        # 检测人脸
        faces = self._detector.detect(image, extract_embedding=True, crop_face=True)
        
        for face in faces:
            if face.embedding is None:
                continue
            
            # 人脸比对
            match_result = self._database.recognize(face.embedding)
            
            # 判断报警类型
            should_alert, alert_type = self._determine_alert_type(match_result)
            
            # 检查冷却
            if should_alert and check_cooldown:
                person_id = None if match_result.is_stranger else match_result.person_id
                if not self._cooldown_manager.can_alert(camera_id, person_id):
                    should_alert = False
                else:
                    # 记录报警
                    self._cooldown_manager.record_alert(camera_id, person_id)
            
            # 构建结果
            result = RecognitionResult(
                face_info=face,
                match_result=match_result,
                camera_id=camera_id,
                timestamp=timestamp,
                should_alert=should_alert,
                alert_type=alert_type
            )
            results.append(result)
        
        return results
    
    def get_stats(self) -> dict:
        """
        获取统计信息
        
        Returns:
            统计信息字典
        """
        return {
            "is_loaded": self._is_loaded,
            "database": self._database.get_stats(),
            "config": {
                "similarity_threshold": self.config.similarity_threshold,
                "alert_on_stranger": self.config.alert_on_stranger,
                "alert_cooldown": self.config.alert_cooldown,
            }
        }
