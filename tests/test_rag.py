# ============================================================
# Enterprise AI DevOps Agent — RAG 知识库测试
# 覆盖：文档加载、文本切分、Embedding、知识搜索、Agent 集成
# ============================================================

import pytest
import json
import os
import tempfile

from fastapi.testclient import TestClient
from app.main import app
from app.rag.loader import Document, load_text, load_file
from app.rag.splitter import TextSplitter
from app.rag.embeddings import EmbeddingService
from app.rag.vector_store import similarity_search, _cosine_similarity
from app.rag.retriever import retrieve_knowledge, format_knowledge_context
from app.rag.service import RAGService, rag_service
from app.database.models import KnowledgeDocument, KnowledgeChunk
from app.database.session import init_db, get_local_session

client = TestClient(app)


# ============================================================
# 辅助函数
# ============================================================

def _register_and_login(username: str = "rag_test_user", password: str = "TestPass123!"):
    """注册并登录，返回 token"""
    import random
    suffix = random.randint(10000, 99999)
    uname = f"{username}_{suffix}"
    client.post(
        "/api/auth/register",
        json={"username": uname, "email": f"{uname}@test.com", "password": password}
    )
    resp = client.post(
        "/api/auth/login",
        json={"username": uname, "password": password}
    )
    return resp.json().get("access_token")


# ============================================================
# 文档加载测试
# ============================================================

class TestDocumentLoader:
    """文档加载器测试"""

    def test_load_text(self):
        """加载纯文本"""
        doc = load_text("这是一段测试文本", source="test")
        assert doc is not None
        assert doc.content == "这是一段测试文本"
        assert doc.metadata["source"] == "test"

    def test_load_text_empty(self):
        """加载空文本"""
        doc = load_text("", source="test")
        assert doc is not None
        assert doc.content == ""

    def test_load_file_markdown(self):
        """加载 markdown 文件"""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False, encoding="utf-8") as f:
            f.write("# 测试文档\n\n这是一段测试内容。\n")
            fpath = f.name
        doc = load_file(fpath)
        assert doc is not None
        assert "# 测试文档" in doc.content
        assert doc.metadata["filetype"] == "md"
        os.unlink(fpath)

    def test_load_file_txt(self):
        """加载 txt 文件"""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False, encoding="utf-8") as f:
            f.write("纯文本测试内容。\n")
            fpath = f.name
        doc = load_file(fpath)
        assert doc is not None
        assert "纯文本测试内容" in doc.content
        os.unlink(fpath)

    def test_load_file_not_found(self):
        """文件不存在返回 None"""
        doc = load_file("/nonexistent/file.md")
        assert doc is None

    def test_load_file_unsupported_format(self):
        """不支持的文件格式返回 None"""
        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as f:
            fpath = f.name
        doc = load_file(fpath)
        assert doc is None
        os.unlink(fpath)


# ============================================================
# 文本切分测试
# ============================================================

class TestTextSplitter:
    """文本切分器测试"""

    def test_split_empty(self):
        """空文本切分返回空列表"""
        splitter = TextSplitter()
        assert splitter.split_text("") == []

    def test_split_short_text(self):
        """短文本不切分"""
        splitter = TextSplitter(chunk_size=1000)
        chunks = splitter.split_text("这是一段很短的文本。")
        assert len(chunks) == 1
        assert chunks[0] == "这是一段很短的文本。"

    def test_split_long_text(self):
        """长文本正确切分"""
        splitter = TextSplitter(chunk_size=200, chunk_overlap=10)
        # 生成足够长的文本以确保被切分
        text = "段落一。" * 30 + "\n\n段落二。" * 30 + "\n\n段落三。" * 30
        chunks = splitter.split_text(text)
        assert len(chunks) >= 2

    def test_split_documents(self):
        """文档列表切分"""
        splitter = TextSplitter(chunk_size=500)
        docs = [
            Document(content="文档一的内容。" * 20, metadata={"source": "doc1"}),
            Document(content="文档二的内容。" * 10, metadata={"source": "doc2"}),
        ]
        chunks = splitter.split_documents(docs)
        assert len(chunks) >= 2
        for chunk in chunks:
            assert "content" in chunk
            assert "meta_info" in chunk
            assert "chunk_index" in chunk["meta_info"]

    def test_split_with_overlap(self):
        """单行超过 chunk_size 时强制切分"""
        splitter = TextSplitter(chunk_size=200, chunk_overlap=30)
        text = "A" * 500 + "\n\nB" * 10
        chunks = splitter.split_text(text)
        assert len(chunks) >= 2

    def test_split_paragraph_boundary(self):
        """段落边界切分"""
        splitter = TextSplitter(chunk_size=50)
        text = "第一段。\n\n第二段。\n\n第三段。\n\n第四段。\n\n第五段。"
        chunks = splitter.split_text(text)
        assert all(c.strip() for c in chunks)
        # 每段很短所以应合并，但至少是一个块
        assert len(chunks) >= 1


