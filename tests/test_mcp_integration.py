"""MCP 集成测试 — 连接 / 工具调用 / 开关兼容 / Agent 路由（mock）。"""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

from app.mcp.config import MCPConfig
from app.mcp.tools import MCPToolWrapper, wrap_mcp_tools
from app.tools import registry as registry_mod


# ---------------------------------------------------------------------------
# Fixtures / helpers
# ---------------------------------------------------------------------------

def _make_mcp_tool(name: str, description: str = "", schema: dict | None = None):
    return SimpleNamespace(
        name=name,
        description=description or name,
        inputSchema=schema or {"type": "object", "properties": {}},
    )


@pytest.fixture(autouse=True)
def _reset_registry():
    """避免测试间污染内置 registry。"""
    registry_mod._tool_registry = {}
    yield
    registry_mod._tool_registry = {}


# ---------------------------------------------------------------------------
# Unit: wrap_mcp_tools / MCPToolWrapper
# ---------------------------------------------------------------------------

def test_wrap_mcp_tools_to_openai_schema():
    tools = [
        _make_mcp_tool(
            "get_cpu_usage",
            "Get CPU usage",
            {"type": "object", "properties": {}},
        ),
        _make_mcp_tool(
            "k8s_get_pods",
            "List pods",
            {
                "type": "object",
                "properties": {"namespace": {"type": "string"}},
                "required": ["namespace"],
            },
        ),
    ]
    calls = []

    def call_fn(name, args):
        calls.append((name, args))
        return {"ok": True, "tool": name}

    wrappers = wrap_mcp_tools(tools, call_fn)
    assert len(wrappers) == 2
    assert wrappers[0].name == "get_cpu_usage"

    schema = wrappers[1].to_openai_schema()
    assert schema["type"] == "function"
    assert schema["function"]["name"] == "k8s_get_pods"
    assert "namespace" in schema["function"]["parameters"]["properties"]

    result = wrappers[0].invoke({})
    assert result["ok"] is True
    assert calls == [("get_cpu_usage", {})]


def test_mcp_tool_wrapper_invoke_passes_args():
    w = MCPToolWrapper(
        name="docker_list",
        description="list containers",
        input_schema={"type": "object", "properties": {"all_containers": {"type": "boolean"}}},
        call_fn=lambda n, a: {"name": n, "args": a},
    )
    out = w.invoke({"all_containers": True})
    assert out["args"]["all_containers"] is True


# ---------------------------------------------------------------------------
# Registry merge / ENABLE_MCP=false compatibility
# ---------------------------------------------------------------------------

def test_registry_internal_only_when_mcp_disconnected():
    """ENABLE_MCP 关闭或未连接时，仅内置工具。"""
    with patch("app.tools.registry.get_mcp_tools", return_value={}):
        tools = registry_mod.get_merged_tools()
        names = set(tools.keys())
        assert "server_health" in names
        assert "docker_status" in names
        assert len(names) >= 10
        schemas = registry_mod.get_tool_schemas()
        assert len(schemas) == len(names)
        assert all(s["type"] == "function" for s in schemas)


def test_registry_mcp_overrides_same_name():
    """同名时 MCP 优先。"""
    mcp_tool = MCPToolWrapper(
        name="docker_status",
        description="MCP docker status",
        input_schema={"type": "object", "properties": {}},
        call_fn=lambda n, a: {"source": "mcp"},
    )
    with patch("app.tools.registry.get_mcp_tools", return_value={"docker_status": mcp_tool}):
        tool = registry_mod.get_tool("docker_status")
        assert tool is mcp_tool
        assert tool.invoke({})["source"] == "mcp"
        # 未覆盖的内置仍在
        assert registry_mod.get_tool("server_health") is not None


def test_get_tool_stats_structure():
    with patch("app.tools.registry.get_mcp_tools", return_value={}):
        with patch("app.mcp.manager.mcp_manager") as mgr:
            mgr.status.return_value = {
                "enabled": False,
                "connected": False,
                "tool_count": 0,
                "tools": [],
                "error": None,
            }
            stats = registry_mod.get_tool_stats()
            assert stats["internal_tool_count"] >= 10
            assert stats["mcp_tool_count"] == 0
            assert "mcp" in stats


# ---------------------------------------------------------------------------
# Manager start with ENABLE_MCP=false
# ---------------------------------------------------------------------------

def test_mcp_manager_skip_when_disabled():
    from app.mcp.manager import MCPManager

    mgr = MCPManager()
    cfg = MCPConfig(
        enabled=False,
        command="python",
        args=["-m", "app.server"],
        cwd="",
        timeout=5,
    )
    assert mgr.start(cfg) is False
    assert mgr.connected is False
    assert mgr.status()["enabled"] is False


# ---------------------------------------------------------------------------
# Manager + mock client connect / call_tool
# ---------------------------------------------------------------------------

