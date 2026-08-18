"""数据库会话管理

提供 get_db 依赖，用于 FastAPI 路由。
"""

from typing import Generator
from sqlalchemy.orm import Session as SASession
from app.database.database import engine, Base


def init_db():
    """初始化数据库，创建所有表（开发/SQLite 模式）"""
    import app.database.models  # noqa: F401
    Base.metadata.create_all(bind=engine)
    _sqlite_upgrade_columns()


def _sqlite_upgrade_columns() -> None:
    """已有 SQLite 库补齐 v3.x 新增列，避免破坏开发库。"""
    from sqlalchemy import text, inspect
    from app.database.database import get_db_type

    if get_db_type() != "sqlite":
        return
    inspector = inspect(engine)
    tables = set(inspector.get_table_names())
    with engine.begin() as conn:
        if "users" in tables:
            cols = {c["name"] for c in inspector.get_columns("users")}
        if "knowledge_documents" in tables:
            cols = {c["name"] for c in inspector.get_columns("knowledge_documents")}
            extras = [
                ("organization_id", "INTEGER"),
                ("source_id", "INTEGER"),
                ("external_id", "VARCHAR(200)"),
                ("external_url", "VARCHAR(500)"),
                ("checksum", "VARCHAR(64)"),
                ("status", "VARCHAR(20) DEFAULT 'active'"),
            ]
            for name, decl in extras:
                if name not in cols:
                    conn.execute(text(f"ALTER TABLE knowledge_documents ADD COLUMN {name} {decl}"))


def init_db_with_alembic():
    """初始化数据库（生产环境），使用 Alembic 迁移"""
    from alembic.config import Config
    from alembic import command
    alembic_cfg = Config("alembic.ini")
    command.upgrade(alembic_cfg, "head")


def get_local_session() -> SASession:
    """创建新的数据库会话"""
    return SASession(bind=engine, autocommit=False, autoflush=False)


def get_db() -> Generator[SASession, None, None]:
    """FastAPI 依赖：获取数据库会话"""
    db = get_local_session()
    try:
        yield db
    finally:
        db.close()