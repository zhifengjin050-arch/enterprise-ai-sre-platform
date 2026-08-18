"""v3.2.1 Production Hardening 测试。

覆盖 JWT 门禁、/api/system/status 鉴权与响应脱敏。
不修改 Agent / MCP 工具执行逻辑。
"""
from __future__ import annotations

import json

import pytest
from fastapi.testclient import TestClient

from app.config import APP_VERSION, JWT_INSECURE_PRODUCTION_MSG, Settings
from app.database.models import User, UserRole
from app.database.session import get_local_session, init_db
from app.main import _build_system_status, app

client = TestClient(app)
init_db()

ALLOWED_STATUS_KEYS = {
    "version",
    "environment",
    "database",
    "llm_provider",
    "mcp_enabled",
    "mcp_tools",
    "redis_connected",
    "otel_enabled",
}

FORBIDDEN_SUBSTR = (
    "api_key",
    "jwt_secret",
    "database_url",
    "redis_url",
    "mcp_server_cwd",
    "siliconflow_api_key",
    "password",
    "sk-",
    "sqlite:///",
    "postgresql://",
    "redis://",
)


def test_jwt_production_weak_secret_fails():
    s = Settings(environment="production", jwt_secret="change-me-to-a-random-secret")
    with pytest.raises(RuntimeError) as ei:
        s.validate_production_security()
    assert JWT_INSECURE_PRODUCTION_MSG in str(ei.value)


def test_jwt_production_short_secret_fails():
    s = Settings(environment="production", jwt_secret="short-key")
    with pytest.raises(RuntimeError) as ei:
        s.validate_production_security()
    assert JWT_INSECURE_PRODUCTION_MSG in str(ei.value)


def test_jwt_production_contains_secret_word_fails():
    s = Settings(environment="production", jwt_secret="this-is-a-very-long-secret-key-value-32")
    with pytest.raises(RuntimeError) as ei:
        s.validate_production_security()
    assert JWT_INSECURE_PRODUCTION_MSG in str(ei.value)


def test_jwt_production_contains_test_fails():
    s = Settings(environment="production", jwt_secret="abcdefghijklmnopqrstuvwxyz012345-test")
    with pytest.raises(RuntimeError) as ei:
        s.validate_production_security()
    assert JWT_INSECURE_PRODUCTION_MSG in str(ei.value)


def test_jwt_development_default_secret_succeeds():
    s = Settings(environment="development", jwt_secret="change-me-to-a-random-secret")
    s.validate_production_security()


def test_jwt_production_strong_secret_succeeds():
    s = Settings(
        environment="production",
        jwt_secret="xk9mP2qR7wL4nV8bY3cH6jF1aD5tG0uZ",
    )
    s.validate_production_security()


def test_app_version_is_321():
    assert APP_VERSION in ("3.2.1", "3.3.0")  # 兼容旧版测试


def _register_and_login(username: str) -> str:
    client.post(
        "/api/auth/register",
        json={
            "username": username,
            "email": f"{username}@local.test",
            "password": "webtest123",
        },
    )
    resp = client.post(
        "/api/auth/login",
        json={"username": username, "password": "webtest123"},
    )
    assert resp.status_code == 200, resp.text
    return resp.json()["access_token"]


def test_system_status_requires_jwt():
    resp = client.get("/api/system/status")
    assert resp.status_code == 401


def test_system_status_dev_logged_in_ok():
    token = _register_and_login("v321_status_user")
    resp = client.get("/api/system/status", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert set(data.keys()) == ALLOWED_STATUS_KEYS
    assert data["version"] == "3.2.1"
    assert data["database"] in ("sqlite", "postgresql", "other")
    assert isinstance(data["mcp_enabled"], bool)
    assert isinstance(data["mcp_tools"], int)
    assert isinstance(data["redis_connected"], bool)
    assert isinstance(data["otel_enabled"], bool)


def test_system_status_payload_has_no_secrets():
    payload = _build_system_status()
    blob = json.dumps(payload, ensure_ascii=False).lower()
    assert set(payload.keys()) == ALLOWED_STATUS_KEYS
    for frag in FORBIDDEN_SUBSTR:
        assert frag not in blob, f"leaked {frag}"
    for key in payload:
        assert "url" not in key.lower()
        assert "secret" not in key.lower()
        assert "token" not in key.lower()
        assert "cwd" not in key.lower()
        assert "path" not in key.lower()


def test_system_status_production_user_forbidden(monkeypatch):
    from app.config import settings as live

    token = _register_and_login("v321_prod_user")
    monkeypatch.setattr(live, "environment", "production")
    try:
        resp = client.get("/api/system/status", headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 403
    finally:
        monkeypatch.setattr(live, "environment", "development")


def test_system_status_production_admin_ok(monkeypatch):
    from app.config import settings as live

    username = "v321_prod_admin"
    token = _register_and_login(username)
    db = get_local_session()
    try:
        user = db.query(User).filter(User.username == username).first()
        assert user is not None
        user.role = UserRole.admin
        db.commit()
    finally:
        db.close()

    monkeypatch.setattr(live, "environment", "production")
    try:
        resp = client.get("/api/system/status", headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 200, resp.text
        assert resp.json()["version"] == "3.2.1"
    finally:
        monkeypatch.setattr(live, "environment", "development")
