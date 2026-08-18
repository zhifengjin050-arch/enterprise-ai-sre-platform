#!/usr/bin/env python3
"""v3.2.1 Production Hardening acceptance — real HTTP + Settings probes."""
from __future__ import annotations

import json
import os
import socket
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
os.chdir(ROOT)

BASE = os.environ.get("TEST_BASE_URL", "http://127.0.0.1:8000")
RESULTS: list[tuple[str, bool, str]] = []


def rec(name: str, ok: bool, detail: str = "") -> None:
    RESULTS.append((name, ok, detail[:240]))
    mark = "PASS" if ok else "FAIL"
    print(f"  [{mark}] {name}  {detail[:160]}")


def port_open(port: int = 8000) -> bool:
    try:
        with socket.create_connection(("127.0.0.1", port), timeout=1.5):
            return True
    except OSError:
        return False


def http(method: str, path: str, data=None, token: str = "", timeout: int = 20):
    req = urllib.request.Request(f"{BASE}{path}", method=method)
    if token:
        req.add_header("Authorization", f"Bearer {token}")
    body = None
    if data is not None:
        body = json.dumps(data).encode("utf-8")
        req.add_header("Content-Type", "application/json")
    try:
        with urllib.request.urlopen(req, data=body, timeout=timeout) as resp:
            raw = resp.read().decode("utf-8", errors="replace")
            parsed = json.loads(raw) if raw else {}
            return resp.status, parsed
    except urllib.error.HTTPError as e:
        raw = e.read().decode("utf-8", errors="replace")
        try:
            parsed = json.loads(raw) if raw else {}
        except json.JSONDecodeError:
            parsed = {"detail": raw[:200]}
        return e.code, parsed
    except Exception as e:
        return 0, {"detail": f"{type(e).__name__}: {e}"}


def main() -> int:
    print("v3.2.1 hardening acceptance")
    rec("Backend listening :8000", port_open(8000), "uvicorn")

    from app.config import APP_VERSION, JWT_INSECURE_PRODUCTION_MSG, Settings

    rec("APP_VERSION", APP_VERSION in ("3.2.1", "3.3.0"), APP_VERSION)

    weak = Settings(environment="production", jwt_secret="change-me-to-a-random-secret")
    try:
        weak.validate_production_security()
        rec("JWT production weak secret rejected", False, "did not raise")
    except RuntimeError as e:
        rec("JWT production weak secret rejected", JWT_INSECURE_PRODUCTION_MSG in str(e), str(e))

    strong = Settings(environment="production", jwt_secret="xk9mP2qR7wL4nV8bY3cH6jF1aD5tG0uZ")
    try:
        strong.validate_production_security()
        rec("JWT production strong secret accepted", True)
    except Exception as e:
        rec("JWT production strong secret accepted", False, str(e))

    dev = Settings(environment="development", jwt_secret="change-me-to-a-random-secret")
    try:
        dev.validate_production_security()
        rec("JWT development default allowed", True)
    except Exception as e:
        rec("JWT development default allowed", False, str(e))

    st, health = http("GET", "/health")
    rec(
        "GET /health",
        st == 200 and health.get("version") == "3.2.1",
        f"status={st} version={health.get('version')}",
    )

    st, me = http("GET", "/api/auth/me")
    rec("Auth unauthenticated 401", st == 401, f"status={st}")

    st, login = http("POST", "/api/auth/login", {"username": "webtest", "password": "webtest123"})
    token = login.get("access_token") or ""
    rec("Auth login webtest", st == 200 and bool(token), f"status={st}")

    st, me = http("GET", "/api/auth/me", token=token)
    rec("GET /api/auth/me", st == 200 and me.get("username") == "webtest", f"status={st} user={me.get('username')}")

    st, status = http("GET", "/api/system/status")
    rec("GET /api/system/status without JWT", st == 401, f"status={st}")

    st, status = http("GET", "/api/system/status", token=token)
    blob = json.dumps(status, ensure_ascii=False).lower()
    forbidden = any(x in blob for x in ("sk-", "sqlite:///", "postgresql://", "redis://", "jwt_secret", "mcp_server_cwd"))
    keys_ok = set(status.keys()) == {
        "version", "environment", "database", "llm_provider",
        "mcp_enabled", "mcp_tools", "redis_connected", "otel_enabled",
    } if isinstance(status, dict) else False
    rec(
        "GET /api/system/status",
        st == 200 and status.get("version") == "3.2.1" and keys_ok and not forbidden,
        f"status={st} keys={list(status.keys()) if isinstance(status, dict) else status}",
    )

    mcp_ok = isinstance(status, dict) and isinstance(status.get("mcp_enabled"), bool) and isinstance(status.get("mcp_tools"), int)
    rec(
        "MCP status fields",
        mcp_ok,
        f"enabled={status.get('mcp_enabled')} tools={status.get('mcp_tools')}" if isinstance(status, dict) else "",
    )

    passed = sum(1 for _, ok, _ in RESULTS if ok)
    failed = len(RESULTS) - passed
    print()
    print("================================")
    print("Enterprise AI SRE Platform v3.2.1")
    print("Production Hardening Result")
    print(f"PASS: {passed}")
    print(f"FAIL: {failed}")
    print("================================")
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
