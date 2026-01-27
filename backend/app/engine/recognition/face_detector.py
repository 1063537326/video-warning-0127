"""
人脸检测模块

功能：
- 使用 InsightFace 进行人脸检测
- 返回人脸边界框、关键点、质量评分
- 支持批量检测
"""
import logging
from typing import List, Optional, Tuple
from dataclasses import dataclass, field

import numpy as np

logger = logging.getLogger(__name__)

# InsightFace 延迟导入，避免未安装时导入失败
_insightface = None
_FaceAnalysis = None


def _load_insightface():
    """延迟加载 InsightFace"""
    global _insightface, _FaceAnalysis
    if _insightface is None:
        try:
            import insightface
            from insightface.app import FaceAnalysis
            _insightface = insightface
            _FaceAnalysis = FaceAnalysis
            logger.info(f"InsightFace 版本: {insightface.__version__}")
        except ImportError as e:
            logger.error(f"InsightFace 未安装: {e}")
            raise ImportError(
                "InsightFace 未安装，请运行: pip install insightface onnxruntime"
            ) from e
    return _insightface, _FaceAnalysis


@dataclass
class FaceInfo:
    """检测到的人脸信息"""
    bbox: Tuple[int, int, int, int]     # 边界框 (x1, y1, x2, y2)
    score: float                         # 检测置信度 (0-1)
    landmarks: Optional[np.ndarray] = None  # 5 点关键点
    embedding: Optional[np.ndarray] = None  # 特征向量 (512维)
    age: Optional[int] = None            # 年龄估计
    gender: Optional[str] = None         # 性别 ('M' 或 'F')
    quality_score: float = 0.0           # 人脸质量评分 (0-1)
    face_image: Optional[np.ndarray] = None  # 裁剪的人脸图像
    
    def to_dict(self) -> dict:
        """转换为字典"""
        return {
            "bbox": list(self.bbox),
            "score": round(self.score, 4),
            "age": self.age,
            "gender": self.gender,
            "quality_score": round(self.quality_score, 4),
        }


@dataclass
class DetectorConfig:
    """检测器配置"""
    model_name: str = "buffalo_l"       # 模型名称：buffalo_l, buffalo_s, buffalo_sc
    det_size: Tuple[int, int] = (640, 640)  # 检测输入尺寸
    det_thresh: float = 0.5             # 检测阈值
    max_faces: int = 10                 # 单帧最大人脸数
    providers: List[str] = field(default_factory=lambda: ["CPUExecutionProvider"])
    # GPU: ["CUDAExecutionProvider", "CPUExecutionProvider"]
    
    # 质量过滤参数
    min_face_size: int = 50             # 最小人脸像素
    min_quality_score: float = 0.3      # 最低质量分数
    enable_quality_filter: bool = True  # 是否启用质量过滤


