"""
数据清理定时任务
- 过期报警记录清理
- 过期截图文件清理
"""
import os
import shutil
import time
import logging
import asyncio
from datetime import datetime, timedelta
from sqlalchemy import delete, select
from app.core.config import settings
from app.core.database import AsyncSessionLocal
from app.models.alert import AlertLog
from app.models.system import CleanupLog
from typing import List

logger = logging.getLogger(__name__)

def _cleanup_files_sync(captures_dir: str, cutoff_date: datetime) -> int:
    """
    同步文件清理函数 (用于在 executor 中运行)
    """
    files_deleted = 0
    try:
        if not os.path.exists(captures_dir):
            return 0
            
        for date_folder in os.listdir(captures_dir):
            folder_path = os.path.join(captures_dir, date_folder)
            if not os.path.isdir(folder_path): continue
            
            # Check date folder name YYYYMMDD
            try:
                folder_date = datetime.strptime(date_folder, "%Y%m%d")
                if folder_date < cutoff_date:
                    # 准确统计文件数量
                    file_count = 0
                    for _, _, files in os.walk(folder_path):
                        file_count += len(files)
                    
                    shutil.rmtree(folder_path)
                    logger.info(f"删除过期文件夹: {folder_path}, 包含 {file_count} 个文件")
                    files_deleted += file_count
                    continue
            except ValueError:
                continue
    except Exception as e:
        logger.error(f"文件清理失败: {e}")
    return files_deleted

async def cleanup_expired_data():
    """
    清理过期数据 (异步)
    """
    retention_days = settings.DATA_RETENTION_DAYS
    logger.info(f"开始执行数据清理，保留天数: {retention_days}")
    
    async with AsyncSessionLocal() as db:
        cleanup_log = CleanupLog(
            cleanup_type="auto_daily",
            started_at=datetime.now(),
            status="running"
        )
        db.add(cleanup_log)
        await db.commit()
        
        try:
            # 1. 清理过期 DB 记录
            cutoff_date = datetime.now() - timedelta(days=retention_days)
            
            # 使用 execute(delete(...))
            result = await db.execute(
                delete(AlertLog).where(AlertLog.created_at < cutoff_date)
            )
            deleted_count = result.rowcount
            
            # 2. 清理过期文件
            # 遍历 captures 目录
            captures_dir = settings.CAPTURES_DIR
            files_deleted = 0
            
            # 文件操作比较耗时，为了不阻塞 loop，可以使用 run_in_executor
            loop = asyncio.get_running_loop()
            files_deleted = await loop.run_in_executor(None, _cleanup_files_sync, captures_dir, cutoff_date)
                        
            cleanup_log.records_deleted = deleted_count
            cleanup_log.files_deleted = files_deleted
            cleanup_log.finished_at = datetime.now()
            cleanup_log.status = "success"
            await db.commit()
            
            logger.info(f"数据清理完成. Del DB: {deleted_count}, Del Files: {files_deleted}")
            
        except Exception as e:
            logger.error(f"数据清理失败: {e}")
            cleanup_log.status = "failed"
            cleanup_log.error_message = str(e)[0:500]
            await db.commit()
