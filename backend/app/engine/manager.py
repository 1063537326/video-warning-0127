"""
视频分析引擎管理器
"""
import logging
import threading
import time
import asyncio
import cv2
import os
import shutil
from typing import Dict, List, Optional, Callable, Awaitable
from dataclasses import dataclass, field
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor
from ultralytics import YOLO

from app.core.config import settings
from app.models.alert import AlertType, AlertLevel
from .capture import CameraCapture, CaptureConfig, CaptureStatus
from .stream import stream_broadcaster
from .recognition.client import compreface_client
from .analyzers.tracker import YoloTracker, TrackerEvent

logger = logging.getLogger(__name__)

from enum import Enum

class EngineStatus(Enum):
    STOPPED = "stopped"
    STARTING = "starting"
    RUNNING = "running"
    STOPPING = "stopping"
    ERROR = "error"

@dataclass
class CameraTask:
    """摄像头任务"""
    camera_id: int
    name: str
    rtsp_url: str
    username: Optional[str] = None
    password: Optional[str] = None
    target_fps: int = 5
    is_enabled: bool = True
    config: Optional[dict] = None
    
    # 运行时状态
    capture: Optional[CameraCapture] = None
    tracker: Optional[YoloTracker] = None # 每个摄像头独立的 Tracker (状态独立)
    status: CaptureStatus = CaptureStatus.IDLE
    last_frame_time: Optional[datetime] = None
    error_count: int = 0

