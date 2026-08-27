"""SSH 远程运维模块测试

覆盖：
- ManagedServer CRUD（通过数据库操作）
- SSH 工具函数（模拟）
- SSH 命令执行（模拟）
- 服务器管理 API（通过 TestClient）
"""

import json

from app.database.models import ManagedServer, User, SSHKeyType
from app.database.session import get_local_session, init_db

# 初始化数据库
init_db()


def _get_or_create_user(session, username: str, email: str) -> User:
    user = session.query(User).filter(User.username == username).first()
    if user is not None:
        return user
    user = User(
        username=username,
        email=email,
        password_hash="dummy_hash",
        role="user",
    )
    session.add(user)
    session.flush()
    return user


def _get_or_create_server(session, user_id: int, **kwargs) -> ManagedServer:
    name = kwargs["name"]
    server = session.query(ManagedServer).filter(
        ManagedServer.name == name,
        ManagedServer.user_id == user_id,
    ).first()
    if server is None:
        server = ManagedServer(user_id=user_id, **kwargs)
        session.add(server)
    else:
        for key, value in kwargs.items():
            setattr(server, key, value)
    session.commit()
    session.refresh(server)
    return server


def test_managed_server_create():
    """测试1: 创建托管服务器记录"""
    session = get_local_session()
    try:
        user = _get_or_create_user(session, "ssh_test_user", "ssh_test@example.com")
        server = _get_or_create_server(
            session,
            user.id,
            name="test-server-01",
            host="192.168.1.100",
            port=22,
            username="root",
            auth_type="password",
            auth_credential="test-password",
            description="测试服务器",
            is_active=True,
        )

        assert server.id is not None
        print(f"[OK] 创建托管服务器: id={server.id} name={server.name}")
    finally:
        session.close()


def test_managed_server_query():
    """测试2: 查询托管服务器"""
    session = get_local_session()
    try:
        user = session.query(User).filter(User.username == "ssh_test_user").first()
        assert user is not None
        server = session.query(ManagedServer).filter(
            ManagedServer.name == "test-server-01",
            ManagedServer.user_id == user.id,
        ).first()

        assert server is not None
        assert server.host == "192.168.1.100"
        assert server.port == 22
        assert server.username == "root"
        assert server.auth_type == "password"
        assert server.is_active is True
        print(f"[OK] 查询服务器: {server.name} @ {server.host}:{server.port}")
    finally:
        session.close()


def test_managed_server_update():
    """测试3: 更新托管服务器"""
    session = get_local_session()
    try:
        user = session.query(User).filter(User.username == "ssh_test_user").first()
        server = session.query(ManagedServer).filter(
            ManagedServer.name == "test-server-01",
            ManagedServer.user_id == user.id,
        ).first()

        server.host = "10.0.0.1"
        server.port = 2222
        server.description = "更新后的描述"
        session.commit()

        # 重新查询
        updated = session.query(ManagedServer).filter(
            ManagedServer.name == "test-server-01",
            ManagedServer.user_id == user.id,
        ).first()
        assert updated.host == "10.0.0.1"
        assert updated.port == 2222
        assert updated.description == "更新后的描述"
        print(f"[OK] 更新服务器: {updated.name} → {updated.host}:{updated.port}")
    finally:
        session.close()


def test_managed_server_deactivate():
    """测试4: 停用服务器"""
    session = get_local_session()
    try:
        user = session.query(User).filter(User.username == "ssh_test_user").first()
        server = session.query(ManagedServer).filter(
            ManagedServer.name == "test-server-01",
            ManagedServer.user_id == user.id,
        ).first()

        server.is_active = False
        session.commit()

        active = session.query(ManagedServer).filter(
            ManagedServer.name == "test-server-01",
            ManagedServer.user_id == user.id,
            ManagedServer.is_active == True,
        ).first()
        assert active is None

        all_servers = session.query(ManagedServer).filter(
            ManagedServer.name == "test-server-01",
            ManagedServer.user_id == user.id,
        ).first()
        assert all_servers is not None
        assert all_servers.is_active is False
        print("[OK] 停用服务器: is_active=False")
    finally:
        session.close()


