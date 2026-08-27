# ============================================================
# Enterprise AI DevOps Agent — 安全测试
# 覆盖：JWT安全、权限隔离、API限流、输入校验
# ============================================================

import pytest
import time
import uuid
from datetime import timedelta, timezone
from fastapi.testclient import TestClient
from starlette.testclient import WebSocketDenialResponse
from starlette.websockets import WebSocketDisconnect
from app.main import app
from app.auth.jwt import create_access_token, decode_access_token
from app.auth.password import hash_password, verify_password
from app.config import settings
from app.database.session import init_db

client = TestClient(app)

# 初始化数据库（安全测试使用数据库）
init_db()


# ============================================================
# 辅助函数
# ============================================================

def _register_user(username: str, password: str = "TestPass123!",
                   email: str = None):
    if email is None:
        email = f"{username}@test.com"
    # 如果用户已存在，先清理
    resp = client.post(
        "/api/auth/register",
        json={"username": username, "email": email, "password": password}
    )
    return resp


def _login_user(username: str, password: str = "TestPass123!"):
    resp = client.post(
        "/api/auth/login",
        json={"username": username, "password": password}
    )
    return resp


def _create_test_user(username: str, password: str = "TestPass123!"):
    """注册+登录辅助，返回 token"""
    _register_user(username, password)
    resp = _login_user(username, password)
    if resp.status_code != 200:
        return None
    return resp.json().get("access_token")


# ============================================================
# JWT 安全测试
# ============================================================

class TestJWTSecurity:
    """JWT Token 安全测试"""

    def test_jwt_token_expired(self):
        """过期 Token 应解码失败"""
        # create_access_token 的 expires_delta 以分钟为单位（int）
        expired_token = create_access_token(
            data={"sub": "99999"},
            expires_delta=-1  # -1 分钟 = 已过期
        )
        assert expired_token is not None
        # decode_access_token 对过期 token 应返回 None
        decoded = decode_access_token(expired_token)
        assert decoded is None, "过期 Token 应解码失败"

    def test_jwt_token_malformed(self):
        """畸形 Token 应被拒绝"""
        response = client.get(
            "/api/auth/me",
            headers={"Authorization": "Bearer this.is.not.a.valid.jwt"}
        )
        assert response.status_code == 401

    def test_jwt_token_wrong_secret(self):
        """使用错误密钥签名的 Token 应被拒绝"""
        import jwt as pyjwt
        payload = {
            "sub": "testuser",
            "exp": time.time() + 3600
        }
        token = pyjwt.encode(payload, "wrong-secret-key", algorithm="HS256")
        response = client.get(
            "/api/auth/me",
            headers={"Authorization": f"Bearer {token}"}
        )
        assert response.status_code == 401

    def test_jwt_token_no_token(self):
        """未提供 Token 应返回 401"""
        response = client.get("/api/auth/me")
        assert response.status_code == 401

    def test_jwt_token_empty_header(self):
        """空的 Authorization 头应返回 401"""
        response = client.get(
            "/api/auth/me",
            headers={"Authorization": ""}
        )
        assert response.status_code == 401

    def test_jwt_token_no_bearer_prefix(self):
        """缺少 Bearer 前缀应返回 401"""
        response = client.get(
            "/api/auth/me",
            headers={"Authorization": "some-random-token-string"}
        )
        assert response.status_code == 401

    def test_password_hash_security(self):
        """密码哈希测试"""
        password = "TestPassword123!"
        hashed = hash_password(password)
        assert hashed != password
        assert verify_password(password, hashed) is True
        assert verify_password("WrongPassword", hashed) is False

    def test_password_hash_uniqueness(self):
        """相同密码应生成不同哈希"""
        password = "SamePassword123!"
        hash1 = hash_password(password)
        hash2 = hash_password(password)
        assert hash1 != hash2
        assert verify_password(password, hash1) is True
        assert verify_password(password, hash2) is True


# ============================================================
# 权限隔离测试
# ============================================================

