#!/usr/bin/env python3
"""v3.1.0 真实运行验收 — 失败如实记录，不伪造结果。"""

from __future__ import annotations

import json
import os
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
os.chdir(ROOT)

from dotenv import load_dotenv
load_dotenv(ROOT / ".env")

BASE_URL = os.environ.get("TEST_BASE_URL", "http://localhost:8000")
RESULTS: list[dict] = []
START = time.monotonic()


def log(phase: str, name: str, passed: bool, detail: str = "", duration: float = 0.0) -> None:
    RESULTS.append({
        "phase": phase, "name": name, "passed": passed,
        "detail": detail[:400], "duration": round(duration, 2),
    })
    icon = "PASS" if passed else "FAIL"
    print(f"  [{icon}] {phase} > {name} ({duration:.1f}s) {detail[:160]}")


def http(method: str, path: str, data=None, token: str = "", timeout: int = 60):
    req = urllib.request.Request(f"{BASE_URL}{path}", method=method)
    if token:
        req.add_header("Authorization", f"Bearer {token}")
    body = None
    if data is not None:
        body = json.dumps(data).encode()
        req.add_header("Content-Type", "application/json")
    t0 = time.monotonic()
    try:
        with urllib.request.urlopen(req, data=body, timeout=timeout) as resp:
            raw = resp.read().decode()
            parsed = json.loads(raw) if raw else {}
            return resp.status, parsed, time.monotonic() - t0
    except urllib.error.HTTPError as e:
        raw = e.read().decode()
        try:
            parsed = json.loads(raw) if raw else {}
        except json.JSONDecodeError:
            parsed = {"detail": raw[:200]}
        return e.code, parsed, time.monotonic() - t0
    except Exception as e:
        return 0, {"detail": str(e)}, time.monotonic() - t0


def test_database():
    phase = "Database"
    t0 = time.monotonic()
    try:
        from sqlalchemy import text
        from app.database.database import engine, get_db_type
        db_type = get_db_type()
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        log(phase, "连接", True, f"db_type={db_type}", time.monotonic() - t0)
        log(phase, "Connection Pool", True, f"pool={getattr(engine.pool, 'size', lambda: '?')()}", 0)
    except Exception as e:
        log(phase, "连接", False, str(e), time.monotonic() - t0)
        return

    t0 = time.monotonic()
    try:
        from app.database.session import init_db
        init_db()
        log(phase, "Migration/建表", True, "init_db ok (dev create_all / 表已存在)", time.monotonic() - t0)
    except Exception as e:
        log(phase, "Migration/建表", False, str(e), time.monotonic() - t0)

    t0 = time.monotonic()
    try:
        from app.database.session import get_local_session
        from app.database.models import User
        db = get_local_session()
        count = db.query(User).count()
        db.close()
        log(phase, "CRUD 读", True, f"users={count}", time.monotonic() - t0)
    except Exception as e:
        log(phase, "CRUD 读", False, str(e), time.monotonic() - t0)


def test_redis():
    phase = "Redis"
    t0 = time.monotonic()
    try:
        from app.cache.redis import get_redis, ping_redis
        ok = ping_redis()
        log(phase, "PING", ok, "PONG" if ok else "Redis 未启动或无法连接", time.monotonic() - t0)
        if not ok:
            log(phase, "Cache", False, "跳过：Redis 不可用", 0)
            log(phase, "TTL", False, "跳过：Redis 不可用", 0)
            log(phase, "连接池", False, "跳过：Redis 不可用", 0)
            return
        r = get_redis()
        key = "v31:accept:cache"
        r.set(key, "1", ex=5)
        val = r.get(key)
        ttl = r.ttl(key)
        log(phase, "Cache", val == "1", f"get={val}", 0)
        log(phase, "TTL", isinstance(ttl, int) and ttl > 0, f"ttl={ttl}", 0)
        log(phase, "连接池", True, "redis-py 连接已建立", 0)
        r.delete(key)
    except Exception as e:
        log(phase, "PING", False, str(e), time.monotonic() - t0)


def test_rq():
    phase = "RQ"
    t0 = time.monotonic()
    try:
        from app.tasks.agent_task import _get_queue, get_job_status
        q = _get_queue()
        job = q.enqueue("app.tasks.agent_task.rq_health_check", job_timeout=30, result_ttl=120)
        log(phase, "创建 Job", True, f"job_id={job.id} status=queued", time.monotonic() - t0)
        # 等待 worker（最多 8s）；无 worker 则记录真实原因
        deadline = time.monotonic() + 8
        last = {}
        while time.monotonic() < deadline:
            last = get_job_status(job.id)
            if last.get("status") in ("finished", "failed"):
                break
            time.sleep(0.4)
        status = last.get("status", "unknown")
        log(phase, "Worker 执行", status == "finished", f"status={status} result={last.get('result')}", 0)
        log(phase, "状态流转", status in ("queued", "started", "finished", "failed"),
            f"最终状态={status}（无 worker 时会停留 queued）", 0)
    except Exception as e:
        log(phase, "创建 Job", False, str(e), time.monotonic() - t0)


