"""v3.3 Enterprise Knowledge Hub 自动化测试

覆盖：
1. 数据库模型（新表 + 扩展列）
2. 凭据加密 / 解密
3. 连接器注册 / Stub
4. 飞书连接器（mock）
5. 同步管线（mock，含 embedding mock）
6. API（Sources CRUD / Sync / Search）
7. 文档可见性隔离
8. 旧 upload / SSE 回归
"""
from __future__ import annotations

import json
import uuid
import bcrypt
import pytest
from fastapi.testclient import TestClient

from app.database.models import (
    KnowledgeDocument, KnowledgeChunk, KnowledgeSource,
    Organization, OrganizationMember, OrganizationRole,
    SyncLog, SyncTask, User, UserRole,
)
from sqlalchemy import inspect
from app.database.session import get_local_session, init_db
from app.knowledge.crypto import decrypt_config, encrypt_config
from app.knowledge.connectors.base import (
    ConnectResult, HealthResult, Page, RemoteDoc, RemoteDocContent, SyncBatch,
)
from app.knowledge.connectors.registry import get_connector, register_connector, supported_types
from app.main import app

client = TestClient(app)

# ──────────────────────────────────────────────
# Helpers
# ──────────────────────────────────────────────

def _hash() -> str:
    return bcrypt.hashpw(b"anypass", bcrypt.gensalt()).decode("utf-8")

def _unique_slug() -> str:
    return f"org-{uuid.uuid4().hex[:12]}"

def _create_org_and_user(db, prefix="hub", role=UserRole.admin) -> tuple[Organization, User]:
    tag = f"{prefix}_{uuid.uuid4().hex[:8]}"
    org = Organization(name=f"TestOrg{tag}", slug=_unique_slug())
    db.add(org)
    db.flush()
    user = User(
        username=tag,
        email=f"{tag}@test.com",
        password_hash=_hash(),
        role=role,
        organization_id=org.id,
    )
    db.add(user)
    db.flush()
    member = OrganizationMember(
        organization_id=org.id, user_id=user.id,
        role=OrganizationRole.admin if role == UserRole.admin else OrganizationRole.viewer,
    )
    db.add(member)
    db.commit()
    db.refresh(org)
    db.refresh(user)
    return org, user

def _login(username: str) -> str:
    resp = client.post("/api/auth/login", json={
        "username": username,
        "password": "anypass",
    })
    assert resp.status_code == 200, resp.text
    return resp.json()["access_token"]

def _auth_header(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}

def _fake_embedding(text: str) -> list[float]:
    import hashlib
    dimension = 128
    vec = []
    for i in range(dimension):
        h = hashlib.md5(f"{text}{i}".encode()).hexdigest()
        val = int(h[:8], 16) / 0xFFFFFFFF
        vec.append(val)
    return vec

def _add_doc_with_chunks(db, user, org_id, source_id, title_prefix, content):
    """Create KnowledgeDocument + chunk with fake embedding, using unique title."""
    tag = uuid.uuid4().hex[:8]
    title = f"{title_prefix}_{tag}"
    doc = KnowledgeDocument(
        user_id=user.id, title=title, content=content,
        source="feishu" if source_id else "manual",
        organization_id=org_id, source_id=source_id,
        external_id=f"e_{tag}" if source_id else None,
        status="active",
    )
    db.add(doc)
    db.flush()
    chunk = KnowledgeChunk(
        document_id=doc.id,
        content=content,
        embedding=json.dumps(_fake_embedding(content)),
    )
    db.add(chunk)
    db.commit()
    db.refresh(doc)
    return doc


@pytest.fixture(autouse=True)
def _mock_embeddings():
    """Replace real embedding with deterministic fake to avoid real API calls."""
    from app.rag.embeddings import embedding_service
    original = embedding_service.get_embedding
    embedding_service.get_embedding = lambda text, allow_fallback=True: _fake_embedding(text)
    yield
    embedding_service.get_embedding = original


# ──────────────────────────────────────────────
# Phase 1: Schema
# ──────────────────────────────────────────────

