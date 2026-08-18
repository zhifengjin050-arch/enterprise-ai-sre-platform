"""端到端验证: TestClient 模拟 FastAPI + 前端 + Agent"""

import sys, io, os
os.chdir(r"D:\代码项目\AI Agent项目\项目1：AI DevOps Assistant 在线版")
sys.path.insert(0, os.getcwd())
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

from app.main import app
from fastapi.testclient import TestClient

client = TestClient(app)

print("=" * 70)
print("  AI 智能运维助手 — E2E 测试 v1.1")
print("=" * 70)

# Test 1: Health check
resp = client.get("/health")
assert resp.status_code == 200
data = resp.json()
assert data["status"] == "healthy"
assert "version" in data
assert "services" in data
assert "database" in data["services"]
print(f"[OK] GET /health → {data['status']} v{data['version']}")
print(f"     Services: {data['services']}")

# Test 2: Server status
resp = client.get("/api/server/status")
assert resp.status_code == 200
data = resp.json()
assert "cpu" in data
assert "memory" in data
print(f"[OK] GET /api/server/status → CPU: {data['cpu']['percent']}%")

# Test 3: Frontend page
resp = client.get("/")
assert resp.status_code == 200
assert "AI" in resp.text
print(f"[OK] GET / → {len(resp.text)} chars")

# Test 4: Static CSS
resp = client.get("/static/style.css")
assert resp.status_code == 200
print(f"[OK] Static CSS: {len(resp.text)} chars")

# Test 5: Static JS
resp = client.get("/static/app.js")
assert resp.status_code == 200
print(f"[OK] Static JS: {len(resp.text)} chars")

# Test 6: Chat greeting
resp = client.post("/api/chat", json={"message": "你好", "session_id": "e2e"})
assert resp.status_code == 200
data = resp.json()
assert len(data.get("report", "")) > 50
assert "trace" in data
print(f"[OK] POST /api/chat (greeting) → {len(data['report'])} chars, {len(data['trace'])} trace steps")

# Test 7: Chat with tool calling
resp = client.post("/api/chat", json={"message": "检查服务器健康状态", "session_id": "e2e"})
assert resp.status_code == 200
data = resp.json()
assert "CPU" in data.get("report", "") or "cpu" in data.get("report", "").lower()
assert "trace" in data
print(f"[OK] POST /api/chat (server health) → {len(data['report'])} chars, {len(data['trace'])} trace steps")
for t in data.get("trace", []):
    print(f"     [{t['status']}] {t['step']} ({t.get('duration_ms',0):.0f}ms)")

# Test 8: 422 validation (empty message)
resp = client.post("/api/chat", json={"message": "", "session_id": "e2e"})
assert resp.status_code == 422
print("[OK] POST /api/chat (empty) → 422 参数校验")

# Test 9: 404 handling
resp = client.get("/non-existent")
assert resp.status_code == 404
print("[OK] GET /non-existent → 404")

# Test 10: Health check version
resp = client.get("/health")
data = resp.json()
assert data["version"] == "1.3.0"
print(f"[OK] GET /health version → {data['version']}")

# Test 11: Server status structure
resp = client.get("/api/server/status")
data = resp.json()
assert isinstance(data.get("disks", []), list)
assert isinstance(data.get("cpu", {}), dict)
assert isinstance(data.get("memory", {}), dict)
print(f"[OK] Server status — cpu={len(data.get('cpu', {}))} fields, memory={len(data.get('memory', {}))} fields, disks={len(data.get('disks', []))}")

# Test 12: Auth routes available
resp = client.post("/api/auth/register", json={
    "username": "e2e_test_user",
    "email": "e2e@test.com",
    "password": "testpass123",
})
assert resp.status_code in (201, 409)  # 201 if new, 409 if already exists
print(f"[OK] POST /api/auth/register → {resp.status_code}")

# Test 13: Login with test user
resp = client.post("/api/auth/login", json={
    "username": "e2e_test_user",
    "password": "testpass123",
})
assert resp.status_code == 200
token = resp.json().get("access_token")
assert token is not None
print(f"[OK] POST /api/auth/login → token received ({len(token)} chars)")

# Test 14: Auth me endpoint
resp = client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})
assert resp.status_code == 200
data = resp.json()
assert data["username"] == "e2e_test_user"
print(f"[OK] GET /api/auth/me → {data['username']} role={data['role']}")

# Test 15: Auth me without token
resp = client.get("/api/auth/me")
assert resp.status_code == 401
print(f"[OK] GET /api/auth/me (no token) → 401")

# Test 16: Create conversation
resp = client.post("/api/conversations", json={"title": "E2E Test"}, headers={"Authorization": f"Bearer {token}"})
assert resp.status_code == 200
data = resp.json()
assert "id" in data
conv_id = data["id"]
print(f"[OK] POST /api/conversations → id={conv_id}")

