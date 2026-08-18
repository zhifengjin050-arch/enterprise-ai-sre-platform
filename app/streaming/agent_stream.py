"""Agent Streaming Wrapper

Wraps the existing LangGraph agent with event emission
for real-time SSE streaming without modifying core agent logic.
"""
from __future__ import annotations

import logging
from typing import Optional, Callable

from app.streaming.events import stream_manager, StreamEvent
from app.agent.graph import create_agent_graph

logger = logging.getLogger("streaming.agent")

_agent_graph = create_agent_graph()


def run_agent_with_streaming(
    message: str,
    stream_id: str,
    db=None,
    user_id=None,
    conversation_id=None,
    on_event: Optional[Callable] = None,
) -> dict:
    """执行 Agent 并推送实时事件（由 agent_node 内 _push 发出真实 RAG/Tool 事件）"""
    push = stream_manager.push_event
    push(stream_id, StreamEvent.AGENT_START, content="Agent 开始分析用户需求...")
    if on_event:
        on_event("agent_start", {"content": "分析用户需求"})

    initial_state = {
        "messages": [{"role": "user", "content": message}],
        "tool_calls": [],
        "tool_results": [],
        "final_report": "",
        "trace": [],
        "_db": db,
        "_user_id": user_id,
        "_stream_id": stream_id,
        "_conversation_id": conversation_id,
    }

    try:
        result = _agent_graph.invoke(initial_state)
        report = result.get("final_report", "")
        trace = result.get("trace", [])
        push(
            stream_id,
            StreamEvent.COMPLETE,
            content="Agent 执行完成",
            trace=trace,
            report=report,
            conversation_id=conversation_id,
        )
        return {"report": report, "trace": trace}
    except Exception as e:
        import traceback
        err_detail = traceback.format_exc()
        logger.error("[Agent Stream Error] %s", err_detail[:300])
        push(stream_id, StreamEvent.ERROR, message=f"Agent 执行异常: {str(e)[:200]}")
        return {"report": "抱歉，Agent 执行失败，请稍后重试。", "trace": []}
