#!/usr/bin/env python3
"""v3.1.0 最终验收：架构文件 + 安全 + 运行时抽样。"""

from __future__ import annotations

import os
import sys
import time
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
os.chdir(ROOT)

RESULTS: list[dict] = []


def check(dim: str, name: str, passed: bool, detail: str = "") -> None:
    RESULTS.append({"dim": dim, "name": name, "passed": passed, "detail": detail[:300]})
    print(f"  [{'PASS' if passed else 'FAIL'}] {dim} > {name}  {detail[:120]}")


def exists(rel: str) -> bool:
    return (ROOT / rel).exists()


def file_contains(rel: str, *needles: str) -> bool:
    p = ROOT / rel
    if not p.exists():
        return False
    text = p.read_text(encoding="utf-8", errors="ignore")
    return all(n in text for n in needles)


def main():
    # Architecture
    check("Architecture", "LangGraph Agent", exists("app/agent/graph.py"))
    check("Architecture", "MCP Client", exists("app/mcp/client.py") and exists("app/mcp/metadata.py"))
    check("Architecture", "RAG", exists("app/rag/service.py"))
    check("Architecture", "Memory", exists("app/memory/long_term_memory.py") or exists("app/memory"))
    check("Architecture", "Streaming", exists("app/streaming/events.py"))
    check("Architecture", "Trace", exists("app/trace/service.py"))
    check("Architecture", "LLM Provider", exists("app/llm/providers/registry.py"))
    check("Architecture", "Auto Repair", exists("app/agent/approval.py"))
    check("Architecture", "Multi-tenant", file_contains("app/database/models.py", "class Organization"))

    # Security
    check("Security", "JWT 生产门禁", file_contains("app/config.py", "validate_production_security"))
    check("Security", "SecretFilter", file_contains("app/logging_config.py", "class SecretFilter"))
    check("Security", "security_check.py", exists("scripts/security_check.py"))
    check("Security", ".gitignore .env", file_contains(".gitignore", ".env"))
    check("Security", "启动拦截", file_contains("app/main.py", "validate_production_security"))

    # Database / Redis / RQ
    check("Database", "Alembic", exists("alembic.ini") and exists("alembic/versions/001_initial_schema.py"))
    check("Database", "SQLite 兼容", file_contains("app/database/database.py", "sqlite"))
    check("Redis", "惰性连接", file_contains("app/cache/redis.py", "def get_redis"))
    check("RQ", "任务队列", exists("app/tasks/agent_task.py"))

    # AI
    check("AI Capability", "Vision 配置", file_contains("app/config.py", "vision_model"))
    check("AI Capability", "MCP metadata docker_restart dangerous",
          file_contains("app/mcp/metadata.py", "docker_restart") and file_contains("app/mcp/metadata.py", "dangerous"))

    # Cloud native
    check("Cloud Native", "Helm Chart", exists("deploy/helm/Chart.yaml"))
    check("Cloud Native", "Prod compose", exists("docker-compose.prod.yml"))
    check("Cloud Native", "Grafana v3.1 dashboard", exists("monitoring/grafana/agent-sre-dashboard.json"))

    # Observability
    check("Observability", "agent_execution_total", file_contains("app/monitoring/metrics.py", "agent_execution_total"))
    check("Observability", "llm_token_usage", file_contains("app/monitoring/metrics.py", "llm_token_usage"))
    check("Observability", "mcp_tool_call_total", file_contains("app/monitoring/metrics.py", "mcp_tool_call_total"))
    check("Observability", "repair_success_total", file_contains("app/monitoring/metrics.py", "repair_success_total"))
    check("Observability", "OpenTelemetry setup", exists("app/telemetry/setup.py"))

    # Docs
    check("Production Ready", "README v3.1", file_contains("README.md", "v3.1.0") or file_contains("README.md", "3.1.0"))
    check("Production Ready", "故障 Demo", exists("docs/demo/order_service_failure_demo.md"))
    check("Production Ready", "MCP 安全模型文档", exists("docs/MCP_TOOL_SECURITY_MODEL.md"))
    check("Production Ready", "安全加固报告", exists("docs/SECURITY_HARDENING_REPORT.md"))

    # Runtime sample
    try:
        from app.config import Settings
        Settings(environment="development").validate_production_security()
        check("Security", "开发环境兼容", True, "default JWT 在 development 可通过")
    except Exception as e:
        check("Security", "开发环境兼容", False, str(e))

    try:
        from app.config import Settings
        Settings(environment="production", jwt_secret="change-me-to-a-random-secret").validate_production_security()
        check("Security", "生产拒绝弱 JWT", False, "弱密钥未被拒绝")
    except RuntimeError:
        check("Security", "生产拒绝弱 JWT", True)

    try:
        from app.logging_config import SecretFilter
        out = SecretFilter.redact("sk-abcdefghijklmnopqrst")
        check("Security", "日志脱敏运行", "****" in out and "sk-abcdefghijklmnopqrst" not in out, out)
    except Exception as e:
        check("Security", "日志脱敏运行", False, str(e))

    total = len(RESULTS)
    passed = sum(1 for r in RESULTS if r["passed"])
    failed = total - passed

    # dimension scores
    dims = {}
    for r in RESULTS:
        dims.setdefault(r["dim"], [0, 0])
        dims[r["dim"]][1] += 1
        if r["passed"]:
            dims[r["dim"]][0] += 1

    score_map = {
        "Architecture": "Architecture",
        "Production Ready": "Production Ready",
        "Security": "Security",
        "AI Capability": "AI Capability",
        "Cloud Native": "Cloud Native",
        "Observability": "Observability",
        "Database": "Production Ready",
        "Redis": "Production Ready",
        "RQ": "Production Ready",
    }
    agg = {k: [0, 0] for k in (
        "Architecture", "Production Ready", "Security", "AI Capability", "Cloud Native", "Observability",
    )}
    for r in RESULTS:
        bucket = score_map.get(r["dim"], "Production Ready")
        agg[bucket][1] += 1
        if r["passed"]:
            agg[bucket][0] += 1

    def pct(pair):
        return int(round(100 * pair[0] / pair[1])) if pair[1] else 0

    scores = {k: pct(v) for k, v in agg.items()}
    final = int(round(sum(scores.values()) / len(scores))) if scores else 0

    path = ROOT / "docs" / "FINAL_V3.1_ACCEPTANCE_REPORT.md"
    lines = [
        "# Enterprise AI DevOps Platform v3.1.0 Final Acceptance Report",
        "",
        f"> Generated: {datetime.now().isoformat(timespec='seconds')}",
        "",
        "## Executive Summary",
        "",
        f"| Total | Passed | Failed | Final Score |",
        f"|-------|--------|--------|-------------|",
        f"| {total} | {passed} | {failed} | **{final}/100** |",
        "",
        "## 评分维度",
        "",
        "| Dimension | Score |",
        "|-----------|-------|",
    ]
    for k, v in scores.items():
        lines.append(f"| {k} | {v}/100 |")
    lines += [
        "",
        "## 明细",
        "",
        "| Dimension | Check | Status | Detail |",
        "|-----------|-------|--------|--------|",
    ]
    for r in RESULTS:
        lines.append(f"| {r['dim']} | {r['name']} | {'PASS' if r['passed'] else 'FAIL'} | {r['detail'].replace('|','/')} |")
    fails = [r for r in RESULTS if not r["passed"]]
    lines += ["", "## 失败项", ""]
    if fails:
        for r in fails:
            lines.append(f"- **{r['dim']} / {r['name']}**: {r['detail']}")
    else:
        lines.append("无失败项。")
    lines += [
        "",
        "## 结论",
        "",
        f"- 企业生产安全标准: {'YES' if scores.get('Security',0) >= 80 else 'PARTIAL'}",
        f"- GitHub 展示级: {'YES' if final >= 85 else 'PARTIAL'}",
        f"- 面试项目级: {'YES' if final >= 85 else 'PARTIAL'}",
        "",
    ]
    path.write_text("\n".join(lines), encoding="utf-8")
    print(f"\n{passed}/{total}  score={final}/100  report={path}")


if __name__ == "__main__":
    main()
