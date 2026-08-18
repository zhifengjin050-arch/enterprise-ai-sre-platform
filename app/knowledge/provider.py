"""统一文档检索门面：私有上传 ∪ 组织 Hub 文档。"""
from __future__ import annotations

from sqlalchemy.orm import Session as SASession

from app.database.models import KnowledgeDocument, User
from app.knowledge.access import document_visible
from app.rag.retriever import retrieve_knowledge


def search_documents(query: str, db: SASession, user: User | None, top_k: int = 5) -> list[dict]:
    if user is None:
        return []
    hits = retrieve_knowledge(
        query,
        db,
        top_k=top_k,
        user_id=user.id,
        organization_id=user.organization_id,
    )
    return hits


def get_document(db: SASession, user: User, document_id: int) -> KnowledgeDocument | None:
    doc = db.query(KnowledgeDocument).filter(KnowledgeDocument.id == document_id).first()
    if doc is None or not document_visible(doc, user):
        return None
    return doc
