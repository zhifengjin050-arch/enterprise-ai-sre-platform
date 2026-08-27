"""Tools 节点 — 执行工具调用

读取 state.tool_calls，逐个执行，将结果写入 state.tool_calls 和 state.messages（作为 tool 消息）。
同时更新执行轨迹中的工具调用状态并记录生产日志。
"""

import json
import time
import logging

from app.agent.state import AgentState
from app.tools.registry import get_tool

logger = logging.getLogger("agent")


def _update_trace_step(trace: list, tool_name: str, status: str, duration_ms: float):
    """更新轨迹中指定工具的步骤状态（从后往前找第一个 running 状态）"""
    for t in reversed(trace):
        if t["step"] == f"调用 {tool_name}" and t["status"] == "running":
            t["status"] = status
            t["duration_ms"] = duration_ms
            break


def create_tools_node():
    """创建 Tools 节点函数"""

    def _push_tool_result(stream_id: str, tool_name: str, status: str, result: str = "", duration_ms: float = 0):
        if stream_id:
            try:
                from app.streaming.events import stream_manager
                stream_manager.push_event(stream_id, "tool_result",
                                          tool=tool_name, status=status,
                                          result=result[:300],
                                          duration_ms=round(duration_ms))
            except Exception:
                pass

    def tools_node(state: AgentState) -> dict:
        tool_calls = state.get("tool_calls", [])
        existing_trace = state.get("trace", [])
        stream_id = state.get("_stream_id", "")
        db = state.get("_db")
        conversation_id = state.get("_conversation_id")
        new_trace = list(existing_trace)
        tool_messages = []
        updated_tool_calls = []
        tool_results = []

        for tc in tool_calls:
            if tc.get("result") is not None:
                continue

            tool_name = tc["tool"]
            tool_args = tc.get("args", {})
            tool_fn = get_tool(tool_name)
            tool_start = time.monotonic()

            if tool_fn is None:
                elapsed = round((time.monotonic() - tool_start) * 1000, 1)
                result_str = f"Error: tool '{tool_name}' not found"
                logger.error("工具 %s 未注册", tool_name)
                updated_tool_calls.append({
                    "tool": tool_name, "args": tool_args,
                    "result": result_str, "success": False,
                })
                tool_results.append(result_str)
                tool_messages.append({
                    "role": "tool",
                    "tool_call_id": tool_name,
                    "content": result_str,
                })
                _update_trace_step(new_trace, tool_name, "failed", elapsed)
                _push_tool_result(stream_id, tool_name, "failed", result_str, elapsed)
                continue

            try:
                from app.knowledge.context import current_db, current_user_id
                tok_db = current_db.set(db)
                tok_uid = current_user_id.set(state.get("_user_id"))
                try:
                    raw_result = tool_fn.invoke(tool_args)
                finally:
                    current_db.reset(tok_db)
                    current_user_id.reset(tok_uid)
                if isinstance(raw_result, (dict, list)):
                    result_str = json.dumps(raw_result, ensure_ascii=False, indent=2)
                else:
                    result_str = str(raw_result)

                elapsed = round((time.monotonic() - tool_start) * 1000, 1)
                logger.info("工具 %s 执行成功 (%.0fms)", tool_name, elapsed)

                updated_tool_calls.append({
                    "tool": tool_name, "args": tool_args,
                    "result": result_str, "success": True,
                })
                tool_results.append(result_str)
                tool_messages.append({
                    "role": "tool",
                    "tool_call_id": tool_name,
                    "content": result_str,
                })
                _update_trace_step(new_trace, tool_name, "completed", elapsed)
                _push_tool_result(stream_id, tool_name, "completed", result_str, elapsed)
                if db is not None and conversation_id:
                    try:
                        from app.trace.service import trace_service
                        trace_service.save_tool_result(
                            db, conversation_id, tool_name, True, result_str, elapsed
                        )
                    except Exception:
                        pass

            except Exception as e:
                elapsed = round((time.monotonic() - tool_start) * 1000, 1)
                error_msg = f"Tool '{tool_name}' execution failed: {e}"
                logger.error("工具 %s 执行失败 (%.0fms): %s", tool_name, elapsed, e)
                updated_tool_calls.append({
                    "tool": tool_name, "args": tool_args,
                    "result": error_msg, "success": False,
                })
                tool_results.append(error_msg)
                tool_messages.append({
                    "role": "tool",
                    "tool_call_id": tool_name,
                    "content": error_msg,
                })
                _update_trace_step(new_trace, tool_name, "failed", elapsed)
                _push_tool_result(stream_id, tool_name, "failed", error_msg, elapsed)
                if db is not None and conversation_id:
                    try:
                        from app.trace.service import trace_service
                        trace_service.save_tool_result(
                            db, conversation_id, tool_name, False, error_msg, elapsed
                        )
                    except Exception:
                        pass

        return {
            "messages": tool_messages,
            "tool_calls": updated_tool_calls,
            "tool_results": tool_results,
            "trace": new_trace,
        }

    return tools_node
