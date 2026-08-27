"""会话短期记忆

负责加载用户历史会话消息，构建多轮对话上下文。
"""

import logging
from typing import List, Optional

from sqlalchemy.orm import Session as SASession
from app.database.models import Conversation, Message

logger = logging.getLogger(__name__)


def load_conversation_history(
    conversation_id: int,
    db: SASession,
    user_id: Optional[int] = None,
    max_messages: int = 20,
) -> List[dict]:
    """加载会话历史消息

    Args:
        conversation_id: 会话 ID
        db: 数据库会话
        user_id: 用户 ID（用于验证）
        max_messages: 返回的最大消息数

    Returns:
        消息列表（按时间升序），每项含 role 和 content
    """
    conv = db.query(Conversation).filter(
        Conversation.id == conversation_id,
    )

    if user_id is not None:
        conv = conv.filter(Conversation.user_id == user_id)

    conv = conv.first()
    if conv is None:
        logger.warning("会话不存在: id=%d", conversation_id)
        return []

    # 获取最近的消息（取最新的 max_messages 条）
    messages = (
        db.query(Message)
        .filter(Message.conversation_id == conversation_id)
        .order_by(Message.created_at.asc())
        .limit(max_messages)
        .all()
    )

    history = []
    for msg in messages:
        history.append({
            "role": msg.role,
            "content": msg.content,
        })

    logger.debug(
        "加载会话历史: conversation_id=%d messages=%d",
        conversation_id, len(history),
    )
    return history