class TestSchema:
    def test_knowledge_document_has_new_columns(self):
        init_db()
        db = get_local_session()
        org, user = _create_org_and_user(db)

        src = KnowledgeSource(
            organization_id=org.id, type="feishu", name="飞书SOP",
            status="connected", config_enc=encrypt_config({"space_id": "x1"}),
            created_by=user.id,
        )
        db.add(src)
        db.flush()

        doc = KnowledgeDocument(
            user_id=user.id, title="测试", content="内容", source="feishu",
            organization_id=org.id, source_id=src.id, external_id="node_xxx",
            external_url="https://feishu.cn/wiki/node_xxx",
            checksum="abc123", status="active",
        )
        db.add(doc)
        db.commit()
        db.refresh(doc)

        assert doc.organization_id == org.id
        assert doc.source_id == src.id
        assert doc.external_id == "node_xxx"
        assert doc.checksum == "abc123"
        assert doc.status == "active"

        db.close()

    def test_knowledge_source_model(self):
        init_db()
        db = get_local_session()
        org, user = _create_org_and_user(db)

        src = KnowledgeSource(
            organization_id=org.id, type="feishu", name="FS SOP",
            status="disconnected",
            config_enc=encrypt_config({"app_id": "cli_a1"}),
            created_by=user.id,
        )
        db.add(src)
        db.commit()
        db.refresh(src)

        assert src.id > 0
        assert src.type == "feishu"
        assert src.organization_id == org.id
        assert src.status == "disconnected"

        db.close()

    def test_sync_task_and_log(self):
        init_db()
        db = get_local_session()
        org, user = _create_org_and_user(db)

        src = KnowledgeSource(
            organization_id=org.id, type="feishu", name="FS",
            status="connected", created_by=user.id,
        )
        db.add(src)
        db.flush()

        task = SyncTask(source_id=src.id, trigger="manual", status="queued")
        db.add(task)
        db.flush()

        log = SyncLog(task_id=task.id, level="info", message="start", external_id="n1")
        db.add(log)
        db.commit()
        db.refresh(task)
        db.refresh(log)

        assert task.id > 0
        assert log.id > 0
        assert log.task_id == task.id

        db.close()


# ──────────────────────────────────────────────
# Phase 2: Crypto & Connector
# ──────────────────────────────────────────────

class TestCrypto:
    def test_roundtrip(self):
        payload = {"app_id": "cli_a1", "app_secret": "secret", "space_id": "sp1"}
        enc = encrypt_config(payload)
        assert enc != json.dumps(payload)
        dec = decrypt_config(enc)
        assert dec["app_id"] == "cli_a1"
        assert dec["app_secret"] == "secret"

    def test_decrypt_empty(self):
        assert decrypt_config(None) == {}
        assert decrypt_config("") == {}

    def test_decrypt_garbage(self):
        assert decrypt_config("not-valid-token") == {}


class TestConnectorRegistry:
    def test_supported_types(self):
        types = supported_types()
        assert "feishu" in types
        assert "yuque" in types
        assert "gitlab" in types
        assert "confluence" in types

    def test_get_feishu_connector(self):
        conn = get_connector("feishu", {"app_id": "a", "app_secret": "s", "space_id": "s1"})
        assert conn.type == "feishu"
        assert conn.app_id == "a"

    def test_get_stub_raises_on_list(self):
        conn = get_connector("yuque", {})
        result = conn.connect({})
        assert result.ok is False
        assert "即将推出" in result.message
        with pytest.raises(NotImplementedError):
            conn.list_documents()

    def test_get_unknown_type(self):
        with pytest.raises(ValueError, match="不支持"):
            get_connector("not_exist", {})


# ──────────────────────────────────────────────
# Phase 3: Feishu Connector (mock)
# ──────────────────────────────────────────────

