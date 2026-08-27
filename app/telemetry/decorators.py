"""Telemetry decorators for Agent/LLM/MCP/RAG tracing"""
import functools
import logging
from opentelemetry import trace
from app.telemetry.setup import tracer

logger = logging.getLogger("telemetry.decorators")


def trace_agent_node(node_name: str):
    """Decorator for Agent node tracing"""
    def decorator(func):
        @functools.wraps(func)
        def wrapper(state, *args, **kwargs):
            with tracer().start_as_current_span(
                f"agent.{node_name}",
                attributes={"node": node_name}
            ) as span:
                try:
                    result = func(state, *args, **kwargs)
                    tool_calls = state.get("tool_calls", [])
                    span.set_attribute("tool_calls.count", len(tool_calls))
                    return result
                except Exception as e:
                    span.record_exception(e)
                    span.set_status(trace.Status(trace.StatusCode.ERROR, str(e)))
                    raise
        return wrapper
    return decorator


def trace_llm_call(model: str = ""):
    """Decorator for LLM call tracing"""
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            with tracer().start_as_current_span(
                "llm.call",
                attributes={
                    "llm.model": model or kwargs.get("model", "unknown"),
                    "llm.tools_count": len(kwargs.get("tools", [])),
                }
            ) as span:
                try:
                    result = func(*args, **kwargs)
                    if hasattr(result, 'usage'):
                        span.set_attribute("llm.completion_tokens", result.usage.completion_tokens)
                        span.set_attribute("llm.prompt_tokens", result.usage.prompt_tokens)
                    return result
                except Exception as e:
                    span.record_exception(e)
                    span.set_status(trace.Status(trace.StatusCode.ERROR, str(e)))
                    raise
        return wrapper
    return decorator


def trace_tool_call(tool_name: str):
    """Decorator for tool call tracing"""
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            with tracer().start_as_current_span(
                f"tool.{tool_name}",
                attributes={"tool": tool_name}
            ) as span:
                try:
                    result = func(*args, **kwargs)
                    return result
                except Exception as e:
                    span.record_exception(e)
                    span.set_status(trace.Status(trace.StatusCode.ERROR, str(e)))
                    raise
        return wrapper
    return decorator