class FaceDetector:
    """
    人脸检测器
    
    基于 InsightFace 的人脸检测，支持：
    - 人脸检测与定位
    - 人脸关键点提取
    - 人脸质量评估
    - 年龄/性别估计（可选）
    
    使用示例：
        config = DetectorConfig(det_thresh=0.5)
        detector = FaceDetector(config)
        detector.load_model()
        
        faces = detector.detect(image)
        for face in faces:
            print(f"人脸位置: {face.bbox}, 置信度: {face.score}")
    """
    
    def __init__(self, config: Optional[DetectorConfig] = None):
        """
        初始化检测器
        
        Args:
            config: 检测器配置，None 时使用默认配置
        """
        self.config = config or DetectorConfig()
        self._model = None
        self._is_loaded = False
    
    @property
    def is_loaded(self) -> bool:
        """模型是否已加载"""
        return self._is_loaded
    
    def load_model(self) -> bool:
        """
        加载检测模型
        
        Returns:
            是否加载成功
        """
        if self._is_loaded:
            logger.warning("模型已加载，跳过")
            return True
        
        try:
            _, FaceAnalysis = _load_insightface()
            
            logger.info(f"正在加载人脸检测模型: {self.config.model_name}")
            
            # 创建 FaceAnalysis 实例
            self._model = FaceAnalysis(
                name=self.config.model_name,
                providers=self.config.providers
            )
            
            # 准备模型
            self._model.prepare(
                ctx_id=0,  # GPU ID，-1 表示 CPU
                det_size=self.config.det_size,
                det_thresh=self.config.det_thresh
            )
            
            self._is_loaded = True
            logger.info("人脸检测模型加载完成")
            return True
            
        except Exception as e:
            logger.error(f"人脸检测模型加载失败: {e}")
            self._is_loaded = False
            return False
    
    def _calculate_quality_score(self, face, image_shape: Tuple[int, int, int]) -> float:
        """
        计算人脸质量分数
        
        综合考虑：
        - 人脸大小
        - 检测置信度
        - 人脸位置（是否靠近边缘）
        - 姿态角度（通过关键点估计）
        
        Args:
            face: InsightFace 检测结果
            image_shape: 图像形状 (height, width, channels)
            
        Returns:
            质量分数 (0-1)
        """
        height, width = image_shape[:2]
        bbox = face.bbox.astype(int)
        x1, y1, x2, y2 = bbox
        
        face_width = x2 - x1
        face_height = y2 - y1
        
        # 1. 人脸大小分数 (越大越好，但不超过图像的50%)
        size_ratio = (face_width * face_height) / (width * height)
        size_score = min(size_ratio * 10, 1.0)  # 10% 面积得满分
        
        # 2. 检测置信度分数
        det_score = float(face.det_score)
        
        # 3. 边缘惩罚 (人脸靠近边缘时降低分数)
        margin_x = min(x1, width - x2) / width
        margin_y = min(y1, height - y2) / height
        edge_score = min(margin_x * 10, 1.0) * min(margin_y * 10, 1.0)
        
        # 4. 人脸比例分数 (接近 1:1 比例更好)
        aspect_ratio = face_width / max(face_height, 1)
        ratio_score = 1.0 - abs(aspect_ratio - 1.0) * 0.5
        ratio_score = max(0, min(1, ratio_score))
        
        # 5. 综合分数
        quality_score = (
            size_score * 0.25 +
            det_score * 0.35 +
            edge_score * 0.2 +
            ratio_score * 0.2
        )
        
        return float(quality_score)
    
    def _crop_face(
        self, 
        image: np.ndarray, 
        bbox: Tuple[int, int, int, int],
        margin: float = 0.2
    ) -> np.ndarray:
        """
        裁剪人脸图像
        
        Args:
            image: 原始图像
            bbox: 人脸边界框
            margin: 边距比例
            
        Returns:
            裁剪后的人脸图像
        """
        height, width = image.shape[:2]
        x1, y1, x2, y2 = bbox
        
        # 添加边距
        face_width = x2 - x1
        face_height = y2 - y1
        margin_x = int(face_width * margin)
        margin_y = int(face_height * margin)
        
        x1 = max(0, x1 - margin_x)
        y1 = max(0, y1 - margin_y)
        x2 = min(width, x2 + margin_x)
        y2 = min(height, y2 + margin_y)
        
        return image[y1:y2, x1:x2].copy()
    
    def detect(
        self, 
        image: np.ndarray,
        extract_embedding: bool = True,
        crop_face: bool = False
    ) -> List[FaceInfo]:
        """
        检测图像中的人脸
        
        Args:
            image: BGR 格式图像 (numpy array)
            extract_embedding: 是否提取特征向量
            crop_face: 是否裁剪人脸图像
            
        Returns:
            检测到的人脸列表
        """
        if not self._is_loaded:
            raise RuntimeError("模型未加载，请先调用 load_model()")
        
        if image is None or image.size == 0:
            logger.warning("输入图像为空")
            return []
        
        try:
            # 执行检测
            faces = self._model.get(image, max_num=self.config.max_faces)
            
            results = []
            for face in faces:
                # 获取边界框
                bbox = tuple(face.bbox.astype(int))
                x1, y1, x2, y2 = bbox
                
                # 检查人脸大小
                face_width = x2 - x1
                face_height = y2 - y1
                if face_width < self.config.min_face_size or face_height < self.config.min_face_size:
                    continue
                
                # 计算质量分数
                quality_score = self._calculate_quality_score(face, image.shape)
                
                # 质量过滤
                if self.config.enable_quality_filter and quality_score < self.config.min_quality_score:
                    logger.debug(f"人脸质量过低 ({quality_score:.2f})，跳过")
                    continue
                
                # 构建结果
                face_info = FaceInfo(
                    bbox=bbox,
                    score=float(face.det_score),
                    landmarks=face.kps if hasattr(face, 'kps') else None,
                    embedding=face.embedding if extract_embedding and hasattr(face, 'embedding') else None,
                    age=int(face.age) if hasattr(face, 'age') else None,
                    gender='M' if hasattr(face, 'gender') and face.gender == 1 else 'F' if hasattr(face, 'gender') else None,
                    quality_score=quality_score,
                )
                
                # 裁剪人脸
                if crop_face:
                    face_info.face_image = self._crop_face(image, bbox)
                
                results.append(face_info)
            
            # 按质量分数排序
            results.sort(key=lambda x: x.quality_score, reverse=True)
            
            return results
            
        except Exception as e:
            logger.error(f"人脸检测失败: {e}")
            return []
    
    def detect_largest(
        self, 
        image: np.ndarray,
        extract_embedding: bool = True
    ) -> Optional[FaceInfo]:
        """
        检测图像中最大的人脸
        
        Args:
            image: BGR 格式图像
            extract_embedding: 是否提取特征向量
            
        Returns:
            最大的人脸信息，没有检测到时返回 None
        """
        faces = self.detect(image, extract_embedding=extract_embedding)
        
        if not faces:
            return None
        
        # 按人脸面积排序
        faces.sort(key=lambda f: (f.bbox[2] - f.bbox[0]) * (f.bbox[3] - f.bbox[1]), reverse=True)
        return faces[0]
    
    def unload_model(self) -> None:
        """卸载模型，释放内存"""
        if self._model is not None:
            del self._model
            self._model = None
            self._is_loaded = False
            logger.info("人脸检测模型已卸载")
