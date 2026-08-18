"""长期记忆系统

保存和检索历史故障记录和解决方案摘要。
基于数据库存储，支持语义搜索。
"""

import logging
from datetime import datetime, timedelta
from typing import List, Optional

from sqlalchemy.orm import Session as SASession
from sqlalchemy import desc

from app.database.models import Message, Conversation, AgentExecution

logger = logging.getLogger(__name__)


class MemoryEntry:
    """记忆条目"""
    def __init__(self, summary: str, date: str, category: str, detail: str = ""):
        self.summary = summary
        self.date = date
        self.category = category
        self.detail = detail

    def to_text(self) -> str:
        return f"[{self.date}] ({self.category}) {self.summary}"
        if self.detail:
            return f"[{self.date}] ({self.category}) {self.summary}\n  详情: {self.detail[:200]}"


def get_recent_failures(
    db: SASession,
    user_id: Optional[int] = None,
    days: int = 30,
    limit: int = 10,
) -> List[MemoryEntry]:
    """获取最近的故障记录

    Args:
        db: 数据库会话
        user_id: 用户 ID
        days: 回溯天数
        limit: 返回条数

    Returns:
        记忆条目列表
    """
    since = datetime.utcnow() - timedelta(days=days)

    q = db.query(AgentExecution).filter(
        AgentExecution.created_at >= since,
        AgentExecution.status == "failed",
    )

    if user_id is not None:
        q = q.filter(AgentExecution.user_id == user_id)

    executions = q.order_by(desc(AgentExecution.created_at)).limit(limit).all()

    entries = []
    for exe in executions:
        detail = exe.error_message or ""
        entries.append(MemoryEntry(
            summary=f"Agent 执行失败 (耗时 {exe.duration:.1f}s)",
            date=exe.created_at.strftime("%Y-%m-%d %H:%M"),
            category="故障",
            detail=detail[:200],
        ))

    return entries


def get_successful_solutions(
    db: SASession,
    user_id: Optional[int] = None,
    days: int = 30,
    limit: int = 10,
) -> List[MemoryEntry]:
    """获取最近的故障解决记录（来自 Agent 成功执行中的对话）

    Args:
        db: 数据库会话
        user_id: 用户 ID
        days: 回溯天数
        limit: 返回条数

    Returns:
        记忆条目列表
    """
    since = datetime.utcnow() - timedelta(days=days)

    q = db.query(Message).filter(
        Message.created_at >= since,
        Message.role == "assistant",
        Message.content.like("%解决方案%"),
    )

    if user_id is not None:
        q = q.join(Conversation).filter(Conversation.user_id == user_id)

    messages = q.order_by(desc(Message.created_at)).limit(limit).all()

    entries = []
    for msg in messages:
        # 提取前 200 字符作为摘要
        summary = msg.content[:150].replace("\n", " ").strip()
        entries.append(MemoryEntry(
            summary=summary,
            date=msg.created_at.strftime("%Y-%m-%d %H:%M"),
            category="解决方案",
            detail=msg.content[:500],
        ))

    return entries


def format_memory_context(
    failures: List[MemoryEntry],
    solutions: List[MemoryEntry],
    max_entries: int = 6,
) -> str:
    """将记忆格式化为 Agent 上下文

    Args:
        failures: 故障记录列表
        solutions: 解决方案列表
        max_entries: 最大条目数

    Returns:
        Markdown 格式的上下文
    """
    parts = []

    if solutions:
        parts.append("## 历史解决方案参考")
        for entry in solutions[:max_entries // 2]:
            parts.append(f"- {entry.to_text()}")

    if failures:
        if parts:
            parts.append("")
        parts.append("## 近期故障记录")
        for entry in failures[:max_entries // 2]:
            parts.append(f"- {entry.to_text()}")

    return "\n".join(parts)