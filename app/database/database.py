"""数据库引擎配置

- 根据 database_url 自动选择 SQLite (同步) 或 PostgreSQL (同步，Alembic 兼容)
- 提供 get_db_type() 辅助函数
- PostgreSQL 生产池: pool_size=20, max_overflow=30, pool_recycle=3600
"""

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase
from app.config import settings


def get_db_type() -> str:
    """返回当前数据库类型: 'sqlite' 或 'postgresql'"""
    url = settings.database_url
    if url.startswith("sqlite"):
        return "sqlite"
    return "postgresql"


def _create_engine():
    url = settings.database_url
    if url.startswith("sqlite"):
        return create_engine(url, pool_pre_ping=True, echo=False)
    return create_engine(
        url,
        pool_pre_ping=True,
        pool_size=20,
        max_overflow=30,
        pool_recycle=3600,
        echo=False,
    )


engine = _create_engine()


class Base(DeclarativeBase):
    """SQLAlchemy ORM 基类"""
    pass