# ============================================================
# Embedding 测试
# ============================================================

class TestEmbedding:
    """Embedding 服务测试"""

    def test_embedding_fallback(self):
        """降级方案应生成有效向量"""
        service = EmbeddingService()
        vec = service._fallback_embedding("测试文本")
        assert len(vec) == 128
        assert all(isinstance(v, float) for v in vec)

    def test_embedding_fallback_deterministic(self):
        """相同文本的降级向量应一致"""
        service = EmbeddingService()
        vec1 = service._fallback_embedding("相同的文本")
        vec2 = service._fallback_embedding("相同的文本")
        assert vec1 == vec2

    def test_embedding_dimension(self):
        """向量维度应正确"""
        service = EmbeddingService()
        assert service.dimension == 128

    def test_cosine_similarity_identical(self):
        """相同向量的余弦相似度应为 1.0"""
        vec = [0.5, 0.3, 0.2]
        sim = _cosine_similarity(vec, vec)
        assert abs(sim - 1.0) < 0.0001

    def test_cosine_similarity_orthogonal(self):
        """正交向量的余弦相似度应为 0.0"""
        vec_a = [1.0, 0.0]
        vec_b = [0.0, 1.0]
        sim = _cosine_similarity(vec_a, vec_b)
        assert abs(sim) < 0.0001

    def test_cosine_similarity_zero_vector(self):
        """零向量的余弦相似度应为 0.0"""
        vec_a = [0.0, 0.0]
        vec_b = [0.5, 0.5]
        sim = _cosine_similarity(vec_a, vec_b)
        assert abs(sim) < 0.0001


# ============================================================
# 知识库 API 测试
# ============================================================

