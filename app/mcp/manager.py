"""MCP Server 生命周期管理 — 后台事件循环 + 同步桥接。"""

from __future__ import annotations

import asyncio
import logging
import threading
from typing import Any

from app.mcp.client import MCPClient
from app.mcp.config import MCPConfig, get_mcp_config
from app.mcp.tools import MCPToolWrapper, wrap_mcp_tools

logger = logging.getLogger("mcp.manager")


class MCPManager:
    """单例管理器：启动/停止 MCP Client，提供同步 call_tool。"""

    def __init__(self) -> None:
        self._config: MCPConfig | None = None
        self._client: MCPClient | None = None
        self._loop: asyncio.AbstractEventLoop | None = None
        self._thread: threading.Thread | None = None
        self._wrappers: dict[str, MCPToolWrapper] = {}
        self._lock = threading.Lock()
        self._started = False
        self._start_error: str | None = None

    @property
    def enabled(self) -> bool:
        cfg = self._config or get_mcp_config()
        return cfg.enabled

    @property
    def connected(self) -> bool:
        return bool(self._client and self._client.connected)

    @property
    def start_error(self) -> str | None:
        return self._start_error

    def start(self, config: MCPConfig | None = None) -> bool:
        """启动 MCP（同步）。失败时降级，不抛出。"""
        with self._lock:
            if self._started:
                return self.connected

            self._config = config or get_mcp_config()
            if not self._config.enabled:
                logger.info("ENABLE_MCP=false，跳过 MCP 连接")
                # #region agent log
                try:
                    import json as _json, time as _time
                    from pathlib import Path as _P
                    with open(_P(__file__).resolve().parents[2] / "debug-c5f825.log", "a", encoding="utf-8") as _f:
                        _f.write(_json.dumps({"sessionId":"c5f825","runId":"v32-debug","hypothesisId":"H1","location":"app/mcp/manager.py:start","message":"MCP skipped disabled","data":{"enabled":False},"timestamp":int(_time.time()*1000)}, ensure_ascii=False)+"\n")
                except Exception:
                    pass
                # #endregion
                return False

            try:
                self._loop = asyncio.new_event_loop()
                self._thread = threading.Thread(
                    target=self._run_loop,
                    name="mcp-client-loop",
                    daemon=True,
                )
                self._thread.start()

                self._client = MCPClient(self._config)
                fut = asyncio.run_coroutine_threadsafe(
                    self._client.connect(),
                    self._loop,
                )
                fut.result(timeout=self._config.timeout)
                self._wrappers = {
                    w.name: w
                    for w in wrap_mcp_tools(
                        self._client.list_tools_sync_cache(),
                        call_fn=self.call_tool,
                    )
                }
                self._started = True
                self._start_error = None
                logger.info("MCP Manager 启动成功，工具数=%d", len(self._wrappers))
                # #region agent log
                try:
                    import json as _json, time as _time
                    from pathlib import Path as _P
                    with open(_P(__file__).resolve().parents[2] / "debug-c5f825.log", "a", encoding="utf-8") as _f:
                        _f.write(_json.dumps({"sessionId":"c5f825","runId":"v32-debug","hypothesisId":"H1","location":"app/mcp/manager.py:start","message":"MCP start ok","data":{"enabled":True,"tool_count":len(self._wrappers),"tools":list(self._wrappers.keys())[:20]},"timestamp":int(_time.time()*1000)}, ensure_ascii=False)+"\n")
                except Exception:
                    pass
                # #endregion
                return True
            except Exception as e:
                self._start_error = str(e)
                logger.error("MCP Manager 启动失败，降级到内置工具: %s", e)
                self._safe_stop_unlocked()
                return False

    def stop(self) -> None:
        with self._lock:
            self._safe_stop_unlocked()

    def _safe_stop_unlocked(self) -> None:
        if self._client and self._loop:
            try:
                fut = asyncio.run_coroutine_threadsafe(self._client.close(), self._loop)
                fut.result(timeout=10)
            except Exception as e:
                logger.warning("MCP close 异常: %s", e)

        if self._loop is not None:
            try:
                self._loop.call_soon_threadsafe(self._loop.stop)
            except Exception:
                pass

        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=5)

        self._client = None
        self._wrappers = {}
        self._loop = None
        self._thread = None
        self._started = False

    def _run_loop(self) -> None:
        assert self._loop is not None
        asyncio.set_event_loop(self._loop)
        self._loop.run_forever()
        try:
            self._loop.close()
        except Exception:
            pass

    def get_wrappers(self) -> dict[str, MCPToolWrapper]:
        return dict(self._wrappers)

    def get_tool(self, name: str) -> MCPToolWrapper | None:
        return self._wrappers.get(name)

    def list_tool_names(self) -> list[str]:
        return list(self._wrappers.keys())

    def call_tool(self, name: str, arguments: dict[str, Any] | None = None) -> Any:
        """同步调用 MCP 工具。"""
        if not self._client or not self._loop or not self.connected:
            raise RuntimeError("MCP 未连接")
        timeout = (self._config.timeout if self._config else 30)
        try:
            from app.monitoring.metrics import record_mcp_tool
        except Exception:
            record_mcp_tool = None  # type: ignore
        try:
            fut = asyncio.run_coroutine_threadsafe(
                self._client.call_tool(name, arguments or {}),
                self._loop,
            )
            result = fut.result(timeout=timeout)
            if record_mcp_tool:
                record_mcp_tool(name, success=True)
            return result
        except Exception:
            if record_mcp_tool:
                try:
                    record_mcp_tool(name, success=False)
                except Exception:
                    pass
            raise

    def status(self) -> dict[str, Any]:
        cfg = self._config or get_mcp_config()
        return {
            "enabled": cfg.enabled,
            "connected": self.connected,
            "tool_count": len(self._wrappers),
            "tools": self.list_tool_names(),
            "error": self._start_error,
            "cwd": cfg.cwd,
        }


# 全局单例
mcp_manager = MCPManager()
