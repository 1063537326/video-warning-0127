"""
日志配置模块

功能：
- 控制台输出（彩色格式化）
- 文件日志（按日期分割，自动创建年/月/类型目录）
- 按级别分离日志文件（app / error）
- 可配置保留天数，自动清理过期日志

日志目录结构：
    logs/
    ├── 2026/
    │   ├── 04/
    │   │   ├── app/
    │   │   │   ├── app_2026-04-24.log
    │   │   │   └── app_2026-04-25.log
    │   │   └── error/
    │   │       ├── error_2026-04-24.log
    │   │       └── error_2026-04-25.log
"""
import os
import glob
import logging
import time
from datetime import datetime, timedelta
from logging.handlers import BaseRotatingHandler


class DailyRotatingFileHandler(BaseRotatingHandler):
    """
    按日期轮转的日志 Handler

    每天自动创建新的日志文件，按 年/月/类型 组织目录结构。

    Args:
        base_dir: 日志根目录（如 "logs"）
        log_type: 日志类型名称（如 "app" 或 "error"），同时用作子目录名和文件名前缀
        retention_days: 日志保留天数，超过此天数的日志文件自动删除
        encoding: 文件编码
    """

    def __init__(
        self,
        base_dir: str = "logs",
        log_type: str = "app",
        retention_days: int = 90,
        encoding: str = "utf-8",
    ):
        self.base_dir = os.path.abspath(base_dir)
        self.log_type = log_type
        self.retention_days = retention_days
        self._current_date = self._get_today()

        # 计算当前日志文件路径并初始化
        filepath = self._build_filepath(self._current_date)
        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        super().__init__(filepath, mode="a", encoding=encoding)

    def _get_today(self) -> str:
        """获取当前日期字符串（YYYY-MM-DD）"""
        return time.strftime("%Y-%m-%d")

    def _build_filepath(self, date_str: str) -> str:
        """
        根据日期构建日志文件完整路径

        Args:
            date_str: 日期字符串，格式 YYYY-MM-DD

        Returns:
            完整文件路径，如 logs/2026/04/app/app_2026-04-24.log
        """
        year = date_str[:4]
        month = date_str[5:7]
        filename = f"{self.log_type}_{date_str}.log"
        return os.path.join(self.base_dir, year, month, self.log_type, filename)

    def shouldRollover(self, record: logging.LogRecord) -> int:
        """
        判断是否需要切换到新的日志文件

        当日期发生变化时返回 1 触发轮转。
        """
        today = self._get_today()
        if today != self._current_date:
            return 1
        return 0

    def doRollover(self):
        """
        执行日志文件轮转

        关闭当前文件，切换到新日期的日志文件，并清理过期日志。
        """
        # 关闭当前文件流
        if self.stream:
            self.stream.close()
            self.stream = None  # type: ignore[assignment]

        # 更新日期并切换文件
        self._current_date = self._get_today()
        new_filepath = self._build_filepath(self._current_date)
        os.makedirs(os.path.dirname(new_filepath), exist_ok=True)

        self.baseFilename = new_filepath
        self.stream = self._open()

        # 异步清理过期日志（不阻塞当前写入）
        self._cleanup_old_logs()

    def _cleanup_old_logs(self):
        """
        清理超过保留天数的旧日志文件

        遍历所有匹配的日志文件，删除日期早于保留期限的文件，
        并清理空的日期目录。
        """
        if self.retention_days <= 0:
            return

        cutoff_date = datetime.now() - timedelta(days=self.retention_days)
        cutoff_str = cutoff_date.strftime("%Y-%m-%d")

        # 搜索所有匹配的日志文件：logs/**/log_type/log_type_YYYY-MM-DD.log
        pattern = os.path.join(
            self.base_dir, "**", self.log_type, f"{self.log_type}_*.log"
        )

        for filepath in glob.glob(pattern, recursive=True):
            filename = os.path.basename(filepath)
            # 从文件名中提取日期部分：app_2026-04-24.log -> 2026-04-24
            try:
                date_part = filename.replace(f"{self.log_type}_", "").replace(".log", "")
                if date_part < cutoff_str:
                    os.remove(filepath)
                    # 尝试清理空目录
                    parent_dir = os.path.dirname(filepath)
                    try:
                        os.removedirs(parent_dir)
                    except OSError:
                        pass  # 目录非空，跳过
            except (ValueError, OSError):
                continue


def setup_logging(
    log_dir: str = "logs",
    level: int = logging.INFO,
    retention_days: int = 90,
):
    """
    配置全局日志系统

    Args:
        log_dir: 日志文件根目录
        level: 日志级别
        retention_days: 日志保留天数（默认 90 天）
    """
    # 确保日志根目录存在
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

    # 2. 全量日志文件 Handler（info 及以上）— 按日期分割
    app_handler = DailyRotatingFileHandler(
        base_dir=log_dir,
        log_type="app",
        retention_days=retention_days,
    )
    app_handler.setLevel(logging.INFO)
    app_handler.setFormatter(formatter)
    root_logger.addHandler(app_handler)

    # 3. 错误日志文件 Handler（error 及以上）— 按日期分割
    error_handler = DailyRotatingFileHandler(
        base_dir=log_dir,
        log_type="error",
        retention_days=retention_days,
    )
    error_handler.setLevel(logging.ERROR)
    error_handler.setFormatter(formatter)
    root_logger.addHandler(error_handler)

    # 降低第三方库的日志级别
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)
    logging.getLogger("ultralytics").setLevel(logging.WARNING)
    logging.getLogger("httpx").setLevel(logging.WARNING)

    logging.info(f"日志系统已初始化: 目录={log_dir}, 级别={logging.getLevelName(level)}, 保留={retention_days}天")
