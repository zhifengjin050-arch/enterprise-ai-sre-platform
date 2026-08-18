"""工具注册中心

统一管理所有运维工具，供 LangGraph Agent 调用。
支持：内置工具 + MCP 工具（ENABLE_MCP=true 时合并，同名 MCP 优先）。
"""
from typing import Any


def _load_tools() -> dict[str, Any]:
    """自动发现并导入所有内置工具模块"""
    import app.tools.server_health as sh
    import app.tools.docker_ops as doc
    import app.tools.logs as log
    import app.tools.k8s_ops as k8s
    import app.tools.ssh_ops as ssh
    import app.agent.k8s_tools as k8s_agent
    import app.tools.knowledge as kb

    tools = {}

    for module in [sh, doc, log, k8s, ssh, k8s_agent, kb]:
        for attr_name in dir(module):
            attr = getattr(module, attr_name)
            if hasattr(attr, "name") and hasattr(attr, "func"):
                tools[attr.name] = attr

    return tools


# 全局内置工具注册表
_tool_registry: dict[str, Any] = {}


def _init_registry():
    """初始化内置工具注册表（惰性加载）"""
    global _tool_registry
    if not _tool_registry:
        _tool_registry = _load_tools()


def get_internal_tools() -> dict[str, Any]:
    """仅返回内置工具。"""
    _init_registry()
    return dict(_tool_registry)


def get_mcp_tools() -> dict[str, Any]:
    """返回已连接的 MCP 工具包装（未启用/未连接则为空）。"""
    try:
        from app.mcp.manager import mcp_manager
        if mcp_manager.connected:
            return mcp_manager.get_wrappers()
    except Exception:
        pass
    return {}


def get_merged_tools() -> dict[str, Any]:
    """
    Tool Router 视图：
    - 先加载内置工具
    - ENABLE_MCP 且已连接时，MCP 同名覆盖内置
    """
    merged = get_internal_tools()
    mcp_tools = get_mcp_tools()
    if mcp_tools:
        merged.update(mcp_tools)
    return merged


def get_tool(name: str) -> Any | None:
    """根据名称获取工具（MCP 优先，再内置）。"""
    mcp_tools = get_mcp_tools()
    if name in mcp_tools:
        return mcp_tools[name]
    _init_registry()
    return _tool_registry.get(name)


def get_all_tools() -> list:
    """获取合并后的全部工具对象列表。"""
    return list(get_merged_tools().values())


def _schema_from_tool(tool: Any) -> dict:
    """将工具转为 OpenAI Function Calling schema。"""
    if hasattr(tool, "to_openai_schema"):
        return tool.to_openai_schema()

    schema = {
        "type": "function",
        "function": {
            "name": tool.name,
            "description": tool.description,
        },
    }
    if hasattr(tool, "args_schema") and tool.args_schema is not None:
        model_schema = tool.args_schema.model_json_schema()
        model_schema.pop("title", None)
        schema["function"]["parameters"] = model_schema
    else:
        schema["function"]["parameters"] = {"type": "object", "properties": {}}
    return schema


def get_tool_schemas() -> list[dict]:
    """获取合并后的 OpenAI Function Calling Schema（每次调用动态刷新）。"""
    schemas = []
    for tool in get_merged_tools().values():
        schemas.append(_schema_from_tool(tool))
    return schemas


def get_tool_stats() -> dict[str, Any]:
    """供 /api/agent/stats 使用。"""
    internal = get_internal_tools()
    mcp = get_mcp_tools()
    try:
        from app.mcp.manager import mcp_manager
        mcp_status = mcp_manager.status()
    except Exception:
        mcp_status = {"enabled": False, "connected": False, "tool_count": 0}

    return {
        "internal_tool_count": len(internal),
        "mcp_tool_count": len(mcp),
        "total_tool_count": len(get_merged_tools()),
        "mcp": mcp_status,
    }
