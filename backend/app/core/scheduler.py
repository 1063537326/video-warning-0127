import logging
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from app.tasks.cleanup import cleanup_expired_data

logger = logging.getLogger(__name__)

_scheduler = None

async def init_scheduler():
    """初始化并启动定时任务调度器"""
    global _scheduler
    _scheduler = AsyncIOScheduler()
    
    # 每天凌晨 3:00 执行清理
    _scheduler.add_job(cleanup_expired_data, 'cron', hour=3, minute=0)
    
    _scheduler.start()
    logger.info("定时任务调度器已启动")

async def shutdown_scheduler():
    """关闭调度器"""
    global _scheduler
    if _scheduler:
        _scheduler.shutdown()
        logger.info("定时任务调度器已关闭")
