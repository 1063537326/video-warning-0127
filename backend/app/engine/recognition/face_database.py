"""
人脸特征数据库模块

功能：
- 管理已知人员的人脸特征向量
- 提供高效的特征比对
- 支持动态添加/删除人员
"""
import logging
import threading
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime

import numpy as np

logger = logging.getLogger(__name__)


@dataclass
class PersonFeature:
    """人员特征信息"""
    person_id: int                      # 人员 ID
    name: str                           # 姓名
    group_id: Optional[int] = None      # 分组 ID
    group_name: Optional[str] = None    # 分组名称
    embeddings: List[np.ndarray] = None  # 特征向量列表（一个人可能有多张照片）
    created_at: datetime = None
    
    def __post_init__(self):
        if self.embeddings is None:
            self.embeddings = []
        if self.created_at is None:
            self.created_at = datetime.now()


@dataclass  
class MatchResult:
    """匹配结果"""
    person_id: int                      # 匹配的人员 ID
    name: str                           # 姓名
    group_id: Optional[int]             # 分组 ID
    group_name: Optional[str]           # 分组名称
    similarity: float                   # 相似度 (0-1)
    is_stranger: bool = False           # 是否为陌生人
    
    def to_dict(self) -> dict:
        """转换为字典"""
        return {
            "person_id": self.person_id,
            "name": self.name,
            "group_id": self.group_id,
            "group_name": self.group_name,
            "similarity": round(self.similarity, 4),
            "is_stranger": self.is_stranger,
        }


