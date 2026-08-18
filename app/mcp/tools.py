"""将 MCP Tool 定义包装为 Agent 可调用对象（兼容 tools_node.invoke）。"""

from __future__ import annotations

from typing import Any, Callable


class MCPToolWrapper:
    """模拟 LangChain Tool 接口：name / description / args_schema / invoke / func。"""

    def __init__(
        self,
        name: str,
        description: str,
        input_schema: dict[str, Any] | None,
        call_fn: Callable[[str, dict[str, Any]], Any],
    ):
        self.name = name
        self.description = description or name
        self._input_schema = input_schema or {"type": "object", "properties": {}}
        self._call_fn = call_fn
        # tools_node / registry 用 hasattr(attr, "func") 识别；提供占位
        self.func = self.invoke
        self.args_schema = None  # schema 走 to_openai_schema
        try:
            from app.mcp.metadata import get_tool_metadata
            meta = get_tool_metadata(name)
            self.metadata = meta.to_dict() if meta else {
                "name": name,
                "description": self.description,
                "category": "unknown",
                "risk_level": "unknown",
                "required_permission": "devops.viewer",
                "audit_required": False,
            }
        except Exception:
            self.metadata = {"name": name, "risk_level": "unknown"}

    def invoke(self, args: dict[str, Any] | None = None) -> Any:
        return self._call_fn(self.name, args or {})

    def to_openai_schema(self) -> dict[str, Any]:
        params = dict(self._input_schema) if self._input_schema else {
            "type": "object",
            "properties": {},
        }
        params.pop("title", None)
        if "type" not in params:
            params["type"] = "object"
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": params,
            },
        }


def wrap_mcp_tools(
    mcp_tools: list[Any],
    call_fn: Callable[[str, dict[str, Any]], Any],
) -> list[MCPToolWrapper]:
    """将 session.list_tools() 结果转为 wrapper 列表。"""
    wrappers: list[MCPToolWrapper] = []
    for t in mcp_tools:
        name = getattr(t, "name", None) or ""
        if not name:
            continue
        description = getattr(t, "description", None) or name
        input_schema = getattr(t, "inputSchema", None) or getattr(t, "input_schema", None)
        if hasattr(input_schema, "model_dump"):
            input_schema = input_schema.model_dump()
        wrappers.append(
            MCPToolWrapper(
                name=name,
                description=description,
                input_schema=input_schema if isinstance(input_schema, dict) else None,
                call_fn=call_fn,
            )
        )
    return wrappers