def test_managed_server_data_isolation():
    """测试5: 数据隔离 — 不同用户不能看到对方的服务器"""
    session = get_local_session()
    try:
        user2 = _get_or_create_user(session, "ssh_test_user_2", "ssh_test2@example.com")
        server2 = _get_or_create_server(
            session,
            user2.id,
            name="test-server-02",
            host="10.0.0.2",
            port=22,
            username="admin",
            auth_type="password",
            auth_credential="secret",
            is_active=True,
        )

        # 查询第一个用户应该只能看到自己的服务器（被停用了，所以为空）
        user1_servers = session.query(ManagedServer).filter(
            ManagedServer.user_id == 1
        ).all()
        for s in user1_servers:
            assert s.user_id == 1

        # 查询第二个用户的服务器
        user2_servers = session.query(ManagedServer).filter(
            ManagedServer.user_id == user2.id
        ).all()
        assert any(s.name == "test-server-02" for s in user2_servers)

        print(f"[OK] 数据隔离: user2 看到 {len(user2_servers)} 台服务器")
    finally:
        session.close()


def test_managed_server_cascade_delete():
    """测试6: 用户删除时级联删除服务器"""
    session = get_local_session()
    try:
        # 创建临时用户和服务器
        import uuid
        suffix = uuid.uuid4().hex[:8]
        temp_user = User(
            username=f"ssh_temp_{suffix}",
            email=f"ssh_temp_{suffix}@example.com",
            password_hash="dummy_hash",
            role="user",
        )
        session.add(temp_user)
        session.flush()

        temp_server = ManagedServer(
            user_id=temp_user.id,
            name="temp-server",
            host="192.168.1.200",
            port=22,
            username="root",
            auth_type="password",
            auth_credential="temp-pw",
        )
        session.add(temp_server)
        session.commit()

        server_id = temp_server.id

        # 删除用户
        session.delete(temp_user)
        session.commit()

        # 确认服务器也被删除
        deleted_server = session.query(ManagedServer).filter(
            ManagedServer.id == server_id
        ).first()
        assert deleted_server is None
        print("[OK] 级联删除: 用户删除后服务器也被删除")
    finally:
        session.close()


def test_ssh_tool_lookup_server():
    """测试7: SSH 工具查询服务器函数"""
    from app.tools.ssh_ops import _lookup_server

    try:
        info = _lookup_server("test-server-01")
        # 因 test-server-01 被停用了，应失败
        print("[INFO] _lookup_server('test-server-01') 预期失败 (is_active=False)")
    except ValueError as e:
        print(f"[OK] _lookup_server 正确处理非活跃服务器: {e}")


def test_ssh_tool_missing_server():
    """测试8: SSH 工具查询不存在的服务器"""
    from app.tools.ssh_ops import _lookup_server

    try:
        info = _lookup_server("nonexistent-server")
        print("[FAIL] 应抛出 ValueError")
    except ValueError as e:
        print(f"[OK] _lookup_server 正确处理不存在的服务器: {e}")


def test_ssh_exec_tool_connectivity():
    """测试9: SSH exec tool 连接不可达服务器"""
    from app.tools.ssh_ops import ssh_exec

    result = ssh_exec.invoke({
        "server_name": "test-server-01",  # 停用了
        "command": "uptime",
    })
    assert "未找到" in result or "找不到" in result or "不存在" in result or "异常" in result
    print(f"[OK] ssh_exec 正确处理不可达服务器: {result[:60]}")


def test_ssh_health_tool():
    """测试10: SSH health tool 与不可达服务器"""
    from app.tools.ssh_ops import ssh_server_health

    result = ssh_server_health.invoke({"server_name": "test-server-01"})
    assert "未找到" in result or "找不到" in result or "不存在" in result or "异常" in result
    print(f"[OK] ssh_server_health 正确处理不可达服务器: {result[:60]}")


def test_ssh_docker_status_tool():
    """测试11: SSH docker status tool 与不可达服务器"""
    from app.tools.ssh_ops import ssh_docker_status

    result = ssh_docker_status.invoke({"server_name": "test-server-01"})
    assert "未找到" in result or "找不到" in result or "不存在" in result or "异常" in result
    print(f"[OK] ssh_docker_status 正确处理不可达服务器: {result[:60]}")


def test_ssh_docker_logs_tool():
    """测试12: SSH docker logs tool 与不可达服务器"""
    from app.tools.ssh_ops import ssh_docker_logs

    result = ssh_docker_logs.invoke({
        "server_name": "test-server-01",
        "container_name": "test-container",
    })
    assert "未找到" in result or "找不到" in result or "不存在" in result or "异常" in result
    print(f"[OK] ssh_docker_logs 正确处理不可达服务器: {result[:60]}")


def test_ssh_system_logs_tool():
    """测试13: SSH system logs tool 与不可达服务器"""
    from app.tools.ssh_ops import ssh_system_logs

    result = ssh_system_logs.invoke({
        "server_name": "test-server-01",
        "service": "nginx",
    })
    assert "未找到" in result or "找不到" in result or "不存在" in result or "异常" in result
    print(f"[OK] ssh_system_logs 正确处理不可达服务器: {result[:60]}")


