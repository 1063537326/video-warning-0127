"""
分析管道模块

提供视频帧处理的管道架构，支持：
- 灵活的节点组合
- 动态管道构建
- 可扩展的处理节点
"""
from .base import (
    Pipeline,
    PipelineNode,
    PipelineContext,
    PipelineBuilder,
)
from .nodes import (
    DetectionNode,
    RecognitionNode,
    AlertNode,
    FramePreprocessNode,
)

__all__ = [
    # 基类
    "Pipeline",
    "PipelineNode",
    "PipelineContext",
    "PipelineBuilder",
    # 节点
    "DetectionNode",
    "RecognitionNode",
    "AlertNode",
    "FramePreprocessNode",
]
