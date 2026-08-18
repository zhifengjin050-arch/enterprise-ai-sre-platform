"""内置知识库工具（非 MCP）。"""
from __future__ import annotations

from langchain.tools import tool

from app.knowledge.context import current_db, current_user_id
from app.knowledge.provider import get_document, search_documents


def _load_user():
    db = current_db.get()
    user_id = current_user_id.get()
    if db is None or user_id is None:
        return None, None
    from app.database.models import User
    user = db.query(User).filter(User.id == user_id).first()
    return db, user


@tool
def knowledge_search(query: str, top_k: int = 5) -> list:
    """在企业知识库中搜索 SOP / 手册摘要。当自动注入的上下文不够、用户问「按手册怎么排」时使用。返回标题、来源、摘要，不含全文。"""
    db, user = _load_user()
    if user is None:
        return [{"error": "未登录，无法检索知识库"}]
    k = max(1, min(int(top_k or 5), 10))
    hits = search_documents(query, db, user, top_k=k)
    return [
        {
            "title": h.get("title") or "",
            "source_type": h.get("source") or "manual",
            "snippet": (h.get("content") or "")[:400],
            "score": h.get("score"),
            "document_id": h.get("document_id"),
        }
        for h in hits
    ]


@tool
def knowledge_get_document(document_id: int) -> dict:
    """按文档 ID 读取企业知识库中一篇文档的标题与截断正文（最多约 4000 字）。必须是当前用户可见的文档。"""
    db, user = _load_user()
    if user is None:
        return {"error": "未登录，无法读取知识库文档"}
    try:
        doc_id = int(document_id)
    except (TypeError, ValueError):
        return {"error": "无效的 document_id"}
    doc = get_document(db, user, doc_id)
    if doc is None:
        return {"error": "文档不存在或无权访问"}
    return {
        "document_id": doc.id,
        "title": doc.title,
        "source_type": doc.source,
        "content": (doc.content or "")[:4000],
    }
