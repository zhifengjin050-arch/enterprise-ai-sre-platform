"""向量存储

基于内存 + 数据库的向量存储实现。
与 pgvector 兼容的设计，但同时支持 SQLite 开发环境。

存储策略：
- 向量以 JSON 格式存储在 knowledge_chunks 表的 embedding 字段
- 检索时使用余弦相似度进行比对
- 支持 pgvector 的 SQL 级别向量检索（PostgreSQL 生产环境）
"""

import json
import logging
import math
from typing import List, Optional, Tuple

from sqlalchemy import or_, and_
from sqlalchemy.orm import Session as SASession

from app.database.database import engine, Base
from app.database.session import get_local_session
from app.rag.embeddings import embedding_service

logger = logging.getLogger(__name__)


def _cosine_similarity(vec_a: List[float], vec_b: List[float]) -> float:
    """计算余弦相似度"""
    dot = sum(a * b for a, b in zip(vec_a, vec_b))
    norm_a = math.sqrt(sum(a * a for a in vec_a))
    norm_b = math.sqrt(sum(b * b for b in vec_b))
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return dot / (norm_a * norm_b)


def store_chunk_embedding(db: SASession, chunk_id: int, embedding: List[float]):
    """将向量存储到数据库

    Args:
        db: 数据库会话
        chunk_id: 文本块 ID
        embedding: 向量数组
    """
    from app.database.models import KnowledgeChunk

    chunk = db.query(KnowledgeChunk).filter(KnowledgeChunk.id == chunk_id).first()
    if chunk is None:
        logger.warning("chunk 不存在: id=%d", chunk_id)
        return

    chunk.embedding = json.dumps(embedding)
    db.commit()


def similarity_search(
    query: str,
    db: SASession,
    top_k: int = 5,
    user_id: Optional[int] = None,
    organization_id: Optional[int] = None,
) -> List[Tuple[dict, float]]:
    """语义相似度搜索。未指定 user_id/organization_id 时不扫描全库。"""
    from app.database.models import KnowledgeChunk, KnowledgeDocument

    if user_id is None and organization_id is None:
        logger.info("知识检索拒绝：缺少 user_id 与 organization_id")
        return []

    query_vec = embedding_service.get_embedding(query)

    q = db.query(KnowledgeChunk).join(
        KnowledgeDocument,
        KnowledgeChunk.document_id == KnowledgeDocument.id,
    )
    clauses = []
    if user_id is not None:
        clauses.append(KnowledgeDocument.user_id == user_id)
    if organization_id is not None:
        clauses.append(
            and_(
                KnowledgeDocument.organization_id == organization_id,
                KnowledgeDocument.source_id.isnot(None),
            )
        )
    q = q.filter(or_(*clauses))
    q = q.filter(
        or_(KnowledgeDocument.status.is_(None), KnowledgeDocument.status == "active")
    )

    chunks = q.all()

    scored: List[Tuple[dict, float]] = []
    for chunk in chunks:
        if not chunk.embedding:
            continue
        try:
            chunk_vec = json.loads(chunk.embedding)
        except (json.JSONDecodeError, TypeError):
            continue

        score = _cosine_similarity(query_vec, chunk_vec)
        doc = chunk.document
        scored.append(({
            "id": chunk.id,
            "document_id": chunk.document_id,
            "content": chunk.content,
            "metadata": chunk.meta_info,
            "title": getattr(doc, "title", ""),
            "source": getattr(doc, "source", "manual"),
            "source_id": getattr(doc, "source_id", None),
        }, score))

    scored.sort(key=lambda x: x[1], reverse=True)
    return scored[:top_k]


def get_embedding_dimension() -> int:
    """获取向量维度"""
    return embedding_service.dimension