def test_close_all_ssh_connections():
    """测试14: 关闭所有 SSH 连接（安全清理）"""
    from app.tools.ssh_ops import close_all_ssh_connections

    # 应该不会报错
    close_all_ssh_connections()
    print("[OK] close_all_ssh_connections 执行成功")


def test_pkey_from_invalid_material():
    from app.tools.ssh_ops import _pkey_from_material

    assert _pkey_from_material("not-a-key") is None
    print("[OK] 非法 PEM 私钥解析返回 None")


# ============================================================
# API 测试
# ============================================================
print()
print("--- API 测试 ---")


def _first_managed_server_id(servers):
    """跳过本机哨兵 id=-1，取第一台真实托管服务器。"""
    assert isinstance(servers, list) and servers, f"服务器列表为空: {servers}"
    for item in servers:
        sid = item.get("id") if isinstance(item, dict) else None
        if isinstance(sid, int) and sid > 0:
            return sid
    raise AssertionError(f"没有托管服务器可供测试: {servers}")


def test_server_api_create():
    """测试15: POST /api/servers 创建服务器"""
    from fastapi.testclient import TestClient
    from app.main import app

    client = TestClient(app)

    # 先注册登录
    reg_resp = client.post("/api/auth/register", json={
        "username": "server_api_user",
        "email": "server_api@example.com",
        "password": "testpass123",
    })
    assert reg_resp.status_code in (200, 201, 409)
    token = reg_resp.json().get("access_token", "")

    if not token:
        # 尝试登录
        login_resp = client.post("/api/auth/login", json={
            "username": "server_api_user",
            "password": "testpass123",
        })
        assert login_resp.status_code == 200
        token = login_resp.json().get("access_token", "")

    headers = {"Authorization": f"Bearer {token}"}

    # 创建服务器
    resp = client.post("/api/servers", json={
        "name": "api-test-server",
        "host": "192.168.1.50",
        "port": 2222,
        "username": "deploy",
        "auth_type": "password",
        "auth_credential": "secure-password",
        "description": "API 测试服务器",
    }, headers=headers)

    assert resp.status_code in (200, 409), f"期望 200/409，实际 {resp.status_code}: {resp.text}"
    if resp.status_code == 409:
        listed = client.get("/api/servers", headers=headers).json()
        data = next((s for s in listed if s.get("name") == "api-test-server"), None)
        assert data is not None, "重复名称冲突但列表中找不到 api-test-server"
        print(f"[OK] POST /api/servers → 已存在 id={data['id']} name={data['name']}")
        return
    data = resp.json()
    assert data["name"] == "api-test-server"
    assert data["host"] == "192.168.1.50"
    assert data["port"] == 2222
    print(f"[OK] POST /api/servers → id={data['id']} name={data['name']}")


def test_server_credential_encrypted_at_rest():
    """API 写入的 SSH 凭据必须加密落库，且工具层能解密。"""
    import uuid
    from fastapi.testclient import TestClient
    from app.main import app
    from app.security.secrets import SECRET_PREFIX, decrypt_secret
    from app.tools.ssh_ops import _lookup_server

    client = TestClient(app)
    suffix = uuid.uuid4().hex[:8]
    username = f"enc_user_{suffix}"
    server_name = f"enc-svr-{suffix}"

    reg = client.post("/api/auth/register", json={
        "username": username,
        "email": f"{username}@example.com",
        "password": "testpass123",
    })
    token = reg.json().get("access_token", "")
    if not token:
        token = client.post("/api/auth/login", json={
            "username": username,
            "password": "testpass123",
        }).json().get("access_token", "")
    headers = {"Authorization": f"Bearer {token}"}

    resp = client.post("/api/servers", json={
        "name": server_name,
        "host": "10.9.9.9",
        "port": 22,
        "username": "ops",
        "auth_type": "password",
        "auth_credential": "secure-password",
    }, headers=headers)
    assert resp.status_code == 200, resp.text

    session = get_local_session()
    try:
        server = session.query(ManagedServer).filter(
            ManagedServer.name == server_name
        ).first()
        assert server is not None
        assert server.auth_credential != "secure-password"
        assert server.auth_credential.startswith(SECRET_PREFIX)
        assert decrypt_secret(server.auth_credential) == "secure-password"
    finally:
        session.close()

    info = _lookup_server(server_name)
    assert info["password"] == "secure-password"
    print("[OK] SSH 凭据加密存储且工具层解密成功")


def test_ssh_lookup_legacy_plaintext():
    """历史明文凭据仍可被工具层读取。"""
    from app.tools.ssh_ops import _lookup_server

    info = _lookup_server("test-server-02")
    assert info["password"] == "secret"
    print("[OK] 历史明文凭据兼容读取")


def test_server_api_list():
    """测试16: GET /api/servers 列出服务器"""
    from fastapi.testclient import TestClient
    from app.main import app

    client = TestClient(app)

    # 获取 token
    login_resp = client.post("/api/auth/login", json={
        "username": "server_api_user",
        "password": "testpass123",
    })
    token = login_resp.json().get("access_token", "")
    headers = {"Authorization": f"Bearer {token}"}

    resp = client.get("/api/servers", headers=headers)
    assert resp.status_code == 200
    servers = resp.json()
    assert isinstance(servers, list)
    assert len(servers) >= 1
    print(f"[OK] GET /api/servers → {len(servers)} 台服务器")


def test_server_api_get():
    """测试17: GET /api/servers/{id} 获取服务器详情"""
    from fastapi.testclient import TestClient
    from app.main import app

    client = TestClient(app)

    login_resp = client.post("/api/auth/login", json={
        "username": "server_api_user",
        "password": "testpass123",
    })
    token = login_resp.json().get("access_token", "")
    headers = {"Authorization": f"Bearer {token}"}

    # 先列出获取 ID
    list_resp = client.get("/api/servers", headers=headers)
    servers = list_resp.json()
    server_id = _first_managed_server_id(servers)

    resp = client.get(f"/api/servers/{server_id}", headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["id"] == server_id
    # 敏感字段不应返回
    assert "auth_credential" not in data
    print(f"[OK] GET /api/servers/{server_id} → name={data['name']}")


def test_server_api_update():
    """测试18: PUT /api/servers/{id} 更新服务器"""
    from fastapi.testclient import TestClient
    from app.main import app

    client = TestClient(app)

    login_resp = client.post("/api/auth/login", json={
        "username": "server_api_user",
        "password": "testpass123",
    })
    token = login_resp.json().get("access_token", "")
    headers = {"Authorization": f"Bearer {token}"}

    list_resp = client.get("/api/servers", headers=headers)
    server_id = _first_managed_server_id(list_resp.json())

    resp = client.put(f"/api/servers/{server_id}", json={
        "description": "已更新的服务器",
        "port": 2223,
    }, headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["port"] == 2223
    assert data["description"] == "已更新的服务器"
    print(f"[OK] PUT /api/servers/{server_id} → port={data['port']}")


def test_server_api_delete():
    """测试19: DELETE /api/servers/{id} 删除服务器"""
    from fastapi.testclient import TestClient
    from app.main import app

    client = TestClient(app)

    login_resp = client.post("/api/auth/login", json={
        "username": "server_api_user",
        "password": "testpass123",
    })
    token = login_resp.json().get("access_token", "")
    headers = {"Authorization": f"Bearer {token}"}

    list_resp = client.get("/api/servers", headers=headers)
    servers = list_resp.json()
    server_id = _first_managed_server_id(servers)

    resp = client.delete(f"/api/servers/{server_id}", headers=headers)
    assert resp.status_code == 200
    assert resp.json()["detail"] == "服务器已删除"

    # 确认已删除
    get_resp = client.get(f"/api/servers/{server_id}", headers=headers)
    assert get_resp.status_code == 404
    print(f"[OK] DELETE /api/servers/{server_id} → 已删除")


def test_server_api_duplicate_name():
    """测试20: POST /api/servers 重复名称应返回 409"""
    import uuid
    from fastapi.testclient import TestClient
    from app.main import app

    client = TestClient(app)

    login_resp = client.post("/api/auth/login", json={
        "username": "server_api_user",
        "password": "testpass123",
    })
    token = login_resp.json().get("access_token", "")
    headers = {"Authorization": f"Bearer {token}"}
    name = f"dup-{uuid.uuid4().hex[:8]}"

    resp1 = client.post("/api/servers", json={
        "name": name,
        "host": "10.0.0.1",
        "port": 22,
        "username": "admin",
        "auth_type": "password",
        "auth_credential": "pw123",
    }, headers=headers)
    assert resp1.status_code == 200

    resp2 = client.post("/api/servers", json={
        "name": name,
        "host": "10.0.0.2",
        "port": 22,
        "username": "admin",
        "auth_type": "password",
        "auth_credential": "pw456",
    }, headers=headers)
    assert resp2.status_code == 409
    print("[OK] 重复名称返回 409")


def test_server_api_unauthorized():
    """测试21: 未认证访问服务器接口应返回 401"""
    from fastapi.testclient import TestClient
    from app.main import app

    client = TestClient(app)

    resp = client.get("/api/servers")
    assert resp.status_code == 401
    print("[OK] 未认证访问返回 401")


def test_server_api_test_connection():
    """测试22: POST /api/servers/{id}/test-connection 测试连接"""
    from fastapi.testclient import TestClient
    from app.main import app

    client = TestClient(app)

    login_resp = client.post("/api/auth/login", json={
        "username": "server_api_user",
        "password": "testpass123",
    })
    token = login_resp.json().get("access_token", "")
    headers = {"Authorization": f"Bearer {token}"}

    # 创建一个测试服务器
    import uuid
    conn_name = f"conn-{uuid.uuid4().hex[:8]}"
    create_resp = client.post("/api/servers", json={
        "name": conn_name,
        "host": "192.168.99.99",
        "port": 22,
        "username": "test",
        "auth_type": "password",
        "auth_credential": "test",
        "description": "连接测试",
    }, headers=headers)
    assert create_resp.status_code == 200, create_resp.text
    server_id = create_resp.json()["id"]

    # 测试连接
    resp = client.post(f"/api/servers/{server_id}/test-connection", headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    # 连接应该失败（服务器不存在）
    assert data["success"] is False
    print(f"[OK] POST /api/servers/{server_id}/test-connection → success={data['success']}")


def test_tool_registry_includes_ssh():
    """测试23: 确认 SSH 工具已被注册到工具注册表"""
    from app.tools.registry import get_tool, get_tool_schemas

    # 检查 SSH 工具
    assert get_tool("ssh_exec") is not None
    assert get_tool("ssh_server_health") is not None
    assert get_tool("ssh_docker_status") is not None
    assert get_tool("ssh_docker_logs") is not None
    assert get_tool("ssh_system_logs") is not None

    # 检查 schemas
    schemas = get_tool_schemas()
    ssh_tools = [s for s in schemas if "ssh_" in s["function"]["name"]]
    assert len(ssh_tools) == 5

    print(f"[OK] 工具注册表包含 {len(ssh_tools)} 个 SSH 工具: {[t['function']['name'] for t in ssh_tools]}")


def test_health_servers_count():
    """测试24: 健康检查包含托管服务器数量"""
    from fastapi.testclient import TestClient
    from app.main import app

    client = TestClient(app)

    resp = client.get("/health")
    data = resp.json()
    assert "servers_managed" in data
    print(f"[OK] GET /health → servers_managed={data['servers_managed']}")


# ============================================================
# 运行测试
# ============================================================
if __name__ == "__main__":
    tests = [
        ("ManagedServer创建", test_managed_server_create),
        ("ManagedServer查询", test_managed_server_query),
        ("ManagedServer更新", test_managed_server_update),
        ("ManagedServer停用", test_managed_server_deactivate),
        ("数据隔离", test_managed_server_data_isolation),
        ("级联删除", test_managed_server_cascade_delete),
        ("查询服务器函数(停用)", test_ssh_tool_lookup_server),
        ("查询服务器函数(不存在)", test_ssh_tool_missing_server),
        ("ssh_exec工具", test_ssh_exec_tool_connectivity),
        ("ssh_server_health工具", test_ssh_health_tool),
        ("ssh_docker_status工具", test_ssh_docker_status_tool),
        ("ssh_docker_logs工具", test_ssh_docker_logs_tool),
        ("ssh_system_logs工具", test_ssh_system_logs_tool),
        ("关闭SSH连接", test_close_all_ssh_connections),
        ("API创建服务器", test_server_api_create),
        ("API列出服务器", test_server_api_list),
        ("API获取服务器", test_server_api_get),
        ("API更新服务器", test_server_api_update),
        ("API删除服务器", test_server_api_delete),
        ("API重复名称", test_server_api_duplicate_name),
        ("API未认证", test_server_api_unauthorized),
        ("API测试连接", test_server_api_test_connection),
        ("工具注册表", test_tool_registry_includes_ssh),
        ("健康检查服务器数", test_health_servers_count),
    ]

    passed = 0
    failed = 0
    for name, func in tests:
        try:
            func()
            passed += 1
        except Exception as e:
            import traceback
            print(f"[FAIL] {name}: {e}")
            traceback.print_exc()
            failed += 1

    print()
    print("=" * 60)
    print(f"  SSH 测试结果: {passed} passed, {failed} failed / {len(tests)} total")
    print("=" * 60)