# Test 17: List conversations
resp = client.get("/api/conversations", headers={"Authorization": f"Bearer {token}"})
assert resp.status_code == 200
data = resp.json()
assert isinstance(data, list)
print(f"[OK] GET /api/conversations → {len(data)} conversations")

# Test 18: Get conversation detail
resp = client.get(f"/api/conversations/{conv_id}", headers={"Authorization": f"Bearer {token}"})
assert resp.status_code == 200
data = resp.json()
assert data["id"] == conv_id
assert "messages" in data
print(f"[OK] GET /api/conversations/{conv_id} → {len(data['messages'])} messages")

# Test 19: Delete conversation
resp = client.delete(f"/api/conversations/{conv_id}", headers={"Authorization": f"Bearer {token}"})
assert resp.status_code == 200
print(f"[OK] DELETE /api/conversations/{conv_id} → 200")

# Test 20: Chat with authenticated user (should save to db)
resp = client.post("/api/chat", json={
    "message": "你好",
    "session_id": "auth-test",
}, headers={"Authorization": f"Bearer {token}"})
assert resp.status_code == 200
data = resp.json()
assert "conversation_id" in data
print(f"[OK] POST /api/chat (authenticated) → conversation_id={data.get('conversation_id')}")

# Test 21: Server management - create
resp = client.post("/api/servers", json={
    "name": "e2e-server",
    "host": "192.168.1.10",
    "port": 22,
    "username": "admin",
    "auth_type": "password",
    "auth_credential": "test-pw",
    "description": "E2E 测试服务器",
}, headers={"Authorization": f"Bearer {token}"})
assert resp.status_code == 200
server = resp.json()
server_id = server["id"]
assert server["name"] == "e2e-server"
print(f"[OK] POST /api/servers → id={server_id} name={server['name']}")

# Test 22: Server management - list
resp = client.get("/api/servers", headers={"Authorization": f"Bearer {token}"})
assert resp.status_code == 200
servers = resp.json()
assert isinstance(servers, list)
assert len(servers) >= 1
print(f"[OK] GET /api/servers → {len(servers)} servers")

# Test 23: Server management - get
resp = client.get(f"/api/servers/{server_id}", headers={"Authorization": f"Bearer {token}"})
assert resp.status_code == 200
data = resp.json()
assert data["id"] == server_id
assert data["host"] == "192.168.1.10"
print(f"[OK] GET /api/servers/{server_id} → {data['host']}:{data['port']}")

# Test 24: Server management - update
resp = client.put(f"/api/servers/{server_id}", json={
    "description": "已更新描述",
    "port": 2222,
}, headers={"Authorization": f"Bearer {token}"})
assert resp.status_code == 200
data = resp.json()
assert data["port"] == 2222
assert data["description"] == "已更新描述"
print(f"[OK] PUT /api/servers/{server_id} → port={data['port']}")

# Test 25: Server management - test connection
resp = client.post(f"/api/servers/{server_id}/test-connection", headers={"Authorization": f"Bearer {token}"})
assert resp.status_code == 200
data = resp.json()
assert "success" in data
print(f"[OK] POST /api/servers/{server_id}/test-connection → success={data['success']}")

# Test 26: Server management - delete
resp = client.delete(f"/api/servers/{server_id}", headers={"Authorization": f"Bearer {token}"})
assert resp.status_code == 200
print(f"[OK] DELETE /api/servers/{server_id} → 200")

# Test 27: Server management - verify deleted
resp = client.get(f"/api/servers/{server_id}", headers={"Authorization": f"Bearer {token}"})
assert resp.status_code == 404
print(f"[OK] GET /api/servers/{server_id} after delete → 404")

# Test 28: Server management - unauthorized
resp = client.get("/api/servers")
assert resp.status_code == 401
print(f"[OK] GET /api/servers (no auth) → 401")

# Test 29: Server management - duplicate name
client.post("/api/servers", json={
    "name": "e2e-dup-test",
    "host": "10.0.0.1",
    "port": 22,
    "username": "admin",
    "auth_type": "password",
    "auth_credential": "pw",
}, headers={"Authorization": f"Bearer {token}"})
resp = client.post("/api/servers", json={
    "name": "e2e-dup-test",
    "host": "10.0.0.2",
    "port": 22,
    "username": "admin",
    "auth_type": "password",
    "auth_credential": "pw",
}, headers={"Authorization": f"Bearer {token}"})
assert resp.status_code == 409
print(f"[OK] POST /api/servers (duplicate name) → 409")

# Test 30: Health shows servers_managed
resp = client.get("/health")
data = resp.json()
assert "servers_managed" in data
print(f"[OK] GET /health servers_managed={data['servers_managed']}")

print("\n" + "=" * 70)
print(f"  全部 30 项 E2E 测试通过！（版本 {data['version']}）")
print(f"  Services: {data['services']}")
print("=" * 70)
