"""
摄像头视频采集模块

功能：
- RTSP 视频流连接与读取
- 断流自动重连（指数退避策略）
- 帧率控制与跳帧策略
- 帧队列管理（防内存溢出）
"""
import cv2
import time
import threading
import queue
import logging
from typing import Optional, Callable, Tuple
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime

import numpy as np

logger = logging.getLogger(__name__)


class CaptureStatus(str, Enum):
    """采集状态枚举"""
    IDLE = "idle"           # 空闲
    CONNECTING = "connecting"  # 连接中
    RUNNING = "running"     # 运行中
    RECONNECTING = "reconnecting"  # 重连中
    STOPPED = "stopped"     # 已停止
    ERROR = "error"         # 错误


@dataclass
class CaptureConfig:
    """采集配置"""
    rtsp_url: str                           # RTSP 地址
    camera_id: int = 0                      # 摄像头 ID
    username: Optional[str] = None          # 用户名
    password: Optional[str] = None          # 密码
    target_fps: int = 5                     # 目标帧率（跳帧后）
    queue_size: int = 30                    # 帧队列大小
    reconnect_interval: float = 1.0         # 初始重连间隔（秒）
    max_reconnect_interval: float = 60.0    # 最大重连间隔（秒）
    reconnect_backoff: float = 2.0          # 重连退避倍数
    connection_timeout: float = 10.0        # 连接超时（秒）
    read_timeout: float = 5.0               # 读取超时（秒）


@dataclass
class FrameData:
    """帧数据"""
    frame: np.ndarray                       # 图像帧
    camera_id: int                          # 摄像头 ID
    timestamp: datetime                     # 时间戳
    frame_id: int                           # 帧序号
    resolution: Tuple[int, int] = field(default_factory=lambda: (0, 0))  # 分辨率 (width, height)


