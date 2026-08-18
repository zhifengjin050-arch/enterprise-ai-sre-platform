"""Agent 工具执行时的请求上下文（不改 LangGraph 图结构）。"""
from __future__ import annotations

from contextvars import ContextVar
from typing import Optional

from sqlalchemy.orm import Session as SASession

current_db: ContextVar[Optional[SASession]] = ContextVar("kb_db", default=None)
current_user_id: ContextVar[Optional[int]] = ContextVar("kb_user_id", default=None)