class EngineManager:
    """
    新版视频分析引擎管理器
    集成 YOLO检测、ByteTrack追踪、CompreFace识别、流媒体广播
    """
    
    def __init__(self):
        self._status = EngineStatus.STOPPED
        self._status_lock = threading.Lock()
        
        self._cameras: Dict[int, CameraTask] = {}
        self._cameras_lock = threading.Lock()
        
        # 共享模型 (只加载一次)
        self._shared_body_model = None
        self._shared_face_model = None
        
        self._executor: Optional[ThreadPoolExecutor] = None
        self._analysis_threads: Dict[int, threading.Thread] = {}
        self._stop_events: Dict[int, threading.Event] = {}
        
        # 健康检查
        self._health_thread: Optional[threading.Thread] = None
        self._health_stop_event = threading.Event()
        
        # 主线程 Loop (用于跨线程调度)
        self._main_loop: Optional[asyncio.AbstractEventLoop] = None
        
        # 回调
        self._on_alert: Optional[Callable[[dict], Awaitable[None]]] = None
        self._on_status_change: Optional[Callable[[int, str], Awaitable[None]]] = None
    
    @property
    def status(self) -> str:
        return self._status
        
    def set_alert_callback(self, callback: Callable[[dict], Awaitable[None]]):
        self._on_alert = callback
        
    def set_status_callback(self, callback: Callable[[int, str], Awaitable[None]]):
        self._on_status_change = callback
        
    async def start(self) -> bool:
        if self._status == EngineStatus.RUNNING: return True
        self._status = EngineStatus.STARTING
        
        try:
            # 1. 加载模型
            logger.info(f"正在加载 YOLO 模型...")
            self._shared_body_model = YOLO(settings.YOLO_BODY_MODEL)
            self._shared_face_model = YOLO(settings.YOLO_FACE_MODEL)
            logger.info("YOLO 模型加载完成")
            
            # 2. 初始化 CompreFace 客户端资源
            await compreface_client.start()
            
            # 捕获主循环
            self._main_loop = asyncio.get_running_loop()
            
            # 3. 线程池
            self._executor = ThreadPoolExecutor(max_workers=settings.CONCURRENT_LIMIT_DEFAULT + 4)
            
            # 4. 健康检查
            self._health_stop_event.clear()
            self._health_thread = threading.Thread(target=self._health_check_loop, daemon=True, name="HealthCheck")
            self._health_thread.start()
            
            self._status = EngineStatus.RUNNING
            logger.info("引擎启动回调完成")
            
            # 启动所有已添加的摄像头
            await self.start_all_cameras()
            
            return True
        except Exception as e:
            logger.error(f"引擎启动失败: {e}")
            self._status = EngineStatus.ERROR
            return False

    async def stop(self):
        if self._status == EngineStatus.STOPPED: return
        self._status = EngineStatus.STOPPING
        
        await self.stop_all_cameras()
        
        self._health_stop_event.set()
        if self._health_thread: self._health_thread.join()
        
        if self._executor: self._executor.shutdown(wait=True)
        
        self._status = EngineStatus.STOPPED
        logger.info("引擎已停止")

    # ... 摄像头增删改查逻辑与原版类似，略微简化 ...
    def add_camera(self, camera_id: int, name: str, rtsp_url: str, **kwargs):
        with self._cameras_lock:
            if camera_id in self._cameras: return False
            self._cameras[camera_id] = CameraTask(camera_id, name, rtsp_url, **kwargs)
            
        # 如果引擎正在运行，尝试启动摄像头
        if self._status == EngineStatus.RUNNING:
            self.start_camera(camera_id)
            
        return True

    def remove_camera(self, camera_id: int):
        self.stop_camera(camera_id)
        with self._cameras_lock:
            if camera_id in self._cameras:
                del self._cameras[camera_id]
                return True
        return False

    def start_camera(self, camera_id: int) -> bool:
        if self._status != EngineStatus.RUNNING: return False
        
        with self._cameras_lock:
            task = self._cameras.get(camera_id)
            if not task: return False
            if task.capture and task.status == CaptureStatus.RUNNING: return True
            
            # 1. 采集器
            task.capture = CameraCapture(
                CaptureConfig(task.rtsp_url, camera_id, task.username, task.password, task.target_fps),
                on_status_change=self._on_camera_status_change
            )
            if not task.capture.start(): return False
            
            # 2. 追踪器 (传入共享模型)
            task.tracker = YoloTracker(self._shared_body_model, self._shared_face_model)
            
            # 3. 分析线程
            stop_event = threading.Event()
            self._stop_events[camera_id] = stop_event
            thread = threading.Thread(
                target=self._analysis_loop,
                args=(camera_id, stop_event),
                name=f"Analysis-{camera_id}",
                daemon=True
            )
            self._analysis_threads[camera_id] = thread
            thread.start()
            
            logger.info(f"摄像头 {camera_id} 已启动")
            return True

    def stop_camera(self, camera_id: int):
        # ... 停止逻辑 ...
        with self._cameras_lock:
            task = self._cameras.get(camera_id)
            
        if camera_id in self._stop_events:
            self._stop_events[camera_id].set()
            
        if camera_id in self._analysis_threads:
            self._analysis_threads[camera_id].join(timeout=2.0)
            del self._analysis_threads[camera_id]
            del self._stop_events[camera_id]
            
        if task and task.capture:
            task.capture.stop()
            task.capture = None
            task.tracker = None
            task.status = CaptureStatus.STOPPED

    async def stop_all_cameras(self):
        ids = list(self._cameras.keys())
        for i in ids: self.stop_camera(i)

    async def start_all_cameras(self):
        """启动所有摄像头"""
        ids = list(self._cameras.keys())
        for i in ids:
            self.start_camera(i)

    def _analysis_loop(self, camera_id: int, stop_event: threading.Event):
        """分析主循环"""
        task = self._cameras.get(camera_id)
        if not task: return
        
        logger.info(f"Analysis loop started for camera {camera_id}")
        
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        while not stop_event.is_set():
            try:
                # 1. 获取帧
                frame_data = task.capture.get_frame(timeout=0.5)
                if frame_data is None: continue
                
                # 2. 追踪处理
                annotated_frame, events = task.tracker.process(frame_data.frame, frame_data.timestamp)
                
                # 3. 广播直播流 (MJPEG)
                # 使用 threadsafe 调用提交给主线程 Loop
                if self._main_loop and not self._main_loop.is_closed():
                    _, buffer = cv2.imencode('.jpg', annotated_frame, [cv2.IMWRITE_JPEG_QUALITY, 70])
                    jpg_bytes = buffer.tobytes()
                    asyncio.run_coroutine_threadsafe(
                        stream_broadcaster.broadcast(camera_id, jpg_bytes),
                        self._main_loop
                    )
                
                # 运行异步处理逻辑 (识别 + 报警)
                # 注意: 这里使用当前线程的 loop 等待结果
                loop.run_until_complete(self._handle_analysis_events(camera_id, events))
                
            except Exception as e:
                logger.error(f"Analysis error: {e}")
                time.sleep(1)
                
        loop.close()

    async def _handle_analysis_events(self, camera_id: int, events: List[TrackerEvent]):
        """处理事件 (在分析线程的 loop 中运行)"""
        
        for event in events:
            # 根据决策矩阵处理
            
            # 1. 保存图片到磁盘
            img_paths = await self._save_event_images(camera_id, event)
            
            # 2. 识别逻辑
            person_name = None
            is_known = False
            
            if event.type == "FACE_DETECTED" and event.face_image is not None:
                # 编码人脸
                _, f_buf = cv2.imencode('.jpg', event.face_image)
                # 调用 CompreFace
                resp = await compreface_client.recognize_face(f_buf.tobytes())
                
                if resp and 'result' in resp and len(resp['result']) > 0:
                    # 取第一个结果
                    subj = resp['result'][0]['subjects'][0]
                    sim = subj['similarity']
                    name = subj['subject']
                    
                    if sim >= settings.COMPREFACE_THRESHOLD:
                         is_known = True
                         person_name = name
                    else:
                         is_known = False
                         
            # 3. 决策报警级别
            alert_type = AlertType.STRANGER
            alert_level = event.alert_level 
            
            if is_known:
                alert_type = AlertType.KNOWN
                alert_level = AlertLevel.INFO # 降级为 Info (Log)
                event.type = "KNOWN_PERSON_DETECTED" # 修改事件类型用于通知
                
            elif event.type == "BODY_DETECTED":
                alert_type = AlertType.STRANGER
                alert_level = AlertLevel.WARNING # 弱提醒
                
            # 4. 生成报警数据
            alert_data = {
                "track_id": str(event.track_id),
                "camera_id": camera_id,
                "alert_type": alert_type,
                "alert_level": alert_level,
                "person_name": person_name,
                "face_image": img_paths.get('face'),
                "body_image": img_paths.get('body'),
                "full_image": img_paths.get('full'),
                "timestamp": event.timestamp.isoformat(),
                "score": event.face_score if event.type != "BODY_DETECTED" else event.body_score
            }
            
            # 5. 回调通知 (调度到主线程执行)
            if self._on_alert and self._main_loop:
                 asyncio.run_coroutine_threadsafe(self._on_alert(alert_data), self._main_loop)

    async def _save_event_images(self, camera_id: int, event: TrackerEvent) -> dict:
        """保存图片并返回路径"""
        # 路径生成: data/captures/{date}/{camera_id}/{type}/{track_id}_{ts}_{type}.jpg
        date_str = event.timestamp.strftime("%Y%m%d")
        base_dir = os.path.join(settings.CAPTURES_DIR, date_str, str(camera_id))
        
        # 创建子目录
        sub_dirs = ["face", "body", "full"]
        for d in sub_dirs:
            os.makedirs(os.path.join(base_dir, d), exist_ok=True)
        
        paths = {}
        timestamp_str = event.timestamp.strftime("%H%M%S_%f")
        track_prefix = f"{event.track_id}_{timestamp_str}"
        
        # 保存图片函数
        def save_img(img, suffix):
            if img is not None:
                # 放在对应的子目录下
                # 例如: .../face/123_100000_face.jpg
                filename = f"{track_prefix}_{suffix}.jpg"
                filepath = os.path.join(base_dir, suffix, filename)
                cv2.imwrite(filepath, img)
                
                # 返回相对路径供前端使用 (static/...)
                # 假设 settings.DATA_DIR 对应 /static
                rel_path = os.path.relpath(filepath, settings.DATA_DIR)
                # fix windows path sep
                rel_path = rel_path.replace("\\", "/")
                return f"/static/{rel_path}"
            return None

        paths['full'] = save_img(event.full_image, "full")
        paths['face'] = save_img(event.face_image, "face")
        paths['body'] = save_img(event.body_image, "body")
        
        return paths

    def _on_camera_status_change(self, camera_id, status):
        # 调度到主线程
        if self._on_status_change and self._main_loop:
             asyncio.run_coroutine_threadsafe(self._on_status_change(camera_id, status.value), self._main_loop)
        
    def update_config(self, key: str, value: str):
        """
        动态更新配置
        Args:
            key: 配置键 (DB中的key)
            value: 配置值 (字符串)
        """
        try:
            # 1. 映射 DB key 到 Settings key
            mapping = {
                "face_similarity_threshold": "COMPREFACE_THRESHOLD",
                "face_detection_confidence": "CONF_FACE",
                "alert_cooldown_seconds": "ALERT_COOLDOWN_SECONDS",
                "data_retention_days": "DATA_RETENTION_DAYS",
                "capture_quality": "CAPTURE_QUALITY",
                "concurrent_limit": "CONCURRENT_LIMIT_DEFAULT"
            }
            
            target_key = mapping.get(key)
            if target_key:
                # 类型转换
                field_type = settings.model_fields[target_key].annotation
                if field_type == int:
                    new_val = int(float(value))
                elif field_type == float:
                    new_val = float(value)
                elif field_type == bool:
                    new_val = value.lower() == "true"
                else:
                    new_val = value
                    
                setattr(settings, target_key, new_val)
                logger.info(f"Updated setting {target_key} = {new_val}")
                
            # 2. 特殊处理
            # 比如并发限制更新，即便 settings 更新了，client 实例也需要通知
            if key == "concurrent_limit":
                limit = int(float(value))
                compreface_client.update_limit(limit)
                
        except Exception as e:
            logger.error(f"Config update failed for {key}={value}: {e}")

    def _health_check_loop(self):
        """简单健康检查"""
        while not self._health_stop_event.wait(30):
             # 检查线程存活
             pass

    def get_engine_stats(self) -> dict:
        """获取引擎统计信息"""
        running_count = sum(1 for c in self._cameras.values() if c.status == CaptureStatus.RUNNING)
        return {
            "status": self._status.value,
            "camera_count": len(self._cameras),
            "running_camera_count": running_count,
            "recognizer": {
                "is_loaded": True, # Always true in this architecture once started
                "database": {
                    "person_count": 0, # TODO: Get from CompreFace/DB
                    "embedding_count": 0,
                    "similarity_threshold": settings.COMPREFACE_THRESHOLD
                },
                "config": {
                    "similarity_threshold": settings.COMPREFACE_THRESHOLD,
                    "alert_on_stranger": True,
                    "alert_cooldown": settings.ALERT_COOLDOWN_SECONDS
                }
            }
        }

    def get_all_camera_status(self) -> List[dict]:
        """获取所有摄像头状态"""
        status_list = []
        with self._cameras_lock:
            for cam in self._cameras.values():
                status_list.append({
                    "camera_id": cam.camera_id,
                    "camera_name": cam.name,
                    "status": "running" if cam.status == CaptureStatus.RUNNING else "stopped",
                    "fps": getattr(cam.capture, 'current_fps', 0) if cam.capture else 0,
                    "queue_size": 0, # Not tracking queue size in this simplified version
                    "total_frames": 0, # TODO: Track frames
                    "processed_frames": 0,
                    "last_frame_time": cam.last_frame_time.isoformat() if cam.last_frame_time else None
                })
        return status_list

    def get_camera_status(self, camera_id: int) -> Optional[dict]:
        """获取单个摄像头状态"""
        with self._cameras_lock:
            cam = self._cameras.get(camera_id)
            if not cam:
                return None
                
            return {
                "camera_id": cam.camera_id,
                "camera_name": cam.name,
                "status": "running" if cam.status == CaptureStatus.RUNNING else "stopped",
                "fps": getattr(cam.capture, 'current_fps', 0) if cam.capture else 0,
                "queue_size": 0,
                "total_frames": 0,
                "processed_frames": 0,
                "last_frame_time": cam.last_frame_time.isoformat() if cam.last_frame_time else None
            }

# 全局实例
_engine_instance = None
def get_engine():
    global _engine_instance
    if _engine_instance is None:
        _engine_instance = EngineManager()
    return _engine_instance
