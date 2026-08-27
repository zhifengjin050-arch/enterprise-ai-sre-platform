"""LangGraph StateGraph with Tool Calling loop.

   START -> agent_node -> {has pending tool_calls?}
     yes -> tools_node -> agent_node
     no  -> END
"""

from langgraph.graph import StateGraph, START, END
from langgraph.graph.state import CompiledStateGraph

from app.agent.state import AgentState
from app.agent.agent import create_agent_node
from app.agent.tools_node import create_tools_node


def _should_continue(state: AgentState) -> str:
    """条件边：判断是否还有待执行的工具调用"""
    tool_calls = state.get("tool_calls", [])
    pending = [tc for tc in tool_calls if tc.get("result") is None]
    if pending:
        return "tools"
    return "end"


def create_agent_graph() -> CompiledStateGraph:
    workflow = StateGraph(AgentState)

    agent_fn = create_agent_node()
    tools_fn = create_tools_node()

    workflow.add_node("agent", agent_fn)
    workflow.add_node("tools", tools_fn)

    workflow.add_edge(START, "agent")
    workflow.add_conditional_edges(
        "agent",
        _should_continue,
        {"tools": "tools", "end": END},
    )
    workflow.add_edge("tools", "agent")

    return workflow.compile()