class FaceDatabase:
    """
    人脸特征数据库
    
    功能：
    - 存储和管理已知人员的人脸特征
    - 提供高效的特征比对（余弦相似度）
    - 线程安全的读写操作
    - 支持批量操作
    
    使用示例：
        db = FaceDatabase(similarity_threshold=0.6)
        
        # 添加人员
        db.add_person(person_id=1, name="张三", embeddings=[embedding1, embedding2])
        
        # 识别人脸
        result = db.recognize(query_embedding)
        if result.is_stranger:
            print("陌生人！")
        else:
            print(f"识别为: {result.name}, 相似度: {result.similarity}")
    """
    
    def __init__(self, similarity_threshold: float = 0.6):
        """
        初始化人脸数据库
        
        Args:
            similarity_threshold: 识别阈值，相似度低于此值判定为陌生人
        """
        self.similarity_threshold = similarity_threshold
        
        # 人员特征存储
        self._persons: Dict[int, PersonFeature] = {}
        
        # 预计算的特征矩阵（用于批量比对）
        self._feature_matrix: Optional[np.ndarray] = None
        self._feature_ids: List[int] = []  # 特征对应的 person_id
        
        # 线程锁
        self._lock = threading.RLock()
        
        # 统计信息
        self._total_embeddings = 0
    
    @property
    def person_count(self) -> int:
        """人员数量"""
        return len(self._persons)
    
    @property
    def embedding_count(self) -> int:
        """特征向量总数"""
        return self._total_embeddings
    
    def _rebuild_feature_matrix(self) -> None:
        """重建特征矩阵（内部方法）"""
        embeddings = []
        self._feature_ids = []
        
        for person_id, person in self._persons.items():
            for emb in person.embeddings:
                embeddings.append(emb)
                self._feature_ids.append(person_id)
        
        if embeddings:
            self._feature_matrix = np.vstack(embeddings)
            # L2 归一化（用于余弦相似度计算）
            norms = np.linalg.norm(self._feature_matrix, axis=1, keepdims=True)
            self._feature_matrix = self._feature_matrix / np.clip(norms, 1e-10, None)
        else:
            self._feature_matrix = None
        
        self._total_embeddings = len(embeddings)
    
    def add_person(
        self,
        person_id: int,
        name: str,
        embeddings: List[np.ndarray],
        group_id: Optional[int] = None,
        group_name: Optional[str] = None
    ) -> bool:
        """
        添加人员到数据库
        
        Args:
            person_id: 人员 ID
            name: 姓名
            embeddings: 特征向量列表
            group_id: 分组 ID
            group_name: 分组名称
            
        Returns:
            是否添加成功
        """
        if not embeddings:
            logger.warning(f"人员 {person_id} 没有特征向量，跳过")
            return False
        
        with self._lock:
            self._persons[person_id] = PersonFeature(
                person_id=person_id,
                name=name,
                group_id=group_id,
                group_name=group_name,
                embeddings=embeddings
            )
            self._rebuild_feature_matrix()
            logger.debug(f"已添加人员: {name} (ID: {person_id}, 特征数: {len(embeddings)})")
            return True
    
    def remove_person(self, person_id: int) -> bool:
        """
        从数据库移除人员
        
        Args:
            person_id: 人员 ID
            
        Returns:
            是否移除成功
        """
        with self._lock:
            if person_id not in self._persons:
                return False
            
            person = self._persons.pop(person_id)
            self._rebuild_feature_matrix()
            logger.debug(f"已移除人员: {person.name} (ID: {person_id})")
            return True
    
    def update_person_embeddings(
        self,
        person_id: int,
        embeddings: List[np.ndarray]
    ) -> bool:
        """
        更新人员的特征向量
        
        Args:
            person_id: 人员 ID
            embeddings: 新的特征向量列表
            
        Returns:
            是否更新成功
        """
        with self._lock:
            if person_id not in self._persons:
                return False
            
            self._persons[person_id].embeddings = embeddings
            self._rebuild_feature_matrix()
            return True
    
    def clear(self) -> None:
        """清空数据库"""
        with self._lock:
            self._persons.clear()
            self._feature_matrix = None
            self._feature_ids = []
            self._total_embeddings = 0
            logger.info("人脸数据库已清空")
    
    def _cosine_similarity(self, query: np.ndarray, features: np.ndarray) -> np.ndarray:
        """
        计算余弦相似度
        
        Args:
            query: 查询向量 (normalized)
            features: 特征矩阵 (normalized)
            
        Returns:
            相似度数组
        """
        # 归一化查询向量
        query_norm = query / np.clip(np.linalg.norm(query), 1e-10, None)
        
        # 计算余弦相似度（点积）
        similarities = np.dot(features, query_norm)
        
        return similarities
    
    def recognize(
        self,
        embedding: np.ndarray,
        top_k: int = 1
    ) -> MatchResult:
        """
        识别人脸
        
        Args:
            embedding: 查询的特征向量 (512维)
            top_k: 返回前 k 个匹配结果（目前仅使用第一个）
            
        Returns:
            匹配结果
        """
        with self._lock:
            # 数据库为空
            if self._feature_matrix is None or len(self._feature_ids) == 0:
                return MatchResult(
                    person_id=-1,
                    name="陌生人",
                    group_id=None,
                    group_name=None,
                    similarity=0.0,
                    is_stranger=True
                )
            
            # 计算相似度
            similarities = self._cosine_similarity(embedding, self._feature_matrix)
            
            # 找到最大相似度
            max_idx = np.argmax(similarities)
            max_similarity = float(similarities[max_idx])
            matched_person_id = self._feature_ids[max_idx]
            
            # 判断是否为陌生人
            if max_similarity < self.similarity_threshold:
                return MatchResult(
                    person_id=-1,
                    name="陌生人",
                    group_id=None,
                    group_name=None,
                    similarity=max_similarity,
                    is_stranger=True
                )
            
            # 返回匹配的人员
            person = self._persons[matched_person_id]
            return MatchResult(
                person_id=person.person_id,
                name=person.name,
                group_id=person.group_id,
                group_name=person.group_name,
                similarity=max_similarity,
                is_stranger=False
            )
    
    def recognize_batch(
        self,
        embeddings: List[np.ndarray]
    ) -> List[MatchResult]:
        """
        批量识别人脸
        
        Args:
            embeddings: 特征向量列表
            
        Returns:
            匹配结果列表
        """
        return [self.recognize(emb) for emb in embeddings]
    
    def get_person(self, person_id: int) -> Optional[PersonFeature]:
        """
        获取人员信息
        
        Args:
            person_id: 人员 ID
            
        Returns:
            人员特征信息，不存在时返回 None
        """
        with self._lock:
            return self._persons.get(person_id)
    
    def get_all_persons(self) -> List[PersonFeature]:
        """
        获取所有人员信息
        
        Returns:
            人员列表
        """
        with self._lock:
            return list(self._persons.values())
    
    def get_stats(self) -> dict:
        """
        获取数据库统计信息
        
        Returns:
            统计信息字典
        """
        with self._lock:
            return {
                "person_count": len(self._persons),
                "embedding_count": self._total_embeddings,
                "similarity_threshold": self.similarity_threshold,
            }
