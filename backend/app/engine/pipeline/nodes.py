"""
管道处理节点模块

提供各种处理节点的具体实现：
- DetectionNode: 人脸检测节点
- RecognitionNode: 人脸识别节点
- AlertNode: 报警生成节点
"""
import logging
import asyncio
from typing import Optional, Callable, Awaitable, List
from datetime import datetime

import cv2
import numpy as np

from .base import PipelineNode, PipelineContext, PipelineBuilder
from ..recognition import (
    FaceDetector, 
    DetectorConfig, 
    FaceRecognizer, 
    RecognizerConfig,
    FaceInfo,
    RecognitionResult,
)

logger = logging.getLogger(__name__)


class DetectionNode(PipelineNode):
    """
    人脸检测节点
    
    功能：
    - 从图像中检测人脸
    - 提取人脸特征向量
    - 过滤低质量人脸
    """
    
    def __init__(
        self, 
        config: Optional[DetectorConfig] = None,
        name: str = "DetectionNode"
    ):
        """
        初始化检测节点
        
        Args:
            config: 检测器配置
            name: 节点名称
        """
        super().__init__(name)
        self.config = config or DetectorConfig()
        self._detector: Optional[FaceDetector] = None
    
    def initialize(self) -> bool:
        """初始化检测器"""
        try:
            self._detector = FaceDetector(self.config)
            success = self._detector.load_model()
            self._is_initialized = success
            return success
        except Exception as e:
            logger.error(f"DetectionNode 初始化失败: {e}")
            return False
    
    def cleanup(self) -> None:
        """清理资源"""
        if self._detector:
            self._detector.unload_model()
            self._detector = None
        super().cleanup()
    
    def process(self, context: PipelineContext) -> PipelineContext:
        """
        处理图像，检测人脸
        
        Args:
            context: 管道上下文
            
        Returns:
            包含检测结果的上下文
        """
        if context.frame is None:
            context.set_error("输入图像为空")
            return context
        
        if self._detector is None:
            context.set_error("检测器未初始化")
            return context
        
        try:
            # 执行检测
            faces = self._detector.detect(
                context.frame, 
                extract_embedding=True,
                crop_face=True
            )
            
            context.faces = faces
            context.metadata["detection_count"] = len(faces)
            
            logger.debug(f"检测到 {len(faces)} 个人脸")
            
        except Exception as e:
            logger.error(f"人脸检测失败: {e}")
            context.set_error(f"检测失败: {str(e)}")
        
        return context


class RecognitionNode(PipelineNode):
    """
    人脸识别节点
    
    功能：
    - 将检测到的人脸与人脸库比对
    - 判定已知人员/陌生人
    - 应用报警冷却策略
    """
    
    def __init__(
        self,
        recognizer: FaceRecognizer,
        name: str = "RecognitionNode"
    ):
        """
        初始化识别节点
        
        Args:
            recognizer: 人脸识别器实例（共享）
            name: 节点名称
        """
        super().__init__(name)
        self._recognizer = recognizer
    
    def initialize(self) -> bool:
        """初始化（检查识别器状态）"""
        if self._recognizer is None:
            return False
        self._is_initialized = self._recognizer.is_loaded
        return self._is_initialized
    
    def process(self, context: PipelineContext) -> PipelineContext:
        """
        处理检测到的人脸，进行识别
        
        Args:
            context: 管道上下文
            
        Returns:
            包含识别结果的上下文
        """
        if not context.faces:
            # 没有检测到人脸，继续执行
            return context
        
        if self._recognizer is None:
            context.set_error("识别器未配置")
            return context
        
        try:
            results: List[RecognitionResult] = []
            
            for face in context.faces:
                if face.embedding is None:
                    continue
                
                # 人脸比对
                match_result = self._recognizer.database.recognize(face.embedding)
                
                # 构建识别结果
                result = RecognitionResult(
                    face_info=face,
                    match_result=match_result,
                    camera_id=context.camera_id,
                    timestamp=context.timestamp,
                    should_alert=False,
                    alert_type="known" if not match_result.is_stranger else "stranger"
                )
                results.append(result)
            
            context.recognition_results = results
            context.metadata["recognition_count"] = len(results)
            
            logger.debug(f"识别完成，共 {len(results)} 个结果")
            
        except Exception as e:
            logger.error(f"人脸识别失败: {e}")
            context.set_error(f"识别失败: {str(e)}")
        
        return context