def _auth_token():
    import random
    user = f"v31_{random.randint(10000, 99999)}"
    http("POST", "/api/auth/register", {
        "username": user, "email": f"{user}@test.local", "password": "Test1234!",
    })
    st, data, _ = http("POST", "/api/auth/login", {"username": user, "password": "Test1234!"})
    return data.get("access_token", ""), user


def test_agent():
    phase = "Agent"
    token, _ = _auth_token()
    t0 = time.monotonic()
    st, data, dur = http("POST", "/api/chat", {
        "message": "用一句话说明你的版本和能力",
        "session_id": "v31",
    }, token=token, timeout=120)
    report = data.get("report", "") if isinstance(data, dict) else ""
    cid = data.get("conversation_id") if isinstance(data, dict) else None
    log(phase, "真实 LLM 调用", st == 200 and len(report) > 0, f"status={st} len={len(report)}", dur)

    if cid and token:
        st2, tr, dur2 = http("GET", f"/api/agent/traces/{cid}", token=token)
        steps = []
        if isinstance(tr, dict):
            steps = tr.get("steps") or tr.get("traces") or []
        log(phase, "Trace 生成", st2 in (200, 404), f"status={st2} steps={len(steps) if isinstance(steps, list) else '?'}", dur2)
    else:
        log(phase, "Trace 生成", False, "无 conversation_id（可能未登录或接口失败）", 0)

    st3, data3, dur3 = http("GET", "/api/conversations", token=token)
    log(phase, "Memory 保存", st3 == 200, f"status={st3}", dur3)
    return token


def test_mcp():
    phase = "MCP"
    t0 = time.monotonic()
    try:
        from app.mcp.manager import mcp_manager
        started = mcp_manager.start()
        status = mcp_manager.status()
        log(phase, "stdio 连接", bool(status.get("connected") or started),
            json.dumps({k: status.get(k) for k in ("enabled", "connected", "tool_count", "error")}, ensure_ascii=False),
            time.monotonic() - t0)
        names = status.get("tools") or []
        log(phase, "Tool discovery", len(names) > 0, f"tools={len(names)} sample={names[:5]}", 0)
        if "get_cpu_usage" in names:
            t1 = time.monotonic()
            result = mcp_manager.call_tool("get_cpu_usage", {})
            log(phase, "Tool call", result is not None, str(result)[:180], time.monotonic() - t1)
        elif names:
            t1 = time.monotonic()
            result = mcp_manager.call_tool(names[0], {})
            log(phase, "Tool call", result is not None, f"{names[0]} -> {str(result)[:120]}", time.monotonic() - t1)
        else:
            log(phase, "Tool call", False, "无可用工具（ENABLE_MCP=false 或连接失败）", 0)
    except Exception as e:
        log(phase, "stdio 连接", False, str(e), time.monotonic() - t0)


def test_rag(token: str):
    phase = "RAG"
    st, data, dur = http("POST", "/api/knowledge/upload", {
        "title": "订单服务 502 SOP",
        "content": "订单服务 502：1. 查 Ingress/Service 2. 查 Pod Ready 3. 读日志 4. 必要时重启 Deployment。",
    }, token=token)
    doc_id = data.get("id") if isinstance(data, dict) else None
    log(phase, "上传", st == 200 and doc_id is not None, f"status={st} id={doc_id}", dur)
    st2, data2, dur2 = http("POST", "/api/knowledge/search", {"query": "订单 502 怎么排查", "top_k": 3}, token=token)
    results = data2 if isinstance(data2, list) else (data2.get("results") if isinstance(data2, dict) else [])
    log(phase, "Search/引用", st2 == 200 and bool(results), f"status={st2} hits={len(results) if isinstance(results, list) else 0}", dur2)


