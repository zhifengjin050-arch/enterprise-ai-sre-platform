"""Agent Trace 执行轨迹服务

类似 LangSmith Trace，记录 Agent 完整执行链路：
用户请求 → Agent分析 → RAG检索 → Memory读取 → LLM调用 → MCP工具调用 → 工具结果 → 最终输出
"""
from __future__ import annotations

import json
import logging
import time
from typing import Optional
from sqlalchemy.orm import Session as SASession

from app.database.models import AgentTrace

logger = logging.getLogger("trace")


class TraceService:
    """Trace 服务 — 保存和查询 Agent 执行轨迹"""

    def _create_trace_entry(
        self,
        db: SASession,
        conversation_id: int,
        step: int,
        event_type: str,
        content: str = "",
        tool_name: str = "",
        duration: float = 0.0,
        meta_info: Optional[dict] = None,
    ) -> AgentTrace:
        """创建一条轨迹记录"""
        entry = AgentTrace(
            conversation_id=conversation_id,
            step=step,
            event_type=event_type,
            content=str(content)[:500],
            tool_name=tool_name,
            duration=duration,
            meta_info=meta_info,
        )
        db.add(entry)
        return entry

    def save_user_request(self, db: SASession, conversation_id: int, message: str):
        """保存用户请求"""
        entry = self._create_trace_entry(
            db, conversation_id, 0, "user_request",
            content=message[:200],
        )
        db.commit()
        logger.debug("Trace saved: user_request (conv=%d)", conversation_id)
        return entry

    def save_agent_analysis(self, db: SASession, conversation_id: int, analysis: str):
        """保存 Agent 分析"""
        entry = self._create_trace_entry(
            db, conversation_id, 1, "agent_start",
            content=analysis[:200],
        )
        db.commit()
        return entry

    def save_rag_search(self, db: SASession, conversation_id: int, query: str,
                        result_count: int = 0, results: Optional[list] = None):
        """保存 RAG 检索"""
        entry = self._create_trace_entry(
            db, conversation_id, 2, "rag_search",
            content=f"Query: {query[:100]}, Results: {result_count}",
            meta_info={"query": query[:100], "result_count": result_count,
                       "results": [r.get("title", "")[:50] for r in (results or [])]},
        )
        db.commit()
        return entry

    def save_memory_load(self, db: SASession, conversation_id: int,
                         failures: int = 0, solutions: int = 0):
        """保存 Memory 读取"""
        entry = self._create_trace_entry(
            db, conversation_id, 3, "memory_load",
            content=f"Loaded {failures} failures, {solutions} solutions",
            meta_info={"failures": failures, "solutions": solutions},
        )
        db.commit()
        return entry

    def save_llm_call(self, db: SASession, conversation_id: int,
                      model: str, duration_ms: float, tool_count: int = 0):
        """保存 LLM 调用"""
        entry = self._create_trace_entry(
            db, conversation_id, 4, "llm_start",
            content=f"Model: {model}, Tool calls: {tool_count}",
            duration=duration_ms,
            meta_info={"model": model, "tool_count": tool_count},
        )
        db.commit()
        return entry

    def save_tool_call(self, db: SASession, conversation_id: int,
                       tool_name: str, args: dict = None):
        """保存 MCP/内部工具调用"""
        entry = self._create_trace_entry(
            db, conversation_id, 5, "tool_call",
            content=f"Calling {tool_name}",
            tool_name=tool_name,
            meta_info={"args": {k: str(v)[:50] for k, v in (args or {}).items()}},
        )
        db.commit()
        return entry

    def save_tool_result(self, db: SASession, conversation_id: int,
                         tool_name: str, success: bool, result: str = "",
                         duration_ms: float = 0.0):
        """保存工具执行结果"""
        entry = self._create_trace_entry(
            db, conversation_id, 6, "tool_result",
            content=f"{'✅' if success else '❌'} {tool_name}: {result[:200]}",
            tool_name=tool_name,
            duration=duration_ms,
            meta_info={"success": success},
        )
        db.commit()
        return entry

    def save_final_answer(self, db: SASession, conversation_id: int,
                          answer: str, total_duration_ms: float = 0.0):
        """保存最终输出"""
        entry = self._create_trace_entry(
            db, conversation_id, 7, "final_answer",
            content=answer[:300],
            duration=total_duration_ms,
        )
        db.commit()
        return entry

    def get_traces(self, db: SASession, conversation_id: int) -> list[dict]:
        """获取指定会话的完整执行轨迹"""
        entries = db.query(AgentTrace).filter(
            AgentTrace.conversation_id == conversation_id
        ).order_by(AgentTrace.step, AgentTrace.created_at).all()

        return [
            {
                "id": e.id,
                "step": e.step,
                "event_type": e.event_type,
                "content": e.content,
                "tool_name": e.tool_name or "",
                "duration": round(e.duration, 2),
                "meta_info": e.meta_info,
                "created_at": e.created_at.isoformat() if e.created_at else None,
            }
            for e in entries
        ]

    def get_conversation_trace_grouped(self, db: SASession, conversation_id: int) -> dict:
        """获取按步骤分组的结构化轨迹"""
        entries = db.query(AgentTrace).filter(
            AgentTrace.conversation_id == conversation_id
        ).order_by(AgentTrace.step, AgentTrace.created_at).all()

        steps = []
        for e in entries:
            step_entry = {
                "event": e.event_type,
                "content": e.content,
                "tool": e.tool_name or "",
                "duration": round(e.duration, 2),
            }
            if e.meta_info:
                step_entry["meta"] = e.meta_info
            steps.append(step_entry)

        return {"conversation_id": conversation_id, "steps": steps}


trace_service = TraceService()