class AlertNode(PipelineNode):
    """
    报警生成节点
    
    功能：
    - 根据识别结果判断是否报警
    - 应用报警冷却策略
    - 生成报警数据
    """
    
    def __init__(
        self,
        alert_on_stranger: bool = True,
        blacklist_group_ids: Optional[List[int]] = None,
        cooldown_manager = None,
        on_alert: Optional[Callable[[dict], Awaitable[None]]] = None,
        name: str = "AlertNode"
    ):
        """
        初始化报警节点
        
        Args:
            alert_on_stranger: 是否对陌生人报警
            blacklist_group_ids: 黑名单分组 ID 列表
            cooldown_manager: 报警冷却管理器
            on_alert: 报警回调函数（异步）
            name: 节点名称
        """
        super().__init__(name)
        self.alert_on_stranger = alert_on_stranger
        self.blacklist_group_ids = blacklist_group_ids or []
        self._cooldown_manager = cooldown_manager
        self._on_alert = on_alert
    
    def initialize(self) -> bool:
        """初始化"""
        self._is_initialized = True
        return True
    
    def _should_alert(self, result: RecognitionResult) -> tuple:
        """
        判断是否应该报警
        
        Args:
            result: 识别结果
            
        Returns:
            (是否报警, 报警类型)
        """
        match = result.match_result
        
        # 陌生人
        if match.is_stranger:
            return self.alert_on_stranger, "stranger"
        
        # 黑名单
        if match.group_id in self.blacklist_group_ids:
            return True, "blacklist"
        
        # 已知人员
        return False, "known"
    
    def _check_cooldown(self, camera_id: int, person_id: Optional[int]) -> bool:
        """
        检查报警冷却
        
        Args:
            camera_id: 摄像头 ID
            person_id: 人员 ID
            
        Returns:
            是否可以报警
        """
        if self._cooldown_manager is None:
            return True
        
        return self._cooldown_manager.can_alert(camera_id, person_id)
    
    def _record_cooldown(self, camera_id: int, person_id: Optional[int]) -> None:
        """记录报警冷却"""
        if self._cooldown_manager:
            self._cooldown_manager.record_alert(camera_id, person_id)
    
    def _generate_alert_data(
        self, 
        result: RecognitionResult, 
        alert_type: str,
        context: PipelineContext
    ) -> dict:
        """
        生成报警数据
        
        Args:
            result: 识别结果
            alert_type: 报警类型
            context: 管道上下文
            
        Returns:
            报警数据字典
        """
        face = result.face_info
        match = result.match_result
        
        # 编码人脸图像
        face_image_base64 = None
        if face.face_image is not None:
            try:
                _, buffer = cv2.imencode('.jpg', face.face_image, [cv2.IMWRITE_JPEG_QUALITY, 85])
                import base64
                face_image_base64 = base64.b64encode(buffer).decode('utf-8')
            except Exception as e:
                logger.warning(f"人脸图像编码失败: {e}")
        
        return {
            "camera_id": context.camera_id,
            "alert_type": alert_type,
            "person_id": match.person_id if not match.is_stranger else None,
            "person_name": match.name,
            "group_id": match.group_id,
            "group_name": match.group_name,
            "confidence": match.similarity,
            "face_bbox": list(face.bbox),
            "face_image": face_image_base64,
            "quality_score": face.quality_score,
            "timestamp": context.timestamp.isoformat(),
            "frame_id": context.frame_id,
        }
    
    def process(self, context: PipelineContext) -> PipelineContext:
        """
        处理识别结果，生成报警
        
        Args:
            context: 管道上下文
            
        Returns:
            包含报警数据的上下文
        """
        if not context.recognition_results:
            return context
        
        alerts = []
        
        for result in context.recognition_results:
            # 判断是否报警
            should_alert, alert_type = self._should_alert(result)
            
            if not should_alert:
                continue
            
            # 检查冷却
            person_id = None if result.match_result.is_stranger else result.match_result.person_id
            if not self._check_cooldown(context.camera_id, person_id):
                logger.debug(f"报警冷却中，跳过: camera={context.camera_id}, person={person_id}")
                continue
            
            # 记录冷却
            self._record_cooldown(context.camera_id, person_id)
            
            # 生成报警数据
            alert_data = self._generate_alert_data(result, alert_type, context)
            alerts.append(alert_data)
            
            # 更新识别结果标志
            result.should_alert = True
            result.alert_type = alert_type
            
            # 异步回调
            if self._on_alert:
                try:
                    # 尝试在事件循环中执行异步回调
                    loop = asyncio.get_event_loop()
                    if loop.is_running():
                        asyncio.create_task(self._on_alert(alert_data))
                    else:
                        loop.run_until_complete(self._on_alert(alert_data))
                except RuntimeError:
                    # 没有事件循环，跳过异步回调
                    logger.debug("无法执行异步报警回调")
        
        context.alerts = alerts
        context.metadata["alert_count"] = len(alerts)
        
        if alerts:
            logger.info(f"生成 {len(alerts)} 条报警")
        
        return context


class FramePreprocessNode(PipelineNode):
    """
    帧预处理节点
    
    功能：
    - 图像缩放
    - 颜色空间转换
    - 增强处理
    """
    
    def __init__(
        self,
        target_size: Optional[tuple] = None,
        convert_color: bool = False,
        enhance: bool = False,
        name: str = "FramePreprocessNode"
    ):
        """
        初始化预处理节点
        
        Args:
            target_size: 目标尺寸 (width, height)，None 表示不缩放
            convert_color: 是否转换颜色空间
            enhance: 是否增强图像
            name: 节点名称
        """
        super().__init__(name)
        self.target_size = target_size
        self.convert_color = convert_color
        self.enhance = enhance
    
    def process(self, context: PipelineContext) -> PipelineContext:
        """预处理图像"""
        if context.frame is None:
            return context
        
        frame = context.frame
        
        # 缩放
        if self.target_size:
            frame = cv2.resize(frame, self.target_size)
        
        # 颜色转换（如果需要）
        if self.convert_color:
            # 假设输入是 BGR，转换为 RGB
            frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        
        # 图像增强
        if self.enhance:
            # 简单的直方图均衡化
            lab = cv2.cvtColor(frame, cv2.COLOR_BGR2LAB)
            l, a, b = cv2.split(lab)
            clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
            l = clahe.apply(l)
            lab = cv2.merge([l, a, b])
            frame = cv2.cvtColor(lab, cv2.COLOR_LAB2BGR)
        
        context.frame = frame
        context.metadata["preprocessed"] = True
        
        return context


# 注册节点类型
PipelineBuilder.register_node("detection", DetectionNode)
PipelineBuilder.register_node("recognition", RecognitionNode)
PipelineBuilder.register_node("alert", AlertNode)
PipelineBuilder.register_node("preprocess", FramePreprocessNode)
