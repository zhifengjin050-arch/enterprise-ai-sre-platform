"""MCP stdio Client — 连接 / 发现工具 / 调用工具。

基于官方 mcp SDK：StdioServerParameters + ClientSession。
同步 API 通过 MCPManager 的事件循环桥接。
"""

from __future__ import annotations

import json
import logging
import os
from typing import Any

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

from app.mcp.config import MCPConfig

logger = logging.getLogger("mcp.client")


class MCPClient:
    """持有一个长期 stdio MCP 会话。"""

    def __init__(self, config: MCPConfig):
        self.config = config
        self._session: ClientSession | None = None
        self._cm = None  # stdio_client context
        self._session_cm = None
        self._tools_cache: list[Any] = []
        self.connected = False

    async def connect(self) -> None:
        if self.connected:
            return

        if not self.config.cwd:
            raise ValueError("MCP_SERVER_CWD 未配置，无法启动 MCP Server 子进程")

        env = {**os.environ, "FASTMCP_SHOW_SERVER_BANNER": "false"}
        params = StdioServerParameters(
            command=self.config.command,
            args=self.config.args,
            cwd=self.config.cwd,
            env=env,
        )
        logger.info(
            "启动 MCP Server: %s %s (cwd=%s)",
            self.config.command,
            " ".join(self.config.args),
            self.config.cwd,
        )

        self._cm = stdio_client(params)
        read, write = await self._cm.__aenter__()
        self._session_cm = ClientSession(read, write)
        self._session = await self._session_cm.__aenter__()
        await self._session.initialize()
        await self.refresh_tools()
        self.connected = True
        logger.info("MCP 已连接，发现 %d 个工具", len(self._tools_cache))

    async def close(self) -> None:
        self.connected = False
        self._tools_cache = []
        try:
            if self._session_cm is not None:
                await self._session_cm.__aexit__(None, None, None)
        except Exception as e:
            logger.warning("关闭 MCP session 异常: %s", e)
        finally:
            self._session = None
            self._session_cm = None

        try:
            if self._cm is not None:
                await self._cm.__aexit__(None, None, None)
        except Exception as e:
            logger.warning("关闭 MCP stdio 异常: %s", e)
        finally:
            self._cm = None

    async def refresh_tools(self) -> list[Any]:
        if self._session is None:
            return []
        result = await self._session.list_tools()
        self._tools_cache = list(result.tools or [])
        return self._tools_cache

    def list_tools_sync_cache(self) -> list[Any]:
        return list(self._tools_cache)

    async def call_tool(self, name: str, arguments: dict[str, Any] | None = None) -> Any:
        if self._session is None or not self.connected:
            raise RuntimeError("MCP Client 未连接")
        arguments = arguments or {}
        result = await self._session.call_tool(name, arguments)
        return _normalize_tool_result(result)


def _normalize_tool_result(result: Any) -> Any:
    """将 MCP CallToolResult 转为 Agent 可读的 dict/str。"""
    if result is None:
        return ""

    # isError
    is_error = bool(getattr(result, "isError", False))

    contents = getattr(result, "content", None) or []
    texts: list[str] = []
    for item in contents:
        text = getattr(item, "text", None)
        if text is not None:
            texts.append(text)
        else:
            texts.append(str(item))

    if not texts:
        structured = getattr(result, "structuredContent", None)
        if structured is not None:
            return structured if not is_error else {"error": True, "data": structured}
        return {"error": True, "message": "empty MCP result"} if is_error else ""

    joined = "\n".join(texts)
    # 尝试 JSON 解析
    try:
        parsed = json.loads(joined)
        if is_error and isinstance(parsed, dict):
            parsed.setdefault("error", True)
        return parsed
    except (json.JSONDecodeError, TypeError):
        if is_error:
            return {"error": True, "message": joined}
        return joined