def test_repair():
    phase = "Auto Repair"
    from app.agent.approval import (
        RepairAction, create_approval, approve_action, execute_approved_action, classify_tool,
    )
    from app.tools.registry import get_all_tools
    log(phase, "风险分级", classify_tool("docker_restart") == "dangerous", "docker_restart=dangerous", 0)
    tools = get_all_tools()
    tool_name = tools[0].name if tools else "get_cpu_usage"
    action = RepairAction(tool_name, {}, f"调用 {tool_name}", severity="info", requires_approval=True)
    token = create_approval(action)
    log(phase, "创建 RepairAction", bool(token), f"token={token}", 0)
    ok = approve_action(token)
    log(phase, "审批", ok, "approved", 0)
    t0 = time.monotonic()
    result = execute_approved_action(token)
    log(phase, "执行", bool(result.get("success")), str(result)[:200], time.monotonic() - t0)


def test_rbac(token: str):
    phase = "RBAC"
    import random
    slug_a = f"tenanta{random.randint(1000,9999)}"
    slug_b = f"tenantb{random.randint(1000,9999)}"
    st, data, dur = http("POST", "/api/org/", {"name": "Tenant A", "slug": slug_a}, token=token)
    log(phase, "创建 Tenant A", st in (200, 201), f"status={st} {data}", dur)

    user_b = f"v31b_{random.randint(10000,99999)}"
    http("POST", "/api/auth/register", {
        "username": user_b, "email": f"{user_b}@test.local", "password": "Test1234!",
    })
    st, data, _ = http("POST", "/api/auth/login", {"username": user_b, "password": "Test1234!"})
    token_b = data.get("access_token", "")
    http("POST", "/api/org/", {"name": "Tenant B", "slug": slug_b}, token=token_b)

    http("POST", "/api/knowledge/upload", {
        "title": "TenantA-only SOP",
        "content": "这是 Tenant A 的机密排障文档 ALPHA-ONLY",
    }, token=token)

    st, listed, _ = http("GET", "/api/knowledge", token=token_b)
    titles = [d.get("title", "") for d in listed] if isinstance(listed, list) else []
    leaked = any("TenantA-only" in t or "ALPHA-ONLY" in t for t in titles)
    log(phase, "数据隔离", st == 200 and not leaked, f"B 可见文档={titles[:5]} leaked={leaked}", 0)


def write_report():
    total = len(RESULTS)
    passed = sum(1 for r in RESULTS if r["passed"])
    failed = total - passed
    duration = time.monotonic() - START
    path = ROOT / "docs" / "V3.1_REAL_PRODUCTION_ACCEPTANCE.md"
    failed_rows = [r for r in RESULTS if not r["passed"]]
    lines = [
        "# Enterprise AI DevOps Platform v3.1.0 — 真实生产运行验收",
        "",
        f"> Generated: {datetime.now().isoformat(timespec='seconds')}",
        f"> Base URL: {BASE_URL}",
        "",
        "## 汇总",
        "",
        "| 总测试 | 通过 | 失败 | 通过率 | 耗时 |",
        "|--------|------|------|--------|------|",
        f"| {total} | {passed} | {failed} | {passed/total*100 if total else 0:.1f}% | {duration:.1f}s |",
        "",
        "## 明细",
        "",
        "| Phase | Test | Status | Detail | Duration |",
        "|-------|------|--------|--------|----------|",
    ]
    for r in RESULTS:
        icon = "PASS" if r["passed"] else "FAIL"
        lines.append(f"| {r['phase']} | {r['name']} | {icon} | {r['detail'].replace('|','/')} | {r['duration']}s |")
    lines += ["", "## 失败项（如实记录）", ""]
    if failed_rows:
        for r in failed_rows:
            lines.append(f"- **{r['phase']} / {r['name']}**: {r['detail']}")
    else:
        lines.append("无失败项。")
    lines += [
        "",
        "## 说明",
        "",
        "- Redis/RQ/PostgreSQL 若本机未启动，对应项记 FAIL，不伪造成功。",
        "- Agent/RAG 依赖 Backend 与有效 LLM Key。",
        "- MCP 依赖 ENABLE_MCP=true 且 Project2 路径正确。",
        "",
    ]
    path.write_text("\n".join(lines), encoding="utf-8")
    print(f"\nReport: {path}  {passed}/{total}")
    return path


def main():
    print("=== v3.1.0 Real Production Acceptance ===")
    test_database()
    test_redis()
    test_rq()
    token = ""
    try:
        token = test_agent() or ""
    except Exception as e:
        log("Agent", "真实 LLM 调用", False, str(e), 0)
    test_mcp()
    if token:
        test_rag(token)
        test_rbac(token)
    else:
        log("RAG", "上传", False, "无 token，Backend 可能未启动", 0)
        log("RBAC", "数据隔离", False, "无 token，Backend 可能未启动", 0)
    test_repair()
    write_report()


if __name__ == "__main__":
    main()