class CameraCapture:
    """
    单路摄像头视频采集器
    
    功能：
    - 连接 RTSP 视频流并持续读取帧
    - 自动跳帧以控制处理帧率
    - 断流时自动重连（指数退避）
    - 将帧数据放入队列供下游消费
    
    使用示例：
        config = CaptureConfig(rtsp_url="rtsp://...", camera_id=1)
        capture = CameraCapture(config)
        capture.start()
        
        while True:
            frame_data = capture.get_frame(timeout=1.0)
            if frame_data:
                process(frame_data)
        
        capture.stop()
    """
    
    def __init__(
        self, 
        config: CaptureConfig,
        on_status_change: Optional[Callable[[int, CaptureStatus], None]] = None
    ):
        """
        初始化采集器
        
        Args:
            config: 采集配置
            on_status_change: 状态变更回调函数 (camera_id, status)
        """
        self.config = config
        self.on_status_change = on_status_change
        
        # 状态
        self._status = CaptureStatus.IDLE
        self._cap: Optional[cv2.VideoCapture] = None
        self._frame_queue: queue.Queue[FrameData] = queue.Queue(maxsize=config.queue_size)
        
        # 线程控制
        self._capture_thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()
        self._lock = threading.Lock()
        
        # 统计信息
        self._frame_count = 0
        self._last_frame_time = 0.0
        self._reconnect_count = 0
        self._current_fps = 0.0
        self._resolution = (0, 0)
    
    @property
    def status(self) -> CaptureStatus:
        """获取当前状态"""
        return self._status
    
    @property
    def frame_count(self) -> int:
        """获取已采集帧数"""
        return self._frame_count
    
    @property
    def reconnect_count(self) -> int:
        """获取重连次数"""
        return self._reconnect_count
    
    @property
    def current_fps(self) -> float:
        """获取当前实际帧率"""
        return self._current_fps
    
    @property
    def resolution(self) -> Tuple[int, int]:
        """获取视频分辨率"""
        return self._resolution
    
    @property
    def queue_size(self) -> int:
        """获取当前队列大小"""
        return self._frame_queue.qsize()
    
    def _set_status(self, status: CaptureStatus) -> None:
        """
        设置状态并触发回调
        
        Args:
            status: 新状态
        """
        if self._status != status:
            old_status = self._status
            self._status = status
            logger.info(f"摄像头 {self.config.camera_id} 状态变更: {old_status.value} -> {status.value}")
            
            if self.on_status_change:
                try:
                    self.on_status_change(self.config.camera_id, status)
                except Exception as e:
                    logger.error(f"状态回调执行失败: {e}")
    
    def _build_rtsp_url(self) -> str:
        """
        构建带认证信息的 RTSP URL
        
        Returns:
            完整的 RTSP URL
        """
        url = self.config.rtsp_url
        
        # 如果有用户名密码，嵌入到 URL 中
        if self.config.username and self.config.password:
            if "://" in url:
                protocol, rest = url.split("://", 1)
                url = f"{protocol}://{self.config.username}:{self.config.password}@{rest}"
        
        return url
    
    def _connect(self) -> bool:
        """
        连接到 RTSP 流
        
        Returns:
            连接是否成功
        """
        self._set_status(CaptureStatus.CONNECTING)
        
        try:
            url = self._build_rtsp_url()
            
            # 创建 VideoCapture 对象
            self._cap = cv2.VideoCapture(url, cv2.CAP_FFMPEG)
            
            # 设置缓冲区大小（减少延迟）
            self._cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
            
            # 设置超时
            self._cap.set(cv2.CAP_PROP_OPEN_TIMEOUT_MSEC, int(self.config.connection_timeout * 1000))
            self._cap.set(cv2.CAP_PROP_READ_TIMEOUT_MSEC, int(self.config.read_timeout * 1000))
            
            # 检查是否打开成功
            if not self._cap.isOpened():
                logger.error(f"摄像头 {self.config.camera_id} 连接失败: 无法打开视频流")
                self._set_status(CaptureStatus.ERROR)
                return False
            
            # 读取第一帧验证连接
            ret, frame = self._cap.read()
            if not ret or frame is None:
                logger.error(f"摄像头 {self.config.camera_id} 连接失败: 无法读取首帧")
                self._set_status(CaptureStatus.ERROR)
                return False
            
            # 获取视频信息
            self._resolution = (
                int(self._cap.get(cv2.CAP_PROP_FRAME_WIDTH)),
                int(self._cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
            )
            source_fps = self._cap.get(cv2.CAP_PROP_FPS)
            
            logger.info(
                f"摄像头 {self.config.camera_id} 连接成功: "
                f"分辨率={self._resolution[0]}x{self._resolution[1]}, "
                f"源帧率={source_fps:.1f}, 目标帧率={self.config.target_fps}"
            )
            
            self._set_status(CaptureStatus.RUNNING)
            return True
            
        except Exception as e:
            logger.error(f"摄像头 {self.config.camera_id} 连接异常: {e}")
            self._set_status(CaptureStatus.ERROR)
            return False
    
    def _disconnect(self) -> None:
        """断开连接"""
        if self._cap is not None:
            try:
                self._cap.release()
            except Exception as e:
                logger.warning(f"释放视频捕获对象时出错: {e}")
            finally:
                self._cap = None
    
    def _reconnect(self) -> bool:
        """
        重连到 RTSP 流（指数退避策略）
        
        Returns:
            重连是否成功
        """
        self._set_status(CaptureStatus.RECONNECTING)
        self._disconnect()
        
        interval = self.config.reconnect_interval
        
        while not self._stop_event.is_set():
            self._reconnect_count += 1
            logger.info(f"摄像头 {self.config.camera_id} 第 {self._reconnect_count} 次重连...")
            
            if self._connect():
                logger.info(f"摄像头 {self.config.camera_id} 重连成功")
                return True
            
            # 等待一段时间后重试
            logger.warning(f"摄像头 {self.config.camera_id} 重连失败，{interval:.1f}秒后重试")
            
            # 使用可中断的等待
            if self._stop_event.wait(interval):
                break
            
            # 指数退避
            interval = min(interval * self.config.reconnect_backoff, self.config.max_reconnect_interval)
        
        return False
    
    def _capture_loop(self) -> None:
        """采集主循环"""
        # 首次连接
        if not self._connect():
            if not self._reconnect():
                self._set_status(CaptureStatus.STOPPED)
                return
        
        # 计算跳帧间隔
        frame_interval = 1.0 / self.config.target_fps
        last_capture_time = 0.0
        fps_counter = 0
        fps_start_time = time.time()
        consecutive_failures = 0
        max_consecutive_failures = 10
        
        while not self._stop_event.is_set():
            try:
                # 帧率控制
                current_time = time.time()
                if current_time - last_capture_time < frame_interval:
                    # 跳帧：读取但不处理
                    if self._cap is not None:
                        self._cap.grab()
                    time.sleep(0.001)  # 短暂休眠避免 CPU 占用过高
                    continue
                
                # 读取帧
                if self._cap is None:
                    raise RuntimeError("VideoCapture 对象为空")
                
                ret, frame = self._cap.read()
                
                if not ret or frame is None:
                    consecutive_failures += 1
                    logger.warning(f"摄像头 {self.config.camera_id} 读取帧失败 ({consecutive_failures}/{max_consecutive_failures})")
                    
                    if consecutive_failures >= max_consecutive_failures:
                        logger.error(f"摄像头 {self.config.camera_id} 连续读取失败，尝试重连")
                        if not self._reconnect():
                            break
                        consecutive_failures = 0
                    continue
                
                # 重置失败计数
                consecutive_failures = 0
                
                # 更新时间
                last_capture_time = current_time
                self._last_frame_time = current_time
                self._frame_count += 1
                
                # 计算 FPS
                fps_counter += 1
                fps_elapsed = current_time - fps_start_time
                if fps_elapsed >= 1.0:
                    self._current_fps = fps_counter / fps_elapsed
                    fps_counter = 0
                    fps_start_time = current_time
                
                # 构建帧数据
                frame_data = FrameData(
                    frame=frame,
                    camera_id=self.config.camera_id,
                    timestamp=datetime.now(),
                    frame_id=self._frame_count,
                    resolution=self._resolution
                )
                
                # 放入队列（非阻塞，队列满时丢弃旧帧）
                try:
                    self._frame_queue.put_nowait(frame_data)
                except queue.Full:
                    # 队列满，丢弃最旧的帧
                    try:
                        self._frame_queue.get_nowait()
                        self._frame_queue.put_nowait(frame_data)
                    except queue.Empty:
                        pass
                
            except Exception as e:
                logger.error(f"摄像头 {self.config.camera_id} 采集异常: {e}")
                if not self._reconnect():
                    break
        
        # 清理
        self._disconnect()
        self._set_status(CaptureStatus.STOPPED)
    
    def start(self) -> bool:
        """
        启动采集
        
        Returns:
            是否成功启动
        """
        with self._lock:
            if self._status == CaptureStatus.RUNNING:
                logger.warning(f"摄像头 {self.config.camera_id} 已在运行中")
                return True
            
            if self._capture_thread is not None and self._capture_thread.is_alive():
                logger.warning(f"摄像头 {self.config.camera_id} 采集线程仍在运行")
                return False
            
            # 重置状态
            self._stop_event.clear()
            self._frame_count = 0
            self._reconnect_count = 0
            
            # 清空队列
            while not self._frame_queue.empty():
                try:
                    self._frame_queue.get_nowait()
                except queue.Empty:
                    break
            
            # 启动采集线程
            self._capture_thread = threading.Thread(
                target=self._capture_loop,
                name=f"CameraCapture-{self.config.camera_id}",
                daemon=True
            )
            self._capture_thread.start()
            
            logger.info(f"摄像头 {self.config.camera_id} 采集线程已启动")
            return True
    
    def stop(self, timeout: float = 5.0) -> None:
        """
        停止采集
        
        Args:
            timeout: 等待线程结束的超时时间（秒）
        """
        with self._lock:
            if self._status == CaptureStatus.STOPPED or self._status == CaptureStatus.IDLE:
                return
            
            logger.info(f"摄像头 {self.config.camera_id} 正在停止...")
            
            # 设置停止标志
            self._stop_event.set()
            
            # 等待线程结束
            if self._capture_thread is not None and self._capture_thread.is_alive():
                self._capture_thread.join(timeout=timeout)
                if self._capture_thread.is_alive():
                    logger.warning(f"摄像头 {self.config.camera_id} 采集线程未能在 {timeout}秒内结束")
            
            self._set_status(CaptureStatus.STOPPED)
            logger.info(f"摄像头 {self.config.camera_id} 已停止")
    
    def get_frame(self, timeout: Optional[float] = None) -> Optional[FrameData]:
        """
        从队列获取一帧
        
        Args:
            timeout: 等待超时时间（秒），None 表示非阻塞
            
        Returns:
            帧数据，队列为空时返回 None
        """
        try:
            if timeout is None:
                return self._frame_queue.get_nowait()
            else:
                return self._frame_queue.get(timeout=timeout)
        except queue.Empty:
            return None
    
    def get_stats(self) -> dict:
        """
        获取采集统计信息
        
        Returns:
            统计信息字典
        """
        return {
            "camera_id": self.config.camera_id,
            "status": self._status.value,
            "frame_count": self._frame_count,
            "reconnect_count": self._reconnect_count,
            "current_fps": round(self._current_fps, 2),
            "resolution": f"{self._resolution[0]}x{self._resolution[1]}",
            "queue_size": self._frame_queue.qsize(),
            "queue_capacity": self.config.queue_size,
        }


def test_rtsp_connection(
    rtsp_url: str,
    username: Optional[str] = None,
    password: Optional[str] = None,
    timeout: float = 10.0
) -> dict:
    """
    测试 RTSP 连接
    
    Args:
        rtsp_url: RTSP 地址
        username: 用户名
        password: 密码
        timeout: 超时时间（秒）
        
    Returns:
        测试结果字典，包含 success, resolution, fps, error 等信息
    """
    result = {
        "success": False,
        "resolution": None,
        "fps": None,
        "error": None,
        "response_time": None
    }
    
    start_time = time.time()
    
    try:
        # 构建 URL
        url = rtsp_url
        if username and password:
            if "://" in url:
                protocol, rest = url.split("://", 1)
                url = f"{protocol}://{username}:{password}@{rest}"
        
        # 创建捕获对象
        cap = cv2.VideoCapture(url, cv2.CAP_FFMPEG)
        cap.set(cv2.CAP_PROP_OPEN_TIMEOUT_MSEC, int(timeout * 1000))
        cap.set(cv2.CAP_PROP_READ_TIMEOUT_MSEC, int(timeout * 1000))
        
        if not cap.isOpened():
            result["error"] = "无法打开视频流"
            return result
        
        # 读取一帧
        ret, frame = cap.read()
        if not ret or frame is None:
            result["error"] = "无法读取视频帧"
            cap.release()
            return result
        
        # 获取信息
        result["success"] = True
        result["resolution"] = f"{int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))}x{int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))}"
        result["fps"] = round(cap.get(cv2.CAP_PROP_FPS), 1)
        result["response_time"] = round((time.time() - start_time) * 1000)  # 毫秒
        
        cap.release()
        
    except Exception as e:
        result["error"] = str(e)
    
    return result
