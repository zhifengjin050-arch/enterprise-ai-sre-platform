"""MCP Client 配置（从 Settings / 环境变量读取）。"""

from __future__ import annotations

from dataclasses import dataclass

from app.config import settings


@dataclass(frozen=True)
class MCPConfig:
    enabled: bool
    command: str
    args: list[str]
    cwd: str
    timeout: float


def get_mcp_config() -> MCPConfig:
    """解析 MCP 相关配置。"""
    raw_args = (settings.mcp_server_args or "").strip()
    if not raw_args:
        args: list[str] = []
    elif "," in raw_args:
        args = [a.strip() for a in raw_args.split(",") if a.strip()]
    else:
        # 空格分隔亦可
        args = raw_args.split()

    return MCPConfig(
        enabled=bool(settings.enable_mcp),
        command=settings.mcp_server_command or "python",
        args=args,
        cwd=(settings.mcp_server_cwd or "").strip(),
        timeout=float(settings.mcp_timeout or 30),
    )
