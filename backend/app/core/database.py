"""
数据库连接模块
- 异步数据库会话管理
- 数据库引擎配置
"""
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.orm import declarative_base

from app.core.config import settings

# 创建异步数据库引擎
engine = create_async_engine(
    settings.DATABASE_URL,
    echo=settings.DEBUG,
    future=True,
    # 连接池配置
    pool_size=10,           # 基础连接池大小
    max_overflow=20,        # 超出 pool_size 后允许的额外连接数
    pool_recycle=3600,      # 每小时回收连接（防止 DB 端超时断开）
    pool_pre_ping=True,     # 使用前检测连接是否存活
)

# 创建异步会话工厂
AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)

# 声明基类
Base = declarative_base()


async def get_db() -> AsyncSession:
    """获取数据库会话"""
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()
