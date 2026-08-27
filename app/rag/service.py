"""RAG 知识库服务 — 统一入口

协调文档加载、切分、向量化、存储和检索的完整流程。
"""

import logging
from typing import List, Optional

from sqlalchemy.orm import Session as SASession

from app.rag.loader import load_text, load_file
from app.rag.splitter import TextSplitter
from app.rag.embeddings import embedding_service
from app.rag.retriever import retrieve_knowledge, format_knowledge_context

logger = logging.getLogger(__name__)


class RAGService:
    """RAG 知识库服务"""

    def __init__(self):
        self.splitter = TextSplitter(chunk_size=500, chunk_overlap=50)

    def ingest_text(
        self,
        title: str,
        content: str,
        db: SASession,
        user_id: int,
        source: str = "manual",
        organization_id: Optional[int] = None,
        source_id: Optional[int] = None,
        external_id: Optional[str] = None,
        external_url: Optional[str] = None,
        checksum: Optional[str] = None,
        require_embedding: bool = False,
    ) -> int:
        """导入文本到知识库。Hub 文档传入 source_id/org 并禁止 embedding 降级。"""
        from app.database.models import KnowledgeDocument, KnowledgeChunk

        doc = None
        if source_id is not None and external_id:
            doc = (
                db.query(KnowledgeDocument)
                .filter(
                    KnowledgeDocument.source_id == source_id,
                    KnowledgeDocument.external_id == external_id,
                )
                .first()
            )

        if doc is None:
            doc = KnowledgeDocument(
                user_id=user_id,
                title=title,
                content=content,
                source=source,
                organization_id=organization_id,
                source_id=source_id,
                external_id=external_id,
                external_url=external_url,
                checksum=checksum,
                status="active",
            )
            db.add(doc)
            db.flush()
        else:
            for chunk in list(doc.chunks):
                db.delete(chunk)
            db.flush()
            doc.title = title
            doc.content = content
            doc.source = source
            doc.user_id = user_id
            doc.organization_id = organization_id
            doc.external_url = external_url
            doc.checksum = checksum
            doc.status = "active"
            db.flush()

        document = load_text(content, source=source)
        chunks = self.splitter.split_documents([document])

        for chunk_data in chunks:
            chunk = KnowledgeChunk(
                document_id=doc.id,
                content=chunk_data["content"],
                meta_info=chunk_data.get("meta_info"),
            )
            db.add(chunk)
            db.flush()
            embedding = embedding_service.get_embedding(
                chunk_data["content"],
                allow_fallback=not require_embedding,
            )
            chunk.embedding_list = embedding

        db.commit()
        logger.info(
            "知识库导入: title='%s' chunks=%d id=%d source=%s",
            title, len(chunks), doc.id, source,
        )
        return doc.id

    def ingest_file(
        self,
        file_path: str,
        db: SASession,
        user_id: int,
        title: Optional[str] = None,
    ) -> Optional[int]:
        """从文件导入文档到知识库

        Args:
            file_path: 文件路径
            db: 数据库会话
            user_id: 用户 ID
            title: 文档标题（默认使用文件名）

        Returns:
            文档 ID，失败返回 None
        """
        import os

        doc_obj = load_file(file_path)
        if doc_obj is None:
            return None

        doc_title = title or os.path.basename(file_path)
        return self.ingest_text(
            title=doc_title,
            content=doc_obj.content,
            db=db,
            user_id=user_id,
            source=file_path,
        )

    def search(
        self,
        query: str,
        db: SASession,
        top_k: int = 5,
        user_id: Optional[int] = None,
        organization_id: Optional[int] = None,
    ) -> List[dict]:
        """搜索知识库"""
        return retrieve_knowledge(
            query, db, top_k=top_k, user_id=user_id, organization_id=organization_id,
        )

    def get_agent_context(
        self,
        query: str,
        db: SASession,
        user_id: Optional[int] = None,
        organization_id: Optional[int] = None,
    ) -> str:
        """获取 Agent 可用的知识上下文

        Args:
            query: 用户查询
            db: 数据库会话
            user_id: 用户 ID

        Returns:
            格式化的知识上下文（Markdown）
        """
        chunks = self.search(
            query, db, top_k=3, user_id=user_id, organization_id=organization_id,
        )
        return format_knowledge_context(chunks)


# 全局单例
rag_service = RAGService()