class MockFeishuConnector:
    type = "feishu"

    def __init__(self, credentials=None, http_client=None):
        self.docs = [
            RemoteDoc(external_id="n1", title="文档1", obj_token="ot1", obj_type="docx"),
            RemoteDoc(external_id="n2", title="文档2", obj_token="ot2", obj_type="docx"),
        ]

    def connect(self, credentials):
        return ConnectResult(ok=True, message="mock done")

    def health_check(self):
        return HealthResult(ok=True, message="mock ok")

    def list_documents(self, cursor=None):
        return Page(items=self.docs[:50], cursor=None)

    def fetch_document(self, external_id):
        for d in self.docs:
            if d.external_id == external_id:
                return RemoteDocContent(
                    external_id=external_id, title=d.title,
                    content=f"模拟正文 {d.title}",
                )
        raise ValueError("not found")

    def sync(self, since=None):
        return SyncBatch(docs=self.docs, truncated=False)


class TestFeishuMock:
    def test_mock_connect_and_health(self):
        conn = MockFeishuConnector()
        assert conn.connect({}).ok
        assert conn.health_check().ok

    def test_mock_list_and_fetch(self):
        conn = MockFeishuConnector()
        page = conn.list_documents()
        assert len(page.items) == 2
        content = conn.fetch_document("n1")
        assert "模拟正文" in content.content


# ──────────────────────────────────────────────
# Phase 3: Pipeline (mock connector + fake embedding)
# ──────────────────────────────────────────────

class TestPipeline:
    def test_enqueue_and_run(self):
        init_db()
        db = get_local_session()
        org, user = _create_org_and_user(db)

        mock_type = f"feishu_mock_{uuid.uuid4().hex[:6]}"
        register_connector(mock_type, MockFeishuConnector)

        src = KnowledgeSource(
            organization_id=org.id, type=mock_type, name="MockFS",
            status="connected", created_by=user.id,
            config_enc=encrypt_config({"space_id": "mock"}),
        )
        db.add(src)
        db.commit()
        db.refresh(src)

        from app.knowledge.pipeline import enqueue_sync, run_sync_task

        task = enqueue_sync(db, src, trigger="manual")
        assert task.status == "queued"
        assert task.id > 0

        result = run_sync_task(task.id)
        assert result["status"] in ("success", "failed"), result

        docs = db.query(KnowledgeDocument).filter(
            KnowledgeDocument.source_id == src.id
        ).all()
        assert len(docs) == 2
        for doc in docs:
            assert doc.status == "active"
            assert doc.organization_id == org.id

        db.close()


# ──────────────────────────────────────────────
# Phase 4: RAG Provider + Document Visibility
# ──────────────────────────────────────────────

class TestProvider:
    def test_org_document_visible_to_member(self):
        init_db()
        db = get_local_session()
        org, admin = _create_org_and_user(db)

        src = KnowledgeSource(
            organization_id=org.id, type="feishu", name="SOP",
            status="connected", created_by=admin.id,
        )
        db.add(src)
        db.flush()
        doc = _add_doc_with_chunks(db, admin, org.id, src.id, "故障SOP", "步骤123")

        # viewer in the same org
        viewer = User(
            username=f"v_{uuid.uuid4().hex[:8]}",
            email=f"v_{uuid.uuid4().hex[:8]}@test.com",
            password_hash=_hash(),
            role=UserRole.viewer,
            organization_id=org.id,
        )
        db.add(viewer)
        db.flush()
        db.add(OrganizationMember(
            organization_id=org.id, user_id=viewer.id,
            role=OrganizationRole.viewer,
        ))
        db.commit()
        # re-read viewer to get fresh org_id from DB
        viewer = db.query(User).filter(User.id == viewer.id).first()

        from app.knowledge.provider import get_document, search_documents
        assert get_document(db, viewer, doc.id) is not None

        hits = search_documents("步骤123", db, viewer, top_k=5)
        titles = [h.get("title") for h in hits]
        assert doc.title in titles

        db.close()

    def test_other_org_cannot_see(self):
        init_db()
        db = get_local_session()
        org_a, user_a = _create_org_and_user(db)
        org_b, user_b = _create_org_and_user(db)

        _add_doc_with_chunks(db, user_a, org_a.id, None, "仅A可见", "机密")

        from app.knowledge.provider import get_document
        doc = db.query(KnowledgeDocument).filter(
            KnowledgeDocument.title == "仅A可见"
        ).first()
        assert get_document(db, user_b, doc.id) is None

        db.close()

    def test_manual_doc_private_to_owner(self):
        init_db()
        db = get_local_session()
        _, user = _create_org_and_user(db)
        _add_doc_with_chunks(db, user, None, None, "私有", "私有内容")

        from app.rag.retriever import retrieve_knowledge
        hits = retrieve_knowledge("私有内容", db, top_k=5, user_id=user.id)
        assert len(hits) > 0

        hits2 = retrieve_knowledge("私有内容", db, top_k=5, user_id=99999)
        assert len(hits2) == 0

        db.close()

    def test_unauthenticated_returns_empty(self):
        init_db()
        db = get_local_session()
        from app.rag.vector_store import similarity_search
        results = similarity_search("任何内容", db, top_k=5)
        assert results == []

        db.close()