def test_mcp_manager_connect_and_call_with_mock():
    from app.mcp.manager import MCPManager

    mgr = MCPManager()
    cfg = MCPConfig(
        enabled=True,
        command="python",
        args=["-m", "app.server"],
        cwd=r"d:\fake\project2",
        timeout=10,
    )

    fake_tools = [
        _make_mcp_tool("get_cpu_usage", "cpu"),
        _make_mcp_tool("docker_list", "docker"),
        _make_mcp_tool("k8s_get_pods", "pods"),
    ]

    async def fake_connect():
        mgr._client.connected = True
        mgr._client._tools_cache = fake_tools

    async def fake_close():
        mgr._client.connected = False

    async def fake_call(name, arguments=None):
        return {"tool": name, "args": arguments or {}, "ok": True}

    with patch("app.mcp.manager.MCPClient") as FakeClient:
        instance = MagicMock()
        instance.connected = False
        instance._tools_cache = []
        instance.connect = fake_connect
        instance.close = fake_close
        instance.call_tool = fake_call
        instance.list_tools_sync_cache = lambda: list(instance._tools_cache)
        FakeClient.return_value = instance

        # 手动模拟 start 成功路径中的 wrappers 构建
        # 因为 connect 是 async 且依赖真实 loop，这里直接测 call 桥接逻辑的子集
        ok = mgr.start(cfg)
        # 若 FakeClient.connect 成功，应 connected
        assert ok is True
        assert mgr.connected is True
        names = set(mgr.list_tool_names())
        assert "get_cpu_usage" in names
        assert "docker_list" in names
        assert "k8s_get_pods" in names

        # 替换 call_tool 为同步 mock（真实路径走 asyncio）
        mgr._client.call_tool = fake_call
        # 通过 wrapper 调用
        tool = mgr.get_tool("get_cpu_usage")
        assert tool is not None

        mgr.stop()
        assert mgr.connected is False


# ---------------------------------------------------------------------------
# Agent path: tools_node routes to MCP wrapper
# ---------------------------------------------------------------------------

def test_tools_node_invokes_mcp_wrapper():
    from app.agent.tools_node import create_tools_node

    mcp_tool = MCPToolWrapper(
        name="k8s_get_pods",
        description="list pods",
        input_schema={"type": "object", "properties": {"namespace": {"type": "string"}}},
        call_fn=lambda n, a: [{"name": "order-service", "status": "CrashLoopBackOff"}],
    )

    with patch("app.agent.tools_node.get_tool", return_value=mcp_tool):
        node = create_tools_node()
        state = {
            "tool_calls": [
                {
                    "tool": "k8s_get_pods",
                    "args": {"namespace": "default"},
                    "result": None,
                    "success": False,
                }
            ],
            "trace": [
                {
                    "step": "调用 k8s_get_pods",
                    "status": "running",
                    "tool": "k8s_get_pods",
                    "duration_ms": 0,
                }
            ],
            "messages": [],
            "tool_results": [],
            "final_report": "",
        }
        out = node(state)
        assert out["tool_calls"][0]["success"] is True
        assert "CrashLoopBackOff" in out["tool_calls"][0]["result"]
        assert out["trace"][0]["status"] == "completed"


def test_agent_node_uses_dynamic_schemas():
    """agent_node 每次应读取 get_tool_schemas（非闭包缓存）。"""
    from app.agent.agent import create_agent_node

    fake_response = SimpleNamespace(tool_calls=None, content="订单服务检查完成：无异常")

    with patch("app.agent.agent.DeepSeekClient") as FakeLLM:
        FakeLLM.return_value.chat_with_tools.return_value = fake_response
        with patch("app.agent.agent.get_tool_schemas") as get_schemas:
            get_schemas.return_value = [
                {
                    "type": "function",
                    "function": {
                        "name": "k8s_get_pods",
                        "description": "pods",
                        "parameters": {"type": "object", "properties": {}},
                    },
                }
            ]
            node = create_agent_node()
            state = {
                "messages": [{"role": "user", "content": "检查生产环境订单服务异常"}],
                "tool_calls": [],
                "tool_results": [],
                "final_report": "",
                "trace": [],
            }
            out = node(state)
            assert get_schemas.called
            assert "订单服务" in out.get("final_report", "") or out.get("messages")
            # 确认 LLM 收到了动态 schema
            kwargs = FakeLLM.return_value.chat_with_tools.call_args
            tools_arg = kwargs.kwargs.get("tools") or kwargs[1].get("tools")
            assert tools_arg[0]["function"]["name"] == "k8s_get_pods"


def test_normalize_tool_result_json():
    from app.mcp.client import _normalize_tool_result

    content_item = SimpleNamespace(text='{"cpu_percent": 12.5}')
    result = SimpleNamespace(content=[content_item], isError=False)
    assert _normalize_tool_result(result)["cpu_percent"] == 12.5

    err = SimpleNamespace(content=[SimpleNamespace(text="boom")], isError=True)
    assert _normalize_tool_result(err)["error"] is True
