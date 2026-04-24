"""
一次性修复脚本：更新数据库中配置项的英文描述为中文

执行方式：
    python scripts/fix_config_descriptions.py
"""
import asyncio
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import select
from app.core.database import AsyncSessionLocal
from app.models.system import SystemConfig


# 配置项中文描述映射
CHINESE_DESCRIPTIONS = {
    "face_similarity_threshold": "人脸相似度阈值 (0.0-1.0)",
    "face_detection_min_size": "人脸检测最小尺寸 (像素)",
    "face_detection_confidence": "人脸检测置信度阈值",
    "concurrent_limit": "人脸识别并发限制",
    "alert_cooldown_seconds": "报警冷却时间 (秒)",
    "alert_sound_enabled": "是否启用报警声音",
    "alert_push_enabled": "是否启用报警推送",
    "data_retention_days": "数据保留天数",
    "capture_quality": "截图质量 (1-100)",
    "max_face_images_per_person": "每人最大人脸图片数",
    "system_name": "系统名称",
    "enable_operation_log": "是否记录操作日志",
    "auto_cleanup_enabled": "是否启用自动清理",
    "auto_cleanup_hour": "自动清理执行时间 (0-23时)",
}


async def fix_descriptions():
    """更新数据库中所有配置项的描述为中文"""
    async with AsyncSessionLocal() as session:
        result = await session.execute(select(SystemConfig))
        configs = result.scalars().all()

        updated = 0
        for config in configs:
            new_desc = CHINESE_DESCRIPTIONS.get(config.config_key)
            if new_desc and config.description != new_desc:
                old_desc = config.description
                config.description = new_desc
                updated += 1
                print(f"  [{config.config_key}] {old_desc!r} -> {new_desc!r}")

        if updated > 0:
            await session.commit()
            print(f"\n[OK] 已更新 {updated} 个配置项的描述")
        else:
            print("\n[INFO] 所有配置项描述已经是中文，无需更新")


if __name__ == "__main__":
    print("=" * 50)
    print("修复配置项英文描述 -> 中文")
    print("=" * 50)
    asyncio.run(fix_descriptions())