# ──────────────────────────────────────────────
# Phase 5: Hub API
# ──────────────────────────────────────────────

class TestKnowledgeHubAPI:
    @pytest.fixture(autouse=True)
    def _setup(self, request):
        init_db()
        db = get_local_session()
        self.org, self.admin = _create_org_and_user(db)
        db.close()
        self.token = _login(self.admin.username)

    @pytest.fixture()
    def headers(self):
        return _auth_header(self.token)

    def _create_source(self, headers, name):
        return client.post("/api/knowledge/sources", headers=headers, json={
            "type": "feishu", "name": name,
            "app_id": "cli_a1", "app_secret": "secret", "space_id": "sp1",
        })

    def test_create_source(self, headers):
        resp = self._create_source(headers, "运维SOP")
        assert resp.status_code == 200, resp.text
        data = resp.json()
        assert data["type"] == "feishu"
        assert data["name"] == "运维SOP"
        assert "config_enc" not in data
        assert "app_secret" not in data

    def test_list_sources(self, headers):
        self._create_source(headers, "S")
        resp = client.get("/api/knowledge/sources", headers=headers)
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)
        assert len(data) >= 1
        for item in data:
            assert "name" in item
            assert "config_enc" not in item

    def test_delete_source(self, headers):
        cr = self._create_source(headers, "ToDelete")
        sid = cr.json()["id"]
        resp = client.delete(f"/api/knowledge/sources/{sid}", headers=headers)
        assert resp.status_code == 200
        get_resp = client.get(f"/api/knowledge/sources/{sid}", headers=headers)
        assert get_resp.status_code == 404

    def test_sync_and_tasks(self, headers):
        cr = self._create_source(headers, "SyncTest")
        sid = cr.json()["id"]
        sync_resp = client.post(f"/api/knowledge/sources/{sid}/sync", headers=headers)
        assert sync_resp.status_code == 200
        task_id = sync_resp.json()["task_id"]

        tasks_resp = client.get("/api/knowledge/sync/tasks", headers=headers)
        assert tasks_resp.status_code == 200
        tasks = tasks_resp.json()
        assert any(t["id"] == task_id for t in tasks)

        detail = client.get(f"/api/knowledge/sync/tasks/{task_id}", headers=headers)
        assert detail.status_code == 200
        assert detail.json()["id"] == task_id

        logs_resp = client.get(f"/api/knowledge/sync/tasks/{task_id}/logs", headers=headers)
        assert logs_resp.status_code == 200
        assert isinstance(logs_resp.json(), list)

    def test_viewer_cannot_create_source(self):
        init_db()
        db = get_local_session()
        _, viewer = _create_org_and_user(db, role=UserRole.viewer)
        db.close()
        token = _login(viewer.username)
        resp = client.post("/api/knowledge/sources", headers=_auth_header(token), json={
            "type": "feishu", "name": "N", "app_id": "a", "app_secret": "s", "space_id": "x",
        })
        assert resp.status_code == 403

    def test_search_returns_results(self, headers):
        client.post("/api/knowledge/upload", headers=headers, json={
            "title": "Redis故障排查",
            "content": "Redis 内存不足时：1. 检查 maxmemory 2. 分析 bigkey 3. 开启 lazyfree",
        })
        resp = client.post("/api/knowledge/search", headers=headers, json={
            "query": "Redis 内存",
            "top_k": 5,
        })
        assert resp.status_code == 200
        results = resp.json()
        assert isinstance(results, list)
        titles = [r.get("title") or r.get("meta_info", {}).get("title") or "" for r in results]
        assert any("Redis" in t for t in titles)


