import cv2
import numpy as np
import time
import logging
import os
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Tuple, Any
from dataclasses import dataclass, field
from ultralytics import YOLO

from app.core.config import settings
from app.models.alert import AlertLevel

logger = logging.getLogger(__name__)

@dataclass
class TrackerEvent:
    """追踪器产生的事件"""
    type: str  # 'FACE_DETECTED', 'BODY_DETECTED', 'PERSON_LEFT'
    track_id: int
    timestamp: datetime
    
    # 图片数据 (BGR numpy array)
    face_image: Optional[np.ndarray] = None
    body_image: Optional[np.ndarray] = None
    full_image: Optional[np.ndarray] = None
    
    # 评分与框
    face_score: float = 0.0
    body_score: float = 0.0
    face_box: Optional[List[int]] = None # [x, y, w, h]
    body_box: Optional[List[int]] = None # [x, y, w, h]
    
    # 状态
    is_best_shot: bool = False
    alert_level: AlertLevel = AlertLevel.INFO

class TrackedPerson:
    """管理单个被追踪人员的状态"""
    def __init__(self, track_id: int, start_time: datetime):
        self.id = track_id
        self.start_time = start_time
        self.last_seen_time = start_time
        
        # 最佳记录
        self.best_face_score = 0.0
        self.best_face_image: Optional[np.ndarray] = None
        self.best_face_box: Optional[List[int]] = None
        
        self.best_body_score = 0.0
        self.best_body_image: Optional[np.ndarray] = None
        self.best_body_box: Optional[List[int]] = None
        
        # 保存状态
        self.last_save_time = 0.0 # timestamp
        self.saved_face_score = 0.0
        
        # 状态标记
        self.is_stranger_body_reported = False

    def update_body(self, frame: np.ndarray, rect: Tuple[int, int, int, int]):
        """更新身体分数"""
        x, y, w, h = rect
        h_img, w_img = frame.shape[:2]
        
        # 简单评分: 面积 * 中心度
        cx, cy = x + w/2, y + h/2
        img_cx, img_cy = w_img/2, h_img/2
        dist = np.sqrt((cx - img_cx)**2 + (cy - img_cy)**2)
        max_dist = np.sqrt(img_cx**2 + img_cy**2)
        centrality = 1.0 - (dist / max_dist)
        
        area_ratio = (w * h) / (w_img * h_img)
        score = area_ratio * (centrality + 0.5) * 1000 # Scaling
        
        if score > self.best_body_score:
            self.best_body_score = score
            self.best_body_box = list(rect)
            self.best_body_image = frame.copy() # 保存当前全帧作为最佳身体帧的基础
            
    def update_face(self, frame: np.ndarray, rect: Tuple[int, int, int, int], conf: float):
        """更新人脸分数"""
        score = conf * 1000.0
        if score > self.best_face_score:
            self.best_face_score = score
            self.best_face_box = list(rect)
            self.best_face_image = frame.copy()

