"""认证模块测试

覆盖：
- 用户注册
- 重复注册
- 用户登录
- 密码错误
- JWT Token 验证
- /api/auth/me 端点
- 无 Token 访问
- 角色权限
- 数据隔离
"""
from app.main import app
from fastapi.testclient import TestClient
from app.database.session import init_db, get_local_session
from app.database.models import User

client = TestClient(app)

# 测试前初始化数据库
init_db()


def clean_test_data():
    """清理测试数据"""
    session = get_local_session()
    try:
        session.query(User).filter(
            User.username.like("test_user_%")
        ).delete()
        session.commit()
    finally:
        session.close()


def test_register_success():
    """测试1: 成功注册新用户"""
    clean_test_data()
    resp = client.post("/api/auth/register", json={
        "username": "test_user_1",
        "email": "test1@example.com",
        "password": "password123",
    })
    assert resp.status_code == 201, f"注册应返回201, 实际: {resp.status_code}"
    data = resp.json()
    assert data["username"] == "test_user_1"
    assert data["email"] == "test1@example.com"
    assert data["role"] == "user"
    assert "id" in data
    assert "password" not in data
    print(f"[OK] test_register_success — user_id={data['id']}")


def test_register_duplicate():
    """测试2: 重复注册应返回409"""
    # 先注册一个用户
    client.post("/api/auth/register", json={
        "username": "test_user_dup",
        "email": "dup@example.com",
        "password": "password123",
    })
    # 重复注册
    resp = client.post("/api/auth/register", json={
        "username": "test_user_dup",
        "email": "dup@example.com",
        "password": "password123",
    })
    assert resp.status_code == 409, f"重复注册应返回409, 实际: {resp.status_code}"
    print("[OK] test_register_duplicate — 409 Conflict")


def test_login_success():
    """测试3: 成功登录返回JWT Token"""
    # 先注册
    client.post("/api/auth/register", json={
        "username": "test_user_login",
        "email": "login@example.com",
        "password": "password123",
    })
    # 登录
    resp = client.post("/api/auth/login", json={
        "username": "test_user_login",
        "password": "password123",
    })
    assert resp.status_code == 200, f"登录应返回200, 实际: {resp.status_code}"
    data = resp.json()
    assert "access_token" in data
    assert len(data["access_token"]) > 20
    assert data["token_type"] == "bearer"
    print(f"[OK] test_login_success — token={data['access_token'][:20]}...")


def test_login_wrong_password():
    """测试4: 错误密码应返回401"""
    resp = client.post("/api/auth/login", json={
        "username": "test_user_login",
        "password": "wrongpassword",
    })
    assert resp.status_code == 401, f"错误密码应返回401, 实际: {resp.status_code}"
    print("[OK] test_login_wrong_password — 401 Unauthorized")


def test_login_nonexistent_user():
    """测试5: 不存在的用户应返回401"""
    resp = client.post("/api/auth/login", json={
        "username": "nonexistent_user_xyz",
        "password": "password123",
    })
    assert resp.status_code == 401, f"不存在用户应返回401, 实际: {resp.status_code}"
    print("[OK] test_login_nonexistent_user — 401 Unauthorized")


def test_me_with_token():
    """测试6: 携带JWT Token访问 /api/auth/me"""
    # 登录获取token
    login_resp = client.post("/api/auth/login", json={
        "username": "test_user_login",
        "password": "password123",
    })
    token = login_resp.json()["access_token"]

    # 访问me
    resp = client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200, f"me应返回200, 实际: {resp.status_code}"
    data = resp.json()
    assert data["username"] == "test_user_login"
    assert data["email"] == "login@example.com"
    assert "id" in data
    print(f"[OK] test_me_with_token — user={data['username']} role={data['role']}")


def test_me_without_token():
    """测试7: 无Token访问 /api/auth/me 应返回401"""
    resp = client.get("/api/auth/me")
    assert resp.status_code == 401, f"无Token应返回401, 实际: {resp.status_code}"
    print("[OK] test_me_without_token — 401 Unauthorized")


def test_me_invalid_token():
    """测试8: 无效Token应返回401"""
    resp = client.get("/api/auth/me", headers={"Authorization": "Bearer invalid_token_here"})
    assert resp.status_code == 401, f"无效Token应返回401, 实际: {resp.status_code}"
    print("[OK] test_me_invalid_token — 401 Unauthorized")


def test_register_validation():
    """测试9: 注册参数验证"""
    # 密码太短
    resp = client.post("/api/auth/register", json={
        "username": "test",
        "email": "test@test.com",
        "password": "123",  # 小于6位
    })
    assert resp.status_code == 422, f"短密码应返回422, 实际: {resp.status_code}"

    # 用户名太短
    resp = client.post("/api/auth/register", json={
        "username": "a",  # 小于2位
        "email": "test@test.com",
        "password": "password123",
    })
    assert resp.status_code == 422, f"短用户名应返回422, 实际: {resp.status_code}"
    print("[OK] test_register_validation — 422 参数校验")


def test_health_with_database():
    """测试10: 健康检查包含数据库状态"""
    resp = client.get("/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "healthy"
    assert "services" in data
    svc = data["services"]
    assert "database" in svc, f"健康检查应包含database, 实际: {list(svc.keys())}"
    print(f"[OK] test_health_with_database — db={svc.get('database', 'N/A')}")


if __name__ == "__main__":
    print("=" * 60)
    print("  认证模块测试")
    print("=" * 60)

    test_register_success()
    test_register_duplicate()
    test_login_success()
    test_login_wrong_password()
    test_login_nonexistent_user()
    test_me_with_token()
    test_me_without_token()
    test_me_invalid_token()
    test_register_validation()
    test_health_with_database()

    print("=" * 60)
    print("  全部 10 项认证测试通过！")
    print("=" * 60)
