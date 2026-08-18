"""Demo 数据导入脚本 — 将 demo/knowledge/ 文档导入知识库

用法:
    cd 项目根目录
    python demo/import_demo_data.py

前置条件:
    1. 后端已启动 (python run.py 或 docker compose up)
    2. 已注册用户并获取 Token (脚本自动注册 admin/admin123)
"""

import sys, os, json, time, uuid
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import httpx

BASE_URL = os.environ.get("DEMO_BASE_URL", "http://localhost:8000")
DEMO_USER = "demo_admin"
DEMO_PASS = "Demo@2026!"


def _register_login():
    """注册并登录 Demo 账号"""
    # 先尝试登录
    resp = httpx.post(f"{BASE_URL}/api/auth/login", json={
        "username": DEMO_USER, "password": DEMO_PASS,
    }, timeout=10)
    if resp.status_code == 200:
        token = resp.json()["access_token"]
        print(f"[OK] 登录成功: {DEMO_USER}")
        return token

    # 登录失败则注册
    resp = httpx.post(f"{BASE_URL}/api/auth/register", json={
        "username": DEMO_USER,
        "email": f"{uuid.uuid4().hex[:8]}@demo.com",
        "password": DEMO_PASS,
    }, timeout=10)
    if resp.status_code == 201:
        # 注册后登录
        resp = httpx.post(f"{BASE_URL}/api/auth/login", json={
            "username": DEMO_USER, "password": DEMO_PASS,
        }, timeout=10)
        if resp.status_code == 200:
            token = resp.json()["access_token"]
            print(f"[OK] 注册并登录成功: {DEMO_USER}")
            return token

    print(f"[FAIL] 注册/登录失败: {resp.status_code} {resp.text[:200]}")
    return None


def _upload_doc(token: str, title: str, content: str) -> bool:
    """上传文档到知识库"""
    headers = {"Authorization": f"Bearer {token}"}
    resp = httpx.post(f"{BASE_URL}/api/knowledge/upload", headers=headers, json={
        "title": title,
        "content": content,
    }, timeout=30)
    if resp.status_code == 200:
        print(f"  [OK] 已导入: {title}")
        return True
    print(f"  [FAIL] {title}: {resp.status_code} {resp.text[:200]}")
    return False


def _load_demo_docs():
    """加载 demo/knowledge/ 目录下的所有文档"""
    demo_dir = os.path.dirname(os.path.abspath(__file__))
    knowledge_dir = os.path.join(demo_dir, "knowledge")

    docs = []
    DEMO_DOCS = [
        ("Kubernetes 生产运维手册", "kubernetes_operation.md"),
        ("Nginx 故障排查指南", "nginx_troubleshooting.md"),
        ("生产部署规范与最佳实践", "production_deployment.md"),
    ]
    for title, fname in DEMO_DOCS:
        fpath = os.path.join(knowledge_dir, fname)
        if not os.path.exists(fpath):
            print(f"  [SKIP] {fname} 不存在，跳过")
            continue
        with open(fpath, "r", encoding="utf-8") as f:
            content = f.read()
        docs.append((title, content))
    return docs


def main():
    print("=" * 60)
    print("Enterprise AI SRE Platform v3.3 — Demo 数据导入")
    print("=" * 60)

    # 1. 登录
    print("\n[1/3] 认证...")
    token = _register_login()
    if not token:
        print("\n[FAIL] 无法获取认证 Token，请确保后端已启动")
        sys.exit(1)

    # 2. 加载文档
    print("\n[2/3] 加载 Demo 文档...")
    docs = _load_demo_docs()
    if not docs:
        print("[FAIL] demo/knowledge/ 目录下没有 .md 文件")
        sys.exit(1)
    print(f"  找到 {len(docs)} 个文档")

    # 3. 上传
    print("\n[3/3] 上传到知识库...")
    success = 0
    for title, content in docs:
        if _upload_doc(token, title, content):
            success += 1
        time.sleep(0.3)  # 避免过快请求

    # 4. 验证
    headers = {"Authorization": f"Bearer {token}"}
    resp = httpx.get(f"{BASE_URL}/api/knowledge", headers=headers, timeout=10)
    if resp.status_code == 200:
        data = resp.json()
        count = len(data) if isinstance(data, list) else 0
        print(f"\n[OK] 知识库中现有 {count} 个文档")

    print(f"\n{'=' * 60}")
    print(f"导入完成: {success}/{len(docs)} 成功")
    print("=" * 60)
    print("\n下一步: 在浏览器中打开 /ops 页面")
    print("输入: \"生产环境 payment-service 出现大量 502，请分析原因\"")
    print("观察 Agent 自动调用 K8s 工具 + 检索知识库 + 生成故障报告")


if __name__ == "__main__":
    main()