class YoloTracker:
    """YOLO + ByteTrack 追踪器"""
    
    def __init__(self, body_model, face_model):
        self.model_body = body_model
        self.model_face = face_model
        self.is_loaded = (body_model is not None and face_model is not None)
            
        # 状态
        self.tracked_persons: Dict[int, TrackedPerson] = {}
        self.disappeared_count: Dict[int, int] = {}
        
        # 配置
        self.conf_body = settings.CONF_BODY
        self.conf_face = settings.CONF_FACE
        self.tracker_config = settings.TRACKER_TYPE
        
        # 离场判断
        self.max_disappeared = 40 
        self.min_body_ratio = 0.05 # 略微降低限制

    def process(self, frame: np.ndarray, timestamp: datetime) -> Tuple[np.ndarray, List[TrackerEvent]]:
        """处理一帧"""
        if not self.is_loaded or frame is None:
            return frame, []
            
        events = []
        h_img, w_img = frame.shape[:2]
        
        # 1. 身体追踪 (ByteTrack)
        # persist=True 维持追踪状态
        results_track = self.model_body.track(
            frame, 
            persist=True, 
            tracker=self.tracker_config,
            classes=[0], # Person class
            conf=self.conf_body,
            verbose=False
        )
        
        current_ids = []
        annotated_frame = results_track[0].plot() # 绘制追踪结果用于直播
        
        if results_track[0].boxes.id is not None:
            boxes = results_track[0].boxes.xyxy.cpu().numpy()
            track_ids = results_track[0].boxes.id.int().cpu().numpy()
            
            for box, track_id in zip(boxes, track_ids):
                x1, y1, x2, y2 = map(int, box)
                w, h = x2 - x1, y2 - y1
                
                if h < h_img * self.min_body_ratio: continue
                
                current_ids.append(track_id)
                
                # 注册新用户
                if track_id not in self.tracked_persons:
                    self.tracked_persons[track_id] = TrackedPerson(track_id, timestamp)
                    self.disappeared_count[track_id] = 0
                    # 刚进入也可以触发一个 BODY_ENTER 事件(可选)
                
                person = self.tracked_persons[track_id]
                person.last_seen_time = timestamp
                person.update_body(annotated_frame, (x1, y1, w, h))
                self.disappeared_count[track_id] = 0
                
        # 2. 筛选在 ROI 区域内的人
        roi_person_ids = []
        if len(current_ids) > 0:
            roi_config = settings.DETECTION_ROI
            # roi_config: [x_min, y_min, x_max, y_max] 比例
            if roi_config and len(roi_config) == 4:
                rmin_x, rmin_y, rmax_x, rmax_y = roi_config
                # 转换绝对坐标
                roi_x1 = int(rmin_x * w_img)
                roi_y1 = int(rmin_y * h_img)
                roi_x2 = int(rmax_x * w_img)
                roi_y2 = int(rmax_y * h_img)
                
                # 绘制 ROI 框 (调试用，可选)
                # cv2.rectangle(annotated_frame, (roi_x1, roi_y1), (roi_x2, roi_y2), (255, 255, 0), 2)
                
                for track_id, box in zip(track_ids, boxes):
                    bx1, by1, bx2, by2 = map(int, box)
                    # 使用身体中心点判断位置 (bx1+bx2)/2, (by1+by2)/2
                    center_x = (bx1 + bx2) / 2
                    center_y = (by1 + by2) / 2
                    
                    if (roi_x1 <= center_x <= roi_x2) and (roi_y1 <= center_y <= roi_y2):
                        roi_person_ids.append(track_id)
            else:
                #如果没有配置 roi, 则所有人都在 roi
                roi_person_ids = list(current_ids)

        # 3. 人脸检测 (仅当 ROI 区域有人在场时)
        if len(roi_person_ids) > 0:
            results_face = self.model_face(frame, conf=self.conf_face, verbose=False)
            
            for r in results_face:
                for box in r.boxes:
                    fx1, fy1, fx2, fy2 = map(int, box.xyxy[0])
                    conf = float(box.conf[0])
                    fw, fh = fx2 - fx1, fy2 - fy1
                    
                    # 匹配人脸到身体
                    face_center = (fx1 + fw/2, fy1 + fh/2)
                    best_match_id = self._match_face_to_body(face_center, boxes, track_ids)
                    
                    # 只处理在 ROI 内的人
                    if best_match_id in roi_person_ids:
                        person = self.tracked_persons[best_match_id]
                        person.update_face(frame, (fx1, fy1, fw, fh), conf)
                        
                        # 检查是否是最佳人脸，生成事件
                        if self._should_save_face(person, conf * 1000.0):
                            events.append(self._create_face_event(person, frame))
                            
        # 3. 检查陌生人徘徊 (无脸但停留久)
        for track_id in current_ids:
            if track_id in self.tracked_persons:
                person = self.tracked_persons[track_id]
                # 如果没有好的脸，且停留超过 1 秒 (User requested immediate), 且未报告过
                duration = (timestamp - person.start_time).total_seconds()
                if person.best_face_score < 300 and duration > 1.0 and not person.is_stranger_body_reported:
                    events.append(self._create_body_event(person, frame))
                    person.is_stranger_body_reported = True
        
        # 4. 离场检测
        active_ids_set = set(current_ids)
        track_ids_list = list(self.tracked_persons.keys())
        
        for tid in track_ids_list:
            if tid not in active_ids_set:
                self.disappeared_count[tid] += 1
                if self.disappeared_count[tid] > self.max_disappeared:
                    # 确认离场
                    # events.append(TrackerEvent(type="PERSON_LEFT", track_id=tid, timestamp=timestamp))
                    del self.tracked_persons[tid]
                    del self.disappeared_count[tid]
                    
        return annotated_frame, events
    
    def _match_face_to_body(self, face_center, body_boxes, track_ids) -> Optional[int]:
        """简单的中心距离匹配"""
        min_dist = float('inf')
        best_id = None
        
        for box, tid in zip(body_boxes, track_ids):
            bx1, by1, bx2, by2 = map(int, box)
            bw, bh = bx2 - bx1, by2 - by1
            b_cx, b_cy = bx1 + bw/2, by1 + bh/2
            
            # 人脸必须在身体框内或附近
            if not (bx1 - bw*0.2 <= face_center[0] <= bx2 + bw*0.2 and 
                    by1 - bh*0.2 <= face_center[1] <= by2 + bh*0.2):
                continue

            dist = (b_cx - face_center[0])**2 + (b_cy - face_center[1])**2
            if dist < min_dist:
                min_dist = dist
                best_id = tid
        
        return best_id

    def _should_save_face(self, person: TrackedPerson, current_score: float) -> bool:
        """判断是否应该触发保存/识别"""
        # 冷却时间 check
        now_ts = time.time()
        if now_ts - person.last_save_time < settings.ALERT_COOLDOWN_SECONDS:
            # 即使在冷却中，如果分数提升很大 (Fast Pass)，也可以触发
            if current_score < person.saved_face_score * 1.2:
                return False
        
        # 阈值 check
        if current_score < 600: # 基础质量分
             return False
             
        # 提升 check
        if current_score > person.saved_face_score * 1.05: # 提升5%
            person.last_save_time = now_ts
            person.saved_face_score = current_score
            return True
            
        return False
        
    def _create_face_event(self, person: TrackedPerson, frame: np.ndarray) -> TrackerEvent:
        fx, fy, fw, fh = person.best_face_box
        # 裁剪人脸
        h, w = frame.shape[:2]
        pad = int(fw * 0.3)
        y1, y2 = max(0, fy-pad), min(h, fy+fh+pad)
        x1, x2 = max(0, fx-pad), min(w, fx+fw+pad)
        face_img = frame[y1:y2, x1:x2].copy()
        
        # 裁剪全身
        bx, by, bw, bh = person.best_body_box
        pad_b = int(bw * 0.1)
        y1b, y2b = max(0, by-pad_b), min(h, by+bh+pad_b)
        x1b, x2b = max(0, bx-pad_b), min(w, bx+bw+pad_b)
        body_img = frame[y1b:y2b, x1b:x2b].copy()
        
        return TrackerEvent(
            type="FACE_DETECTED",
            track_id=person.id,
            timestamp=datetime.now(),
            face_image=face_img,
            body_image=body_img,
            full_image=frame.copy(),
            face_score=person.best_face_score,
            body_score=person.best_body_score,
            face_box=person.best_face_box,
            body_box=person.best_body_box,
            is_best_shot=True,
            alert_level=AlertLevel.CRITICAL # 默认先设为 Critical, 后续 Decision 判断是否降级
        )

    def _create_body_event(self, person: TrackedPerson, frame: np.ndarray) -> TrackerEvent:
        # 仅裁剪全身
        h, w = frame.shape[:2]
        bx, by, bw, bh = person.best_body_box
        pad_b = int(bw * 0.1)
        y1b, y2b = max(0, by-pad_b), min(h, by+bh+pad_b)
        x1b, x2b = max(0, bx-pad_b), min(w, bx+bw+pad_b)
        body_img = frame[y1b:y2b, x1b:x2b].copy()
        
        return TrackerEvent(
            type="BODY_DETECTED",
            track_id=person.id,
            timestamp=datetime.now(),
            body_image=body_img,
            full_image=frame.copy(),
            body_score=person.best_body_score,
            body_box=person.best_body_box,
            alert_level=AlertLevel.WARNING
        )