class TestRBACSecurity:
    """RBAC 权限隔离测试"""

    def _ensure_user(self, username: str):
        """确保用户存在并返回 token"""
        from app.database.session import get_local_session
        from app.database.models import User
        db = get_local_session()
        user = db.query(User).filter(User.username == username).first()
        db.close()
        if user:
            return _login_user(username).json().get("access_token")
        return _create_test_user(username)

    def test_user_can_access_own_data(self):
        """用户登录后可访问自己的信息"""
        token = _create_test_user("sec_own_data_test")
        assert token is not None, "创建用户失败"
        response = client.get(
            "/api/auth/me",
            headers={"Authorization": f"Bearer {token}"}
        )
        assert response.status_code == 200
        assert response.json()["username"] == "sec_own_data_test"

    def test_user_data_isolation(self):
        """用户数据隔离：用户 A 不能看到用户 B 的数据"""
        token_a = _create_test_user("sec_isol_a")
        token_b = _create_test_user("sec_isol_b")
        assert token_a is not None
        assert token_b is not None

        name_a = f"isol-test-svr-{uuid.uuid4().hex[:8]}"
        resp = client.post(
            "/api/servers",
            headers={"Authorization": f"Bearer {token_a}"},
            json={"name": name_a, "host": "10.0.0.1",
                  "port": 22, "username": "root",
                  "auth_credential": "test-password"}
        )
        assert resp.status_code == 200

        # 用户 B 应该看不到 A 的服务器
        resp_b = client.get(
            "/api/servers",
            headers={"Authorization": f"Bearer {token_b}"}
        )
        assert resp_b.status_code == 200
        names = [s.get("name") for s in resp_b.json()]
        assert name_a not in names

    def test_user_cannot_delete_other_user_server(self):
        """用户 A 不能删除用户 B 的服务器"""
        token_a = _create_test_user("sec_del_a")
        token_b = _create_test_user("sec_del_b")

        name_a = f"del-test-svr-{uuid.uuid4().hex[:8]}"
        resp = client.post(
            "/api/servers",
            headers={"Authorization": f"Bearer {token_a}"},
            json={"name": name_a, "host": "10.0.0.2",
                  "port": 22, "username": "root",
                  "auth_credential": "test-password"}
        )
        assert resp.status_code == 200
        server_id = resp.json().get("id")

        # 用户 B 尝试删除，应返回 404（数据隔离）
        resp_del = client.delete(
            f"/api/servers/{server_id}",
            headers={"Authorization": f"Bearer {token_b}"}
        )
        assert resp_del.status_code == 404

    def test_api_requires_auth(self):
        """认证后才能访问受保护 API"""
        # /api/servers
        assert client.get("/api/servers").status_code == 401
        # /api/conversations
        assert client.get("/api/conversations").status_code == 401
        # /api/monitoring/current
        assert client.get("/api/monitoring/current").status_code == 401
        # /api/server/status
        assert client.get("/api/server/status").status_code == 401

    def test_chat_works_without_auth(self):
        """开发环境聊天接口允许未认证访问（不会创建会话）"""
        resp = client.post("/api/chat", json={"message": "ping"})
        assert resp.status_code == 200

    def test_chat_requires_auth_in_production(self, monkeypatch):
        """生产环境聊天接口必须登录"""
        monkeypatch.setattr(settings, "environment", "production")
        resp = client.post("/api/chat", json={"message": "ping"})
        assert resp.status_code == 401
        resp_stream = client.post("/api/chat/stream", json={"message": "ping"})
        assert resp_stream.status_code == 401

    def test_server_status_with_auth(self):
        token = _create_test_user(f"status_{uuid.uuid4().hex[:8]}")
        resp = client.get(
            "/api/server/status",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 200
        assert "cpu" in resp.json()


# ============================================================
# WebSocket 鉴权
# ============================================================

class TestWebSocketAuth:
    def _assert_ws_rejected(self, path: str) -> None:
        try:
            with client.websocket_connect(path) as ws:
                ws.receive_text()
            pytest.fail(f"WebSocket 应被拒绝: {path}")
        except (WebSocketDisconnect, WebSocketDenialResponse):
            return
        except BaseExceptionGroup as eg:
            if any(isinstance(e, (WebSocketDisconnect, WebSocketDenialResponse)) for e in eg.exceptions):
                return
            raise

    def test_ws_rejects_anonymous(self):
        self._assert_ws_rejected("/ws/chat/1")

    def test_ws_accepts_valid_token(self):
        token = _create_test_user(f"ws_ok_{uuid.uuid4().hex[:8]}")
        assert token
        with client.websocket_connect(f"/ws/chat/0?token={token}"):
            pass

    def test_ws_rejects_foreign_conversation(self):
        token_a = _create_test_user(f"ws_a_{uuid.uuid4().hex[:8]}")
        token_b = _create_test_user(f"ws_b_{uuid.uuid4().hex[:8]}")
        conv = client.post(
            "/api/conversations",
            json={"title": "ws-iso"},
            headers={"Authorization": f"Bearer {token_a}"},
        )
        assert conv.status_code == 200
        cid = conv.json()["id"]
        self._assert_ws_rejected(f"/ws/chat/{cid}?token={token_b}")


# ============================================================
# API 限流测试
# ============================================================

class TestRateLimiting:
    """API 限流测试"""

    def test_health_endpoint_no_rate_limit(self):
        """健康检查接口不限流"""
        for _ in range(10):
            resp = client.get("/health")
            assert resp.status_code == 200

    def test_metrics_endpoint_no_rate_limit(self):
        """指标接口不限流"""
        resp = client.get("/metrics")
        assert resp.status_code == 200


# ============================================================
# 输入校验安全测试
# ============================================================

class TestInputValidation:
    """输入校验安全测试"""

    def test_register_requires_email(self):
        """注册需要 email 字段"""
        resp = client.post(
            "/api/auth/register",
            json={"username": "testuser", "password": "TestPass123!"}
        )
        assert resp.status_code == 422

    def test_register_short_username_rejected(self):
        """过短的用户名（< 2 字符）应被拒绝"""
        resp = client.post(
            "/api/auth/register",
            json={"username": "a", "email": "a@t.com", "password": "TestPass123!"}
        )
        assert resp.status_code == 422

    def test_register_short_password_rejected(self):
        """过短的密码（< 6 字符）应被拒绝"""
        resp = client.post(
            "/api/auth/register",
            json={"username": "vali duser", "email": "v@t.com", "password": "ab"}
        )
        assert resp.status_code == 422

    def test_register_empty_password_rejected(self):
        """空密码应被拒绝"""
        resp = client.post(
            "/api/auth/register",
            json={"username": "emptypwuser", "email": "e@t.com", "password": ""}
        )
        assert resp.status_code == 422

    def test_login_wrong_password(self):
        """错误密码登录应返回 401"""
        _register_user("login_wp_test")
        resp = _login_user("login_wp_test", "WrongPassword999!")
        assert resp.status_code == 401

    def test_login_nonexistent_user(self):
        """不存在的用户登录应返回 401"""
        resp = _login_user("user_does_not_exist_xyz")
        assert resp.status_code == 401

    def test_invalid_json_body(self):
        """无效 JSON body 应返回 422"""
        resp = client.post(
            "/api/auth/register",
            content="this is not json",
            headers={"Content-Type": "application/json"}
        )
        assert resp.status_code == 422

    def test_special_chars_in_server_name(self):
        """服务器名中的合法特殊字符应被接受"""
        token = _create_test_user("sec_svr_nm")
        assert token is not None
        suffix = uuid.uuid4().hex[:6]
        names = [f"normal-server-{suffix}", f"server-with-dashes-{suffix}", f"server_123_{suffix}"]
        for name in names:
            resp = client.post(
                "/api/servers",
                headers={"Authorization": f"Bearer {token}"},
                json={"name": name, "host": "10.0.0.1",
                      "port": 22, "username": "root",
                      "auth_credential": "test-password"}
            )
            assert resp.status_code == 200, f"创建服务器 '{name}' 失败: {resp.status_code} {resp.text}"

    def test_register_valid_user_succeeds(self):
        """合法注册应成功"""
        import random
        suffix = random.randint(10000, 99999)
        resp = client.post(
            "/api/auth/register",
            json={
                "username": f"valid_user_{suffix}",
                "email": f"valid_{suffix}@test.com",
                "password": "ValidPass123!"
            }
        )
        assert resp.status_code == 201

    def test_register_disabled_in_production(self, monkeypatch):
        monkeypatch.setattr(settings, "environment", "production")
        monkeypatch.setattr(settings, "allow_register", False)
        resp = client.post(
            "/api/auth/register",
            json={
                "username": f"prod_reg_{uuid.uuid4().hex[:8]}",
                "email": f"prod_reg_{uuid.uuid4().hex[:8]}@test.com",
                "password": "ValidPass123!",
            },
        )
        assert resp.status_code == 403


# ============================================================
# 安全配置测试
# ============================================================

class TestSecurityConfig:
    """安全配置测试"""

    def test_rate_limit_configured(self):
        """速率限制应已配置"""
        # settings 使用小写字段名（Pydantic settings convention）
        assert hasattr(settings, 'rate_limit_per_minute')
        assert settings.rate_limit_per_minute >= 10

    def test_cors_origins_configured(self):
        """CORS 源应已配置"""
        assert settings.cors_origins is not None
        assert len(settings.cors_origins) > 0

    def test_jwt_expire_reasonable(self):
        """JWT 过期时间应在合理范围（1-1440 分钟）"""
        assert 1 <= settings.jwt_expire_minutes <= 1440

    def test_environment_set(self):
        """环境变量应已设置"""
        env = settings.environment
        assert env in ("development", "test", "production")

    def test_database_url_configured(self):
        """数据库 URL 应已配置"""
        url = settings.database_url
        assert url is not None
        assert len(str(url)) > 0

    def test_log_level_configured(self):
        """日志级别应已配置"""
        assert settings.log_level in ("DEBUG", "INFO", "WARNING", "ERROR")
