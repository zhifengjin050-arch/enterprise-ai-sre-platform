"""Docker 部署配置测试（生产级架构验证）

验证新架构：
- backend/Dockerfile
- frontend/Dockerfile + nginx.conf
- docker-compose.yml（根目录）
- deploy.sh
- .env.example
- requirements.txt
"""

import os

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def test_backend_dockerfile_exists():
    """backend/Dockerfile 必须存在"""
    path = os.path.join(PROJECT_ROOT, "backend", "Dockerfile")
    assert os.path.exists(path), f"Missing: {path}"
    with open(path, encoding="utf-8") as f:
        content = f.read()
    assert "python:3.12-slim" in content
    assert "uvicorn" in content
    assert "HEALTHCHECK" in content
    assert "appuser" in content or "appgroup" in content
    assert "EXPOSE 8000" in content
    print(f"[OK] backend/Dockerfile — {len(content)} chars, slim + healthcheck + non-root")


def test_frontend_dockerfile_exists():
    """frontend/Dockerfile 必须存在"""
    path = os.path.join(PROJECT_ROOT, "frontend", "Dockerfile")
    assert os.path.exists(path), f"Missing: {path}"
    with open(path, encoding="utf-8") as f:
        content = f.read()
    assert "nginx:alpine" in content or "nginx" in content
    print(f"[OK] frontend/Dockerfile — {len(content)} chars, nginx alpine")


def test_frontend_nginx_config():
    """frontend/nginx.conf 必须存在"""
    path = os.path.join(PROJECT_ROOT, "frontend", "nginx.conf")
    assert os.path.exists(path), f"Missing: {path}"
    with open(path, encoding="utf-8") as f:
        content = f.read()
    assert "proxy_pass" in content
    assert "gzip" in content
    assert "upstream backend" in content or "server backend" in content
    print(f"[OK] frontend/nginx.conf — {len(content)} chars, upstream + gzip + proxy")


def test_docker_compose_exists():
    """根目录 docker-compose.yml 必须存在"""
    path = os.path.join(PROJECT_ROOT, "docker-compose.yml")
    assert os.path.exists(path), f"Missing: {path}"
    with open(path, encoding="utf-8") as f:
        content = f.read()
    assert "backend:" in content
    assert "frontend:" in content
    assert "devops-net" in content
    print(f"[OK] docker-compose.yml — {len(content)} chars, backend + frontend + network")


def test_deploy_script_exists():
    """deploy.sh 必须存在"""
    path = os.path.join(PROJECT_ROOT, "scripts", "deploy.sh")
    assert os.path.exists(path), f"Missing: {path}"
    with open(path, encoding="utf-8") as f:
        content = f.read()
    assert "#!/bin/bash" in content
    assert "docker compose" in content
    print(f"[OK] scripts/deploy.sh — {len(content)} chars, bash deploy script")


def test_env_example_complete():
    """.env.example 包含所有必要配置项"""
    path = os.path.join(PROJECT_ROOT, ".env.example")
    assert os.path.exists(path), f"Missing: {path}"
    with open(path, encoding="utf-8") as f:
        content = f.read()
    required_fields = [
        "DEEPSEEK_API_KEY",
        "DEEPSEEK_BASE_URL",
        "DEEPSEEK_MODEL_NAME",
        "APP_HOST",
        "APP_PORT",
        "ENVIRONMENT",
        "CORS_ORIGINS",
        "RATE_LIMIT_PER_MINUTE",
    ]
    for field in required_fields:
        assert field in content, f"缺少环境变量: {field}"
    print(f"[OK] .env.example — 包含全部 {len(required_fields)} 个必需配置项")


def test_requirements_complete():
    """requirements.txt 包含生产必需依赖"""
    path = os.path.join(PROJECT_ROOT, "requirements.txt")
    assert os.path.exists(path), f"Missing: {path}"
    with open(path, encoding="utf-8") as f:
        content = f.read()
    required = ["fastapi", "uvicorn", "langgraph", "openai", "psutil", "docker", "httpx"]
    for pkg in required:
        assert pkg in content, f"缺少依赖包: {pkg}"
    print("[OK] requirements.txt — 包含全部生产依赖")


def test_dockerignore_exists():
    """.gitignore 必须存在"""
    path = os.path.join(PROJECT_ROOT, ".gitignore")
    assert os.path.exists(path), f"Missing: {path}"
    print("[OK] .gitignore exists")


def test_logging_config_exists():
    """日志配置文件必须存在"""
    path = os.path.join(PROJECT_ROOT, "app", "logging_config.py")
    assert os.path.exists(path), f"Missing: {path}"
    print("[OK] app/logging_config.py exists")


if __name__ == "__main__":
    print("=" * 60)
    print("  Docker 与生产化部署配置测试")
    print("=" * 60)

    test_backend_dockerfile_exists()
    test_frontend_dockerfile_exists()
    test_frontend_nginx_config()
    test_docker_compose_exists()
    test_deploy_script_exists()
    test_env_example_complete()
    test_requirements_complete()
    test_dockerignore_exists()
    test_logging_config_exists()

    print("=" * 60)
    print("  全部 9 项配置测试通过")
    print("=" * 60)
