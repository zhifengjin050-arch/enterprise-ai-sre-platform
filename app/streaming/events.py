"""Agent Streaming Events Manager

Provides SSE-based real-time event streaming for Agent execution process.
Events: thinking, rag_search, memory_load, llm_start, tool_call, tool_result, final_answer
"""
from __future__ import annotations

import asyncio
import json
import logging
from typing import AsyncGenerator, Optional

logger = logging.getLogger("streaming")


class StreamEvent:
    """SSE 事件类型定义"""

    # Agent 生命周期事件
    AGENT_START = "agent_start"
    THINKING = "thinking"
    RAG_SEARCH = "rag_search"
    MEMORY_LOAD = "memory_load"
    LLM_START = "llm_start"
    TOOL_CALL = "tool_call"
    TOOL_RESULT = "tool_result"
    FINAL_ANSWER = "final_answer"
    COMPLETE = "complete"
    ERROR = "error"

    @staticmethod
    def make(event_type: str, **kwargs) -> dict:
        """构造 sse-starlette 可直接 yield 的事件 dict"""
        data = {"type": event_type, **kwargs}
        return {"data": json.dumps(data, ensure_ascii=False, default=str)}


class AgentStreamManager:
    """Agent 实时事件流管理器

    使用 asyncio.Queue 实现生产者-消费者模式，
    每个 Agent 执行实例拥有独立的事件队列。
    """

    def __init__(self):
        self._queues: dict[str, asyncio.Queue] = {}
        self._loops: dict[str, asyncio.AbstractEventLoop] = {}

    def create_stream(self, stream_id: str) -> asyncio.Queue:
        """为 Agent 执行创建事件流队列"""
        q: asyncio.Queue = asyncio.Queue()
        self._queues[stream_id] = q
        try:
            self._loops[stream_id] = asyncio.get_running_loop()
        except RuntimeError:
            self._loops.pop(stream_id, None)
        return q

    def get_queue(self, stream_id: str) -> Optional[asyncio.Queue]:
        return self._queues.get(stream_id)

    def push_event(self, stream_id: str, event_type: str, **kwargs):
        """推送事件到指定流（线程安全，投递到创建该 stream 的事件循环）"""
        q = self._queues.get(stream_id)
        if q is None:
            logger.warning("Stream %s not found, event dropped: %s", stream_id, event_type)
            return
        loop = self._loops.get(stream_id)
        try:
            if loop is not None and loop.is_running():
                asyncio.run_coroutine_threadsafe(q.put((event_type, kwargs)), loop)
                return
            running = asyncio.get_running_loop()
            running.create_task(q.put((event_type, kwargs)))
        except RuntimeError:
            logger.warning("Failed to push event %s on stream %s (no loop)", event_type, stream_id)
        except Exception as e:
            logger.error("Failed to push event: %s", e)

    async def event_generator(self, stream_id: str) -> AsyncGenerator[dict, None]:
        """生成 SSE 事件流（异步生成器）"""
        q = self._queues.get(stream_id)
        if q is None:
            yield StreamEvent.make("error", message="Stream not found")
            return

        try:
            while True:
                try:
                    event_type, data = await asyncio.wait_for(q.get(), timeout=1.0)
                except asyncio.TimeoutError:
                    yield {"comment": "heartbeat"}
                    continue

                yield StreamEvent.make(event_type, **data)

                if event_type in ("complete", "error"):
                    break
        except asyncio.CancelledError:
            pass
        finally:
            self._queues.pop(stream_id, None)
            self._loops.pop(stream_id, None)

    def cleanup(self, stream_id: str):
        self._queues.pop(stream_id, None)
        self._loops.pop(stream_id, None)


# 全局单例
stream_manager = AgentStreamManager()
