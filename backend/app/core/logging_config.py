"""
日志配置模块

功能：
- 控制台输出（彩色格式化）
- 文件日志（RotatingFileHandler，自动轮转）
- 按级别分离日志文件（info.log / error.log）
"""
import os
import logging
from logging.handlers import RotatingFileHandler


def setup_logging(
    log_dir: str = "logs",
    level: int = logging.INFO,
    max_bytes: int = 10 * 1024 * 1024,  # 10MB
    backup_count: int = 5,
):
    """
    配置全局日志系统

    Args:
        log_dir: 日志文件目录
        level: 日志级别
        max_bytes: 单个日志文件最大大小（字节）
        backup_count: 保留的历史日志文件数
    """
    # 确保日志目录存在
    os.makedirs(log_dir, exist_ok=True)

    # 日志格式
    fmt = "%(asctime)s | %(levelname)-8s | %(name)s:%(lineno)d | %(message)s"
    date_fmt = "%Y-%m-%d %H:%M:%S"
    formatter = logging.Formatter(fmt, datefmt=date_fmt)

    # 根 Logger
    root_logger = logging.getLogger()
    root_logger.setLevel(level)

    # 清除已有 handler（避免重复添加）
    root_logger.handlers.clear()

    # 1. 控制台 Handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(level)
    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)

    # 2. 全量日志文件 Handler（info 及以上）
    info_handler = RotatingFileHandler(
        os.path.join(log_dir, "app.log"),
        maxBytes=max_bytes,
        backupCount=backup_count,
        encoding="utf-8",
    )
    info_handler.setLevel(logging.INFO)
    info_handler.setFormatter(formatter)
    root_logger.addHandler(info_handler)

    # 3. 错误日志文件 Handler（error 及以上）
    error_handler = RotatingFileHandler(
        os.path.join(log_dir, "error.log"),
        maxBytes=max_bytes,
        backupCount=backup_count,
        encoding="utf-8",
    )
    error_handler.setLevel(logging.ERROR)
    error_handler.setFormatter(formatter)
    root_logger.addHandler(error_handler)

    # 降低第三方库的日志级别
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)
    logging.getLogger("ultralytics").setLevel(logging.WARNING)
    logging.getLogger("httpx").setLevel(logging.WARNING)

    logging.info(f"日志系统已初始化: 目录={log_dir}, 级别={logging.getLevelName(level)}")
