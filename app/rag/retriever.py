"""知识检索服务

将用户问题转化为向量查询，从知识库中召回相关文档块，
并格式化为 Agent 可用的上下文。
"""

import logging
from typing import List, Optional

from sqlalchemy.orm import Session as SASession

from app.rag.vector_store import similarity_search

logger = logging.getLogger(__name__)


def retrieve_knowledge(
    query: str,
    db: SASession,
    top_k: int = 5,
    user_id: Optional[int] = None,
    organization_id: Optional[int] = None,
) -> List[dict]:
    """检索相关知识。未登录（无 user_id）时返回空列表。"""
    results = similarity_search(
        query, db, top_k=top_k, user_id=user_id, organization_id=organization_id,
    )

    chunks = []
    for chunk_dict, score in results:
        source = chunk_dict.get("source") or chunk_dict.get("metadata", {}).get("source") or "manual"
        chunks.append({
            "content": chunk_dict["content"][:1000],
            "metadata": chunk_dict.get("metadata", {}),
            "meta_info": chunk_dict.get("meta_info", {}) or chunk_dict.get("metadata", {}),
            "score": round(score, 4),
            "document_id": chunk_dict.get("document_id"),
            "title": chunk_dict.get("title") or "",
            "source": source,
        })

    logger.info(
        "知识检索: query='%s' top_k=%d results=%d user=%s org=%s",
        query[:50], top_k, len(chunks), user_id, organization_id,
    )
    return chunks


def format_knowledge_context(chunks: List[dict]) -> str:
    """将检索到的知识块格式化为 Agent 上下文

    Args:
        chunks: 知识块列表

    Returns:
        格式化后的上下文文本
    """
    if not chunks:
        return ""

    parts = ["## 相关知识库参考\n"]
    for i, chunk in enumerate(chunks, 1):
        source = chunk.get("source") or chunk.get("meta_info", {}).get("source") or chunk.get("metadata", {}).get("source", "未知来源")
        label = "飞书" if source == "feishu" else ("本地上传" if source in ("manual", "file") else source)
        title = chunk.get("title") or ""
        score = chunk.get("score", 0)
        heading = f"### 参考 {i} (来源: {label}"
        if title:
            heading += f" · {title}"
        heading += f", 相关度: {score:.2f})"
        parts.append(heading)
        parts.append(chunk["content"])
        parts.append("")

    return "\n".join(parts)