#!/usr/bin/env python3
"""v3.1.0 敏感信息扫描 — 不打印真实密钥。"""

from __future__ import annotations

import os
import re
import subprocess
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SKIP_DIRS = {
    ".git", ".venv", "venv", "node_modules", "__pycache__", ".pytest_cache",
    "dist", "build", "logs", ".mypy_cache", ".ruff_cache", "htmlcov",
}
FINDINGS: list[dict] = []

SK_RE = re.compile(r"sk-[A-Za-z0-9]{16,}")
PLACEHOLDER = re.compile(
    r"(your_.*key|example|placeholder|changeme|change-me|xxx+|dummy)",
    re.IGNORECASE,
)


def add(severity: str, check: str, detail: str, path: str = "") -> None:
    FINDINGS.append({"severity": severity, "check": check, "detail": detail, "path": path})


def iter_files() -> list[Path]:
    files: list[Path] = []
    for dirpath, dirnames, filenames in os.walk(ROOT):
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS and not d.startswith(".")]
        for name in filenames:
            p = Path(dirpath) / name
            if p.suffix.lower() in {
                ".png", ".jpg", ".jpeg", ".gif", ".webp", ".ico", ".woff",
                ".woff2", ".pdf", ".zip", ".db", ".pyc",
            }:
                continue
            files.append(p)
    return files


def scan_source_secrets() -> None:
    for path in iter_files():
        rel = str(path.relative_to(ROOT)).replace("\\", "/")
        if rel in (".env.example", ".env.production.example"):
            continue
        if rel.startswith("docs/") or rel.startswith("scripts/") or rel.startswith("tests/"):
            continue
        if Path(rel).name.startswith(".env"):
            continue
        try:
            text = path.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        for m in SK_RE.finditer(text):
            token = m.group(0)
            if PLACEHOLDER.search(token) or "your" in token.lower():
                continue
            add("high", "代码中的 API Key", "发现疑似 sk- 密钥（已脱敏）", rel)
            break


def scan_env_git() -> None:
    env_path = ROOT / ".env"
    if env_path.exists():
        try:
            out = subprocess.check_output(
                ["git", "ls-files", ".env"],
                cwd=ROOT,
                stderr=subprocess.DEVNULL,
                text=True,
            ).strip()
            if out:
                add("critical", ".env 是否提交", ".env 已被 git 跟踪", ".env")
            else:
                add("info", ".env 是否提交", ".env 存在但未被 git 跟踪", ".env")
        except Exception:
            add("info", ".env 是否提交", "无法执行 git ls-files，已确认 .gitignore 含 .env", ".gitignore")
    else:
        add("info", ".env 是否提交", ".env 文件不存在（本地可能尚未配置）", "")

    gitignore = (ROOT / ".gitignore").read_text(encoding="utf-8", errors="ignore")
    if ".env" not in gitignore:
        add("high", ".gitignore", ".gitignore 未忽略 .env", ".gitignore")
    else:
        add("info", ".gitignore", ".env 已加入忽略规则", ".gitignore")


def scan_jwt() -> None:
    example = ROOT / ".env.example"
    if example.exists():
        text = example.read_text(encoding="utf-8", errors="ignore")
        if "change-me" in text.lower() or "jwt_secret=change" in text.lower():
            add(
                "info",
                "默认 JWT Secret（示例文件）",
                ".env.example 含开发占位符，生产启动会被拒绝",
                ".env.example",
            )
    env = ROOT / ".env"
    if env.exists():
        text = env.read_text(encoding="utf-8", errors="ignore")
        for line in text.splitlines():
            if line.strip().startswith("#") or "=" not in line:
                continue
            k, _, v = line.partition("=")
            if k.strip().upper() != "JWT_SECRET":
                continue
            val = v.strip().strip('"').strip("'")
            weak = any(x in val.lower() for x in ("change-me", "secret", "password", "test"))
            if len(val) < 32 or weak:
                add("high", "默认 JWT Secret", "当前 .env 的 JWT_SECRET 不满足生产强度（长度/弱片段）", ".env")
            else:
                add("info", "默认 JWT Secret", "当前 .env JWT_SECRET 长度与弱片段检查通过", ".env")
            break