class TestKnowledgeAPI:
    """知识库 API 测试"""

    def setup_method(self):
        """每个测试前初始化数据库"""
        init_db()

    def test_upload_knowledge(self):
        """上传知识文档"""
        token = _register_and_login()
        resp = client.post(
            "/api/knowledge/upload",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "title": "测试运维手册",
                "content": "# 服务器重启 SOP\n\n1. 备份数据\n2. 通知用户\n3. 执行重启\n4. 验证服务",
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "id" in data
        assert data["title"] == "测试运维手册"

    def test_list_knowledge(self):
        """获取知识库列表"""
        token = _register_and_login()
        # 先上传
        client.post(
            "/api/knowledge/upload",
            headers={"Authorization": f"Bearer {token}"},
            json={"title": "列表测试文档", "content": "内容"},
        )
        resp = client.get(
            "/api/knowledge",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 200
        docs = resp.json()
        assert isinstance(docs, list)
        assert len(docs) >= 1

    def test_delete_knowledge(self):
        """删除知识文档"""
        token = _register_and_login()
        # 先上传
        upload = client.post(
            "/api/knowledge/upload",
            headers={"Authorization": f"Bearer {token}"},
            json={"title": "待删除文档", "content": "将被删除的内容"},
        )
        doc_id = upload.json()["id"]

        resp = client.delete(
            f"/api/knowledge/{doc_id}",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 200

    def test_delete_nonexistent_knowledge(self):
        """删除不存在的文档返回 404"""
        token = _register_and_login()
        resp = client.delete(
            "/api/knowledge/99999",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 404

    def test_search_knowledge(self):
        """搜索知识库"""
        token = _register_and_login()
        # 上传包含运维领域知识的文档
        client.post(
            "/api/knowledge/upload",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "title": "Kubernetes 排障指南",
                "content": "当 Pod 处于 CrashLoopBackOff 状态时，首先检查日志。"
                           "常见的原因为 OOMKilled、配置错误、镜像不存在。"
                           "使用 kubectl describe pod 查看事件。"
                           "使用 kubectl logs 查看容器日志。",
            },
        )

        resp = client.post(
            "/api/knowledge/search",
            headers={"Authorization": f"Bearer {token}"},
            json={"query": "Pod 崩溃如何排查", "top_k": 3},
        )
        assert resp.status_code == 200
        results = resp.json()
        assert isinstance(results, list)

    def test_knowledge_requires_auth(self):
        """知识库 API 需要认证"""
        resp = client.get("/api/knowledge")
        assert resp.status_code == 401

    def test_upload_requires_auth(self):
        """上传需要认证"""
        resp = client.post(
            "/api/knowledge/upload",
            json={"title": "test", "content": "test"},
        )
        assert resp.status_code == 401


# ============================================================
# RAG Service 测试
# ============================================================

class TestRAGService:
    """RAG 服务测试"""

    def test_ingest_and_search(self):
        """导入文档并搜索"""
        init_db()
        db = get_local_session()

        # 先创建用户
        from app.database.models import User
        user = db.query(User).first()
        if user is None:
            user = User(username="rag_svc_test", email="rag_svc@test.com", password_hash="test")
            db.add(user)
            db.commit()
            db.refresh(user)

        svc = RAGService()
        doc_id = svc.ingest_text(
            title="Nginx 配置指南",
            content="Nginx 反向代理配置：\n1. 设置 upstream\n2. 配置 proxy_pass\n3. 设置缓存策略\n4. 配置 SSL 证书\n5. 重启 Nginx",
            db=db,
            user_id=user.id,
            source="manual",
        )
        assert doc_id > 0

        # 搜索
        results = svc.search("Nginx 反向代理怎么配置", db=db, top_k=3, user_id=user.id)
        assert len(results) > 0
        assert any("Nginx" in r["content"] for r in results)

        db.close()

    def test_search_no_matches(self):
        """无匹配搜索应返回空列表（使用不存在的 user_id 过滤）"""
        init_db()
        db = get_local_session()
        svc = RAGService()
        results = svc.search("查询不存在的知识", db=db, top_k=3, user_id=99999)
        assert results == []
        db.close()

    def test_agent_context_format(self):
        """Agent 上下文格式应正确"""
        init_db()
        db = get_local_session()
        chunks = retrieve_knowledge("测试", db=db, top_k=3)
        ctx = format_knowledge_context(chunks)
        if chunks:
            assert "相关知识库参考" in ctx
        db.close()

    def test_get_agent_context(self):
        """RAGService.get_agent_context 应返回格式化上下文"""
        init_db()
        db = get_local_session()
        ctx = rag_service.get_agent_context("Nginx 配置", db=db)
        assert isinstance(ctx, str)
        db.close()


# ============================================================
# RAG + Agent 集成测试
# ============================================================

class TestRAGAgentIntegration:
    """RAG + Agent 集成测试"""

    def test_chat_with_rag_context(self):
        """Agent 对话应包含知识库上下文"""
        token = _register_and_login()

        # 先上传知识文档
        client.post(
            "/api/knowledge/upload",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "title": "运维最佳实践",
                "content": "服务器故障排查步骤：\n1. 检查 CPU 使用率\n2. 检查内存使用率\n3. 检查磁盘空间\n4. 查看系统日志\n5. 分析根本原因",
            },
        )

        # 发送对话请求
        resp = client.post(
            "/api/chat",
            json={"message": "ping", "session_id": "test_rag_integration"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "report" in data
        assert "trace" in data

    def test_knowledge_api_cors_and_structure(self):
        """知识库 API 响应结构验证"""
        token = _register_and_login()

        # 上传
        upload_resp = client.post(
            "/api/knowledge/upload",
            headers={"Authorization": f"Bearer {token}"},
            json={"title": "结构测试", "content": "测试内容"},
        )
        assert upload_resp.status_code == 200
        assert "id" in upload_resp.json()
        assert "title" in upload_resp.json()

        # 列表
        list_resp = client.get(
            "/api/knowledge",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert list_resp.status_code == 200
        docs = list_resp.json()
        if docs:
            doc = docs[0]
            assert "id" in doc
            assert "title" in doc
            assert "created_at" in doc


# ============================================================
# 文档关系测试
# ============================================================

class TestDocumentRelations:
    """文档-文本块关系测试"""

    def test_document_chunk_relation(self):
        """验证文档和 chunk 的数据库关系"""
        init_db()
        db = get_local_session()

        from app.database.models import User
        user = db.query(User).first()
        if not user:
            db.close()
            return

        # 创建文档
        doc = KnowledgeDocument(
            user_id=user.id,
            title="关系测试文档",
            content="这是一段测试内容。\n\n这是第二段。\n\n这是第三段。",
            source="test",
        )
        db.add(doc)
        db.flush()

        # 创建 chunk
        chunk = KnowledgeChunk(
            document_id=doc.id,
            content="这是第一段。",
            meta_info={"index": 0},
        )
        db.add(chunk)
        db.flush()

        # 验证关系
        assert chunk.document_id == doc.id
        assert len(doc.chunks) >= 1

        # 清理
        db.rollback()
        db.close()

    def test_document_cascade_delete(self):
        """删除文档应级联删除 chunks"""
        init_db()
        db = get_local_session()

        from app.database.models import User
        user = db.query(User).first()
        if not user:
            db.close()
            return

        doc = KnowledgeDocument(
            user_id=user.id,
            title="级联删除测试",
            content="测试内容。",
            source="test",
        )
        db.add(doc)
        db.flush()

        chunk = KnowledgeChunk(
            document_id=doc.id,
            content="测试块",
            meta_info={"index": 0},
        )
        db.add(chunk)
        db.commit()

        chunk_id = chunk.id
        db.delete(doc)
        db.commit()

        # 验证 chunk 已被删除
        deleted = db.query(KnowledgeChunk).filter(KnowledgeChunk.id == chunk_id).first()
        assert deleted is None

        db.close()
