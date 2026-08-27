"""测试监控相关 API 接口

测试覆盖：
- /metrics Prometheus 指标接口
- /api/monitoring/current 监控指标接口
- /api/alerts 告警列表接口
- /api/alerts/{id}/resolve 关闭告警接口
- /api/agent/executions Agent 执行记录接口
"""

import pytest
import os
from fastapi.testclient import TestClient
from app.database.database import engine
from app.database.database import Base

# 确保数据库包含所有表（包括新增的 agent_executions 和 alerts）
import app.database.models  # noqa: F401
Base.metadata.create_all(bind=engine)


# ============================================================
# 测试组1：Prometheus 指标接口
# ============================================================
class TestMetricsEndpoint:
    def test_metrics_endpoint_returns_text(self):
        """验证 /metrics 返回 Prometheus 文本"""
        from app.main import app
        client = TestClient(app)
        response = client.get("/metrics")
        assert response.status_code == 200
        assert response.headers["content-type"].startswith("text/plain")
        assert "devops_" in response.text or "# HELP" in response.text

    def test_metrics_contains_http_metrics(self):
        """验证 /metrics 包含 HTTP 请求指标"""
        from app.main import app
        client = TestClient(app)
        # 先发一个请求触发指标记录
        client.get("/health")
        response = client.get("/metrics")
        assert response.status_code == 200
        # 指标文件中应有 http_requests_total 或 HTTP 相关指标
        has_http = "http_requests_total" in response.text or "devops_http" in response.text
        assert has_http

    def test_metrics_unlimited(self):
        """验证 /metrics 接口不限流"""
        from app.main import app
        client = TestClient(app)
        # 快速连续访问不应被限流
        for _ in range(5):
            response = client.get("/metrics")
            assert response.status_code == 200


# ============================================================
# 测试组2：监控数据接口
# ============================================================
class TestMonitoringCurrentEndpoint:
    def test_monitoring_requires_auth(self):
        """验证 /api/monitoring/current 需要 JWT 认证"""
        from app.main import app
        client = TestClient(app)
        response = client.get("/api/monitoring/current")
        assert response.status_code == 401

    def test_monitoring_returns_data(self):
        """验证已认证用户可获取监控数据"""
        from app.main import app
        from app.database.session import get_db
        from app.database.models import User
        from app.auth.password import hash_password

        # 注册测试用户并获取 token
        client = TestClient(app)
        register_resp = client.post(
            "/api/auth/register",
            json={"username": "mon_test_user", "password": "test123", "email": "mon_test@example.com"},
        )
        login_resp = client.post(
            "/api/auth/login",
            json={"username": "mon_test_user", "password": "test123"},
        )
        assert login_resp.status_code == 200
        token = login_resp.json().get("access_token")

        response = client.get(
            "/api/monitoring/current",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 200
        data = response.json()
        assert "cpu" in data
        assert "memory" in data
        assert "disks" in data


# ============================================================
# 测试组3：告警 API
# ============================================================
class TestAlertsEndpoint:
    def test_alerts_requires_auth(self):
        """验证 /api/alerts 需要 JWT 认证"""
        from app.main import app
        client = TestClient(app)
        response = client.get("/api/alerts")
        assert response.status_code == 401

    def test_alerts_list(self):
        """验证已认证用户可以获取告警列表"""
        from app.main import app
        client = TestClient(app)

        login_resp = client.post(
            "/api/auth/login",
            json={"username": "mon_test_user", "password": "test123"},
        )
        assert login_resp.status_code == 200
        token = login_resp.json().get("access_token")

        response = client.get(
            "/api/alerts",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)


# ============================================================
# 测试组4：关闭告警 API
# ============================================================
class TestResolveAlertEndpoint:
    def test_resolve_nonexistent_alert(self):
        """验证关闭不存在的告警返回 404"""
        from app.main import app
        client = TestClient(app)

        login_resp = client.post(
            "/api/auth/login",
            json={"username": "mon_test_user", "password": "test123"},
        )
        assert login_resp.status_code == 200
        token = login_resp.json().get("access_token")

        response = client.post(
            "/api/alerts/99999/resolve",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 404


# ============================================================
# 测试组5：Agent 执行记录 API
# ============================================================
class TestAgentExecutionsEndpoint:
    def test_executions_requires_auth(self):
        """验证 /api/agent/executions 需要 JWT 认证"""
        from app.main import app
        client = TestClient(app)
        response = client.get("/api/agent/executions")
        assert response.status_code == 401

    def test_executions_list(self):
        """验证已认证用户可以获取执行记录"""
        from app.main import app
        client = TestClient(app)

        login_resp = client.post(
            "/api/auth/login",
            json={"username": "mon_test_user", "password": "test123"},
        )
        assert login_resp.status_code == 200
        token = login_resp.json().get("access_token")

        response = client.get(
            "/api/agent/executions",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)


# ============================================================
# 测试组6：新增模型数据库操作
# ============================================================
class TestNewModels:
    def test_agent_execution_model_create(self):
        """验证 AgentExecution 模型可创建和查询"""
        from app.database.session import get_db
        from app.database.models import AgentExecution, ExecutionStatus, User

        db = next(get_db())
        user = db.query(User).first()
        if not user:
            pytest.skip("没有可用用户")

        execution = AgentExecution(
            user_id=user.id,
            status=ExecutionStatus.success,
            duration=2.5,
            tools_called=3,
        )
        db.add(execution)
        db.commit()
        assert execution.id is not None
        assert execution.status == ExecutionStatus.success
        assert execution.duration == 2.5

        # 清理
        db.delete(execution)
        db.commit()

    def test_agent_execution_user_relation(self):
        """验证 AgentExecution 与 User 的关系"""
        from app.database.session import get_db
        from app.database.models import User, AgentExecution, ExecutionStatus

        db = next(get_db())
        user = db.query(User).first()
        if not user:
            pytest.skip("没有可用用户")

        execution = AgentExecution(
            user_id=user.id,
            status=ExecutionStatus.success,
            duration=1.0,
            tools_called=2,
        )
        db.add(execution)
        db.commit()
        db.refresh(execution)

        assert execution.user is not None
        assert execution.user.id == user.id

        db.delete(execution)
        db.commit()

    def test_alert_model_create(self):
        """验证 AlertRecord 模型可创建和查询"""
        from app.database.session import get_db
        from app.database.models import AlertRecord, AlertLevel, AlertStatus

        db = next(get_db())

        alert = AlertRecord(
            level=AlertLevel.warning,
            title="测试告警",
            message="这是测试告警消息",
            source="test",
            status=AlertStatus.firing,
        )
        db.add(alert)
        db.commit()
        assert alert.id is not None
        assert alert.level == AlertLevel.warning
        assert alert.status == AlertStatus.firing

        db.delete(alert)
        db.commit()
