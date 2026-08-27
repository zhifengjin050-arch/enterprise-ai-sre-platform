"""Agent 状态类型定义

使用 LangGraph 的 Annotated + operator.add 实现消息累加。
"""
from typing import TypedDict, List, Optional, Annotated, NotRequired
import operator


class ToolCall(TypedDict):
    tool: str
    args: dict
    result: Optional[str]
    success: bool


class AgentTraceStep(TypedDict):
    """Agent 执行轨迹步骤"""
    step: str
    status: str  # "completed" | "running" | "failed"
    tool: str
    duration_ms: float


class AgentState(TypedDict):
    """LangGraph Agent 状态

    关键设计:
      - messages 使用 operator.add 累加（appending），而非覆盖
      - tool_calls 由 agent_node 写入，tools_node 更新
      - final_report 在最后一轮由 agent_node 写入
      - trace 记录 Agent 执行轨迹
      - _stream_id: 可选 SSE 流 ID，用于实时事件推送
    """
    messages: Annotated[List[dict], operator.add]
    tool_calls: List[ToolCall]
    tool_results: List[str]
    final_report: str
    trace: List[AgentTraceStep]
    _stream_id: NotRequired[Optional[str]]
    _db: NotRequired[object]
    _user_id: NotRequired[Optional[int]]
    _conversation_id: NotRequired[Optional[int]]
