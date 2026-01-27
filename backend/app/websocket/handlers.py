"""
WebSocket 消息处理器

功能：
- 报警消息推送
- 摄像头状态推送
- 系统通知推送
- 引擎状态推送
"""
import logging
from typing import Optional, List
from datetime import datetime

from .manager import manager, MessageType
from app.core.database import AsyncSessionLocal
from app.models.alert import AlertLog, AlertType, AlertLevel, AlertStatus
from sqlalchemy import select

logger = logging.getLogger(__name__)


async def push_alert(alert_data: dict) -> int:
    """
    推送报警消息
    
    Args:
        alert_data: 报警数据字典，包含：
            - camera_id: 摄像头 ID
            - alert_type: 报警类型 (stranger/known/blacklist)
            - person_id: 人员 ID（陌生人为 None）
            - person_name: 人员姓名
            - confidence: 识别置信度
            - face_image: 人脸图像 Base64
            - timestamp: 时间戳
            
    Returns:
        成功发送的连接数
    """
    camera_id = alert_data.get("camera_id")
    
    message = {
        "type": MessageType.ALERT.value,
        "data": alert_data,
        "timestamp": datetime.now().isoformat()
    }
    
    # 优先推送给订阅了该摄像头的客户端
    if camera_id is not None:
        count = await manager.broadcast_to_camera_subscribers(camera_id, message)
        # 如果没有订阅者，则广播给所有人
        if count == 0:
            count = await manager.broadcast(message)
    else:
        count = await manager.broadcast(message)
    
    logger.info(f"推送报警消息: camera={camera_id}, type={alert_data.get('alert_type')}, sent={count}")
    return count


async def push_camera_status(
    camera_id: int,
    status: str,
    extra_data: Optional[dict] = None
) -> int:
    """
    推送摄像头状态变更
    
    Args:
        camera_id: 摄像头 ID
        status: 状态 (online/offline/error/connecting)
        extra_data: 额外数据
        
    Returns:
        成功发送的连接数
    """
    message = {
        "type": MessageType.CAMERA_STATUS.value,
        "data": {
            "camera_id": camera_id,
            "status": status,
            **(extra_data or {})
        },
        "timestamp": datetime.now().isoformat()
    }
    
    count = await manager.broadcast(message)
    logger.debug(f"推送摄像头状态: camera={camera_id}, status={status}, sent={count}")
    return count


async def push_batch_camera_status(statuses: List[dict]) -> int:
    """
    批量推送摄像头状态
    
    Args:
        statuses: 状态列表，每项包含 camera_id 和 status
        
    Returns:
        成功发送的连接数
    """
    message = {
        "type": MessageType.CAMERA_STATUS.value,
        "data": {
            "batch": True,
            "statuses": statuses
        },
        "timestamp": datetime.now().isoformat()
    }
    
    count = await manager.broadcast(message)
    logger.debug(f"批量推送摄像头状态: count={len(statuses)}, sent={count}")
    return count


async def push_system_notification(
    message_text: str,
    level: str = "info",
    title: Optional[str] = None,
    duration: int = 5000
) -> int:
    """
    推送系统通知
    
    Args:
        message_text: 通知内容
        level: 级别 (info/success/warning/error)
        title: 标题
        duration: 显示时长（毫秒）
        
    Returns:
        成功发送的连接数
    """
    message = {
        "type": MessageType.NOTIFICATION.value,
        "data": {
            "message": message_text,
            "level": level,
            "title": title,
            "duration": duration
        },
        "timestamp": datetime.now().isoformat()
    }
    
    count = await manager.broadcast(message)
    logger.info(f"推送系统通知: level={level}, message={message_text[:50]}, sent={count}")
    return count


async def push_engine_status(
    status: str,
    camera_count: int = 0,
    running_count: int = 0,
    extra_data: Optional[dict] = None
) -> int:
    """
    推送引擎状态
    
    Args:
        status: 引擎状态 (stopped/starting/running/stopping/error)
        camera_count: 摄像头总数
        running_count: 运行中的摄像头数
        extra_data: 额外数据
        
    Returns:
        成功发送的连接数
    """
    message = {
        "type": MessageType.ENGINE_STATUS.value,
        "data": {
            "status": status,
            "camera_count": camera_count,
            "running_count": running_count,
            **(extra_data or {})
        },
        "timestamp": datetime.now().isoformat()
    }
    
    count = await manager.broadcast(message)
    logger.debug(f"推送引擎状态: status={status}, sent={count}")
    return count


async def push_to_user(user_id: int, message_type: str, data: dict) -> int:
    """
    推送消息给指定用户
    
    Args:
        user_id: 用户 ID
        message_type: 消息类型
        data: 消息数据
        
    Returns:
        成功发送的连接数
    """
    message = {
        "type": message_type,
        "data": data,
        "timestamp": datetime.now().isoformat()
    }
    
    count = await manager.send_to_user(user_id, message)
    logger.debug(f"推送消息给用户: user={user_id}, type={message_type}, sent={count}")
    return count


