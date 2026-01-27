"""
分析管道基类模块

功能：
- 定义管道节点抽象基类
- 提供管道编排功能
- 支持节点动态加载
"""
import logging
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Type
from dataclasses import dataclass, field
from datetime import datetime

import numpy as np

logger = logging.getLogger(__name__)


@dataclass
class PipelineContext:
    """
    管道上下文
    
    在管道节点之间传递的数据容器
    """
    # 原始数据
    frame: Optional[np.ndarray] = None      # 原始图像帧
    camera_id: int = 0                       # 摄像头 ID
    frame_id: int = 0                        # 帧序号
    timestamp: datetime = field(default_factory=datetime.now)
    
    # 处理结果
    faces: List[Any] = field(default_factory=list)          # 检测到的人脸
    recognition_results: List[Any] = field(default_factory=list)  # 识别结果
    alerts: List[Any] = field(default_factory=list)         # 生成的报警
    
    # 元数据
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    # 控制标志
    should_continue: bool = True            # 是否继续执行后续节点
    error: Optional[str] = None             # 错误信息
    
    def set_error(self, error: str) -> None:
        """设置错误并停止管道"""
        self.error = error
        self.should_continue = False


class PipelineNode(ABC):
    """
    管道节点抽象基类
    
    所有管道处理节点都应继承此类
    """
    
    def __init__(self, name: Optional[str] = None):
        """
        初始化节点
        
        Args:
            name: 节点名称，默认使用类名
        """
        self.name = name or self.__class__.__name__
        self._is_initialized = False
    
    @property
    def is_initialized(self) -> bool:
        """节点是否已初始化"""
        return self._is_initialized
    
    def initialize(self) -> bool:
        """
        初始化节点
        
        子类可重写此方法进行资源初始化
        
        Returns:
            是否初始化成功
        """
        self._is_initialized = True
        return True
    
    def cleanup(self) -> None:
        """
        清理节点资源
        
        子类可重写此方法进行资源清理
        """
        self._is_initialized = False
    
    @abstractmethod
    def process(self, context: PipelineContext) -> PipelineContext:
        """
        处理数据
        
        Args:
            context: 管道上下文
            
        Returns:
            处理后的上下文
        """
        pass
    
    def __call__(self, context: PipelineContext) -> PipelineContext:
        """使节点可调用"""
        return self.process(context)


class Pipeline:
    """
    分析管道
    
    将多个处理节点串联，按顺序处理数据
    
    使用示例：
        pipeline = Pipeline("face_analysis")
        pipeline.add_node(DetectionNode())
        pipeline.add_node(RecognitionNode())
        pipeline.add_node(AlertNode())
        
        pipeline.initialize()
        
        context = PipelineContext(frame=image, camera_id=1)
        result = pipeline.run(context)
    """
    
    def __init__(self, name: str = "default"):
        """
        初始化管道
        
        Args:
            name: 管道名称
        """
        self.name = name
        self._nodes: List[PipelineNode] = []
        self._is_initialized = False
    
    @property
    def is_initialized(self) -> bool:
        """管道是否已初始化"""
        return self._is_initialized
    
    @property
    def node_count(self) -> int:
        """节点数量"""
        return len(self._nodes)
    
    def add_node(self, node: PipelineNode) -> "Pipeline":
        """
        添加节点
        
        Args:
            node: 管道节点
            
        Returns:
            管道实例（支持链式调用）
        """
        self._nodes.append(node)
        logger.debug(f"管道 {self.name} 添加节点: {node.name}")
        return self
    
    def remove_node(self, name: str) -> bool:
        """
        移除节点
        
        Args:
            name: 节点名称
            
        Returns:
            是否移除成功
        """
        for i, node in enumerate(self._nodes):
            if node.name == name:
                self._nodes.pop(i)
                logger.debug(f"管道 {self.name} 移除节点: {name}")
                return True
        return False
    
    def get_node(self, name: str) -> Optional[PipelineNode]:
        """
        获取节点
        
        Args:
            name: 节点名称
            
        Returns:
            节点实例，不存在时返回 None
        """
        for node in self._nodes:
            if node.name == name:
                return node
        return None
    
    def initialize(self) -> bool:
        """
        初始化所有节点
        
        Returns:
            是否全部初始化成功
        """
        if self._is_initialized:
            return True
        
        logger.info(f"初始化管道 {self.name}，共 {len(self._nodes)} 个节点")
        
        for node in self._nodes:
            try:
                if not node.initialize():
                    logger.error(f"节点 {node.name} 初始化失败")
                    return False
            except Exception as e:
                logger.error(f"节点 {node.name} 初始化异常: {e}")
                return False
        
        self._is_initialized = True
        logger.info(f"管道 {self.name} 初始化完成")
        return True
    
    def cleanup(self) -> None:
        """清理所有节点"""
        for node in self._nodes:
            try:
                node.cleanup()
            except Exception as e:
                logger.warning(f"节点 {node.name} 清理异常: {e}")
        
        self._is_initialized = False
        logger.info(f"管道 {self.name} 已清理")
    
    def run(self, context: PipelineContext) -> PipelineContext:
        """
        运行管道
        
        Args:
            context: 初始上下文
            
        Returns:
            处理后的上下文
        """
        if not self._is_initialized:
            context.set_error("管道未初始化")
            return context
        
        for node in self._nodes:
            if not context.should_continue:
                logger.debug(f"管道 {self.name} 在节点 {node.name} 前终止")
                break
            
            try:
                context = node.process(context)
            except Exception as e:
                logger.error(f"节点 {node.name} 处理异常: {e}")
                context.set_error(f"节点 {node.name} 异常: {str(e)}")
                break
        
        return context
    
    def __len__(self) -> int:
        """返回节点数量"""
        return len(self._nodes)


class PipelineBuilder:
    """
    管道构建器
    
    提供便捷的管道构建方法
    """
    
    # 注册的节点类型
    _node_registry: Dict[str, Type[PipelineNode]] = {}
    
    @classmethod
    def register_node(cls, name: str, node_class: Type[PipelineNode]) -> None:
        """
        注册节点类型
        
        Args:
            name: 节点类型名称
            node_class: 节点类
        """
        cls._node_registry[name] = node_class
        logger.debug(f"注册节点类型: {name}")
    
    @classmethod
    def create_node(cls, type_name: str, **kwargs) -> Optional[PipelineNode]:
        """
        创建节点实例
        
        Args:
            type_name: 节点类型名称
            **kwargs: 节点初始化参数
            
        Returns:
            节点实例，类型不存在时返回 None
        """
        node_class = cls._node_registry.get(type_name)
        if node_class is None:
            logger.error(f"未知的节点类型: {type_name}")
            return None
        
        return node_class(**kwargs)
    
    @classmethod
    def build_from_config(cls, config: dict) -> Optional[Pipeline]:
        """
        从配置构建管道
        
        配置格式:
        {
            "name": "pipeline_name",
            "nodes": [
                {"type": "detection", "params": {...}},
                {"type": "recognition", "params": {...}},
            ]
        }
        
        Args:
            config: 管道配置
            
        Returns:
            管道实例，构建失败返回 None
        """
        name = config.get("name", "default")
        pipeline = Pipeline(name)
        
        nodes_config = config.get("nodes", [])
        for node_config in nodes_config:
            node_type = node_config.get("type")
            params = node_config.get("params", {})
            
            node = cls.create_node(node_type, **params)
            if node is None:
                logger.error(f"创建节点失败: {node_type}")
                return None
            
            pipeline.add_node(node)
        
        return pipeline