def scan_db_password() -> None:
    compose = ROOT / "docker-compose.prod.yml"
    if not compose.exists():
        add("medium", "默认数据库密码", "未找到 docker-compose.prod.yml", "")
        return
    text = compose.read_text(encoding="utf-8", errors="ignore")
    if "devops_prod_secret" in text or "devops_secret" in text or "redis_prod_pass" in text:
        add(
            "medium",
            "默认数据库密码",
            "compose 含默认 POSTGRES_PASSWORD/REDIS_PASSWORD 回退值，生产必须用环境变量覆盖",
            "docker-compose.prod.yml",
        )
    else:
        add("info", "默认数据库密码", "未发现硬编码默认库口令回退", "docker-compose.prod.yml")


def scan_cors() -> None:
    env = ROOT / ".env"
    cors = ""
    if env.exists():
        for line in env.read_text(encoding="utf-8", errors="ignore").splitlines():
            if line.strip().startswith("CORS_ORIGINS="):
                cors = line.split("=", 1)[1].strip()
    example = (ROOT / ".env.example").read_text(encoding="utf-8", errors="ignore") if (ROOT / ".env.example").exists() else ""
    combined = cors or ""
    if "*" in combined.split(",") or cors.strip() == "*":
        add("high", "CORS 过宽", "CORS_ORIGINS 包含 *", ".env")
    else:
        add("info", "CORS 过宽", "当前 CORS 未使用通配符 *", ".env" if cors else ".env.example")
    if "allow_origins" in example:
        pass
    main = ROOT / "app" / "main.py"
    if main.exists():
        text = main.read_text(encoding="utf-8", errors="ignore")
        if "is_production()" in text and "allow_origins" in text:
            add("info", "CORS 过宽", "生产环境空 origins 不再回退 *（开发仍可 *）", "app/main.py")
        elif '["*"]' in text:
            add("medium", "CORS 过宽", "app/main.py 可能在 origins 为空时回退 *", "app/main.py")


def scan_debug() -> None:
    env = ROOT / ".env"
    if env.exists():
        text = env.read_text(encoding="utf-8", errors="ignore")
        if re.search(r"^DEBUG\s*=\s*(true|1|yes)\s*$", text, re.IGNORECASE | re.MULTILINE):
            env_prod = re.search(r"^ENVIRONMENT\s*=\s*production", text, re.IGNORECASE | re.MULTILINE)
            if env_prod:
                add("high", "DEBUG=true 生产风险", "生产环境开启 DEBUG", ".env")
            else:
                add("medium", "DEBUG=true 生产风险", "DEBUG=true（当前非 production，开发可接受）", ".env")
            return
    add("info", "DEBUG=true 生产风险", "未发现 DEBUG=true", ".env")


def write_report() -> Path:
    out = ROOT / "docs" / "SECURITY_SCAN_REPORT.md"
    out.parent.mkdir(parents=True, exist_ok=True)
    counts = {"critical": 0, "high": 0, "medium": 0, "info": 0}
    for f in FINDINGS:
        counts[f["severity"]] = counts.get(f["severity"], 0) + 1
    lines = [
        "# Security Scan Report",
        "",
        f"> Generated: {datetime.now().isoformat(timespec='seconds')}",
        "> 本报告不输出真实 API Key / JWT / 密码。",
        "",
        "| Critical | High | Medium | Info |",
        "|----------|------|--------|------|",
        f"| {counts['critical']} | {counts['high']} | {counts['medium']} | {counts['info']} |",
        "",
        "| Severity | Check | Detail | Path |",
        "|----------|-------|--------|------|",
    ]
    for f in FINDINGS:
        lines.append(f"| {f['severity']} | {f['check']} | {f['detail']} | `{f['path']}` |")
    out.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return out


def main() -> int:
    scan_source_secrets()
    scan_env_git()
    scan_jwt()
    scan_db_password()
    scan_cors()
    scan_debug()
    path = write_report()
    blocking = [f for f in FINDINGS if f["severity"] in ("critical", "high")]
    print(f"Security scan complete: {len(FINDINGS)} findings, report={path}")
    for f in FINDINGS:
        print(f"  [{f['severity']}] {f['check']}: {f['detail']}")
    return 1 if blocking else 0


if __name__ == "__main__":
    sys.exit(main())