# 创建引擎报警回调（用于 EngineManager）
async def engine_alert_callback(alert_data: dict) -> None:
    """
    引擎报警回调
    
    供 EngineManager 调用，将报警推送到 WebSocket
    
    Args:
        alert_data: 报警数据
    """
    # 1. 保存到数据库 (带合并逻辑)
    should_push = True
    
    try:
        async with AsyncSessionLocal() as db:
            track_id = alert_data.get("track_id")
            camera_id = alert_data.get("camera_id")
            alert_level = alert_data.get("alert_level")
            
            # 查找该 track_id 是否已有活跃/未处理的记录
            existing_alert = None
            if track_id:
                stmt = select(AlertLog).where(
                    AlertLog.track_id == track_id,
                    AlertLog.camera_id == int(camera_id)
                ).order_by(AlertLog.created_at.desc()).limit(1)
                result = await db.execute(stmt)
                existing_alert = result.scalars().first()
                
            if existing_alert:
                # === 合并逻辑 ===
                # 如果是已知人员降级
                if alert_data.get("alert_type") == AlertType.KNOWN.value:
                     # 之前是陌生人，现在认出来了 -> 降级
                     existing_alert.alert_type = AlertType.KNOWN
                     existing_alert.alert_level = AlertLevel.INFO
                     existing_alert.person_id = alert_data.get("person_id") 
                     if alert_data.get("person_name"):
                        extra = existing_alert.extra_data or {}
                        extra["person_name"] = alert_data.get("person_name")
                        existing_alert.extra_data = extra
                     existing_alert.status = AlertStatus.PROCESSED # 自动标记为已处理(因为是自己人)
                     
                     # 更新图片
                     if alert_data.get('face_image'): existing_alert.face_image_path = alert_data.get('face_image')
                     
                     # 修正推送数据类型，让前端知道是 更新
                     alert_data['is_update'] = True
                     alert_data['original_alert_id'] = existing_alert.id
                     
                # 如果是陌生人升级 (Body -> Face)
                elif existing_alert.alert_level == AlertLevel.INFO and alert_level == AlertLevel.CRITICAL:
                     existing_alert.alert_level = AlertLevel.CRITICAL
                     existing_alert.alert_type = AlertType.STRANGER
                     existing_alert.face_image_path = alert_data.get('face_image')
                     existing_alert.status = AlertStatus.PENDING # 重新变回待处理
                     
                     alert_data['is_update'] = True
                     alert_data['original_alert_id'] = existing_alert.id
                     
                # 如果只是普通更新 (图片更好了)
                else:
                     # 更新图片
                     if alert_data.get('face_image'): existing_alert.face_image_path = alert_data.get('face_image')
                     if alert_data.get('body_image'): existing_alert.best_body_image_path = alert_data.get('body_image')
                     
                     # 只有显著变化才推送
                     should_push = False 
                
                existing_alert.end_time = datetime.now()
                # 追加 image_history
                current_history = list(existing_alert.image_history) if existing_alert.image_history else []
                current_history.append({
                    "ts": datetime.now().isoformat(),
                    "face": alert_data.get('face_image'),
                    "score": alert_data.get('score')
                })
                existing_alert.image_history = current_history
                
                await db.commit()
                await db.refresh(existing_alert)
                alert_data['id'] = existing_alert.id
                
            else:
                # === 新建逻辑 ===
                new_alert = AlertLog(
                    track_id=track_id,
                    camera_id=int(camera_id),
                    alert_type=alert_data.get("alert_type"),
                    alert_level=alert_data.get("alert_level"),
                    confidence=alert_data.get("score"), 
                    face_image_path=alert_data.get("face_image"),
                    best_body_image_path=alert_data.get("body_image"),
                    full_image_path=alert_data.get("full_image"),
                    image_history=[{
                        "ts": datetime.now().isoformat(),
                        "face": alert_data.get('face_image'),
                        "score": alert_data.get('score')
                    }],
                    extra_data={"person_name": alert_data.get("person_name")}
                )
                db.add(new_alert)
                await db.commit()
                await db.refresh(new_alert)
                alert_data['id'] = new_alert.id
            
    except Exception as e:
        logger.error(f"报警入库失败: {e}")
        # db.rollback() # Not needed with async context manager generally, but safety
        # If we were in a transaction that failed, we might need it.
        # But AsyncSessionLocal context manager closes the session.

    # 2. 推送 WebSocket
    if should_push:
        await push_alert(alert_data)


async def engine_status_callback(camera_id: int, status: str) -> None:
    """
    引擎摄像头状态回调
    
    供 EngineManager 调用，将状态变更推送到 WebSocket
    
    Args:
        camera_id: 摄像头 ID
        status: 状态
    """
    await push_camera_status(camera_id, status)