# ──────────────────────────────────────────────
# Phase 6: Regression
# ──────────────────────────────────────────────

class TestRegression:
    @pytest.fixture(autouse=True)
    def _setup(self):
        init_db()
        db = get_local_session()
        _, user = _create_org_and_user(db)
        db.close()
        self.token = _login(user.username)

    def test_upload_still_works(self):
        h = _auth_header(self.token)
        resp = client.post("/api/knowledge/upload", headers=h, json={
            "title": "PG 运维",
            "content": "PostgreSQL vacuum 配置与监控",
        })
        assert resp.status_code == 200
        data = resp.json()
        assert data["id"] > 0
        assert "已上传并索引" in data.get("detail", "")

    def test_list_still_works(self):
        h = _auth_header(self.token)
        client.post("/api/knowledge/upload", headers=h, json={
            "title": "Docker 清理", "content": "docker system prune -af",
        })
        resp = client.get("/api/knowledge", headers=h)
        assert resp.status_code == 200
        docs = resp.json()
        assert isinstance(docs, list)

    def test_delete_still_works(self):
        h = _auth_header(self.token)
        cr = client.post("/api/knowledge/upload", headers=h, json={
            "title": "临时", "content": "内容",
        })
        doc_id = cr.json()["id"]
        resp = client.delete(f"/api/knowledge/{doc_id}", headers=h)
        assert resp.status_code == 200

    def test_sse_knowledge_still_works(self):
        h = _auth_header(self.token)
        client.post("/api/knowledge/upload", headers=h, json={
            "title": "SSE回归", "content": "这是一篇 SSE 回归测试文档",
        })
        resp = client.post("/api/chat", headers=h, json={
            "message": "ping", "session_id": "regression_sse",
        })
        assert resp.status_code == 200
        data = resp.json()
        assert "report" in data or "final_report" in data


# ──────────────────────────────────────────────
# Phase 6: Multi-tenant isolation
# ──────────────────────────────────────────────

class TestMultiTenant:
    def test_cross_org_search_isolation(self):
        init_db()
        db = get_local_session()

        org_a, admin_a = _create_org_and_user(db)
        org_b, admin_b = _create_org_and_user(db)

        src_a = KnowledgeSource(
            organization_id=org_a.id, type="feishu", name="SOP-A",
            status="connected", created_by=admin_a.id,
        )
        db.add(src_a)
        db.flush()
        doc_a = _add_doc_with_chunks(db, admin_a, org_a.id, src_a.id, "OrgA机密", "A数据")

        src_b = KnowledgeSource(
            organization_id=org_b.id, type="feishu", name="SOP-B",
            status="connected", created_by=admin_b.id,
        )
        db.add(src_b)
        db.flush()
        doc_b = _add_doc_with_chunks(db, admin_b, org_b.id, src_b.id, "OrgB机密", "B数据")

        from app.rag.retriever import retrieve_knowledge
        hits_a = retrieve_knowledge(
            "数据", db, top_k=5,
            user_id=admin_a.id, organization_id=org_a.id,
        )
        titles_a = [h.get("title") for h in hits_a]
        assert doc_a.title in titles_a
        assert doc_b.title not in titles_a

        hits_b = retrieve_knowledge(
            "数据", db, top_k=5,
            user_id=admin_b.id, organization_id=org_b.id,
        )
        titles_b = [h.get("title") for h in hits_b]
        assert doc_b.title in titles_b
        assert doc_a.title not in titles_b

        db.close()