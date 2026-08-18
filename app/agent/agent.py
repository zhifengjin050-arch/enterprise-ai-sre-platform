"""Agent 节点 — Tool Calling Agent

1. 调用 DeepSeek API（传入工具描述）
2. 判断 LLM 返回的是 tool_calls 还是直接回答
3. 如果是 tool_calls → 写入 state.tool_calls，交给 tools_node 执行
4. 如果是直接回答 → 写入 final_report
5. 记录执行轨迹（trace）和生产日志
6. 记录 Prometheus 指标
"""

import time
import logging
from app.agent.state import AgentState
from app.agent.prompts import SYSTEM_PROMPT
from app.llm.client import DeepSeekClient
from app.tools.registry import get_tool_schemas

logger = logging.getLogger("agent")


def create_agent_node():
    """创建 Agent 节点函数"""
    client = DeepSeekClient()

    def agent_node(state: AgentState) -> dict:
        existing_trace = state.get("trace", [])
        new_trace = list(existing_trace)
        node_start = time.monotonic()
        db = state.get("_db")
        user_id = state.get("_user_id")
        stream_id = state.get("_stream_id", "")
        conversation_id = state.get("_conversation_id")

        def _persist(method: str, *args, **kwargs):
            if db is None or not conversation_id:
                return
            try:
                from app.trace.service import trace_service
                getattr(trace_service, method)(db, conversation_id, *args, **kwargs)
            except Exception:
                logger.debug("trace persist skipped: %s", method)

        # --- 实时事件推送辅助 ---
        def _push(evt_type: str, **kw):
            if stream_id:
                try:
                    from app.streaming.events import stream_manager
                    stream_manager.push_event(stream_id, evt_type, **kw)
                except Exception:
                    pass

        # 每次动态刷新工具 schema（支持 MCP 运行时发现）
        tool_schemas = get_tool_schemas()

        messages = state.get("messages", [])
        user_query = ""
        for msg in messages:
            if msg.get("role") == "user":
                user_query = msg.get("content", "")
                break

        # 记录"分析用户需求"步骤（仅在首次调用时）
        has_analysis = any(t["step"] == "分析用户需求" for t in new_trace)
        if not has_analysis:
            new_trace.append({
                "step": "分析用户需求",
                "status": "completed",
                "tool": "",
                "duration_ms": round((time.monotonic() - node_start) * 1000, 1),
            })
            logger.info("分析用户需求完成")
            _push("agent_start", content="Agent 开始分析用户需求")
            _persist("save_agent_analysis", "分析用户需求")
            if user_query:
                _persist("save_user_request", user_query)

        # 构建动态 System Prompt，注入 RAG 上下文和记忆
        context_parts = [SYSTEM_PROMPT]

        # 注入知识库上下文
        if user_query and db is not None:
            try:
                from app.rag.retriever import retrieve_knowledge, format_knowledge_context
                _push("rag_search", query=user_query[:50], status="running")
                org_id = None
                if user_id:
                    try:
                        from app.database.models import User
                        u = db.query(User).filter(User.id == user_id).first()
                        if u is not None:
                            org_id = u.organization_id
                    except Exception:
                        org_id = None
                knowledge = retrieve_knowledge(
                    user_query, db, top_k=3, user_id=user_id, organization_id=org_id,
                )
                if knowledge:
                    ctx = format_knowledge_context(knowledge)
                    if ctx:
                        context_parts.append(f"\n\n{ctx}")
                    _push("rag_search", query=user_query[:50],
                          status="completed", result_count=len(knowledge))
                    _persist("save_rag_search", user_query, result_count=len(knowledge), results=knowledge)
            except Exception as e:
                logger.debug("知识库检索失败: %s", e)
                _push("rag_search", query=user_query[:50], status="failed", error=str(e)[:50])

            # 注入长期记忆
            try:
                from app.memory.long_term_memory import (
                    get_recent_failures, get_successful_solutions, format_memory_context,
                )
                _push("memory_load", type="long_term", status="running")
                failures = get_recent_failures(db, user_id=user_id, days=30, limit=3)
                solutions = get_successful_solutions(db, user_id=user_id, days=30, limit=3)
                mem_ctx = format_memory_context(failures, solutions, max_entries=6)
                if mem_ctx:
                    context_parts.append(f"\n\n{mem_ctx}")
                _push("memory_load", type="long_term", status="completed",
                      failures=len(failures), solutions=len(solutions))
                _persist("save_memory_load", failures=len(failures), solutions=len(solutions))
            except Exception as e:
                logger.debug("长期记忆检索失败: %s", e)

        full_messages = [{"role": "system", "content": "\n\n".join(context_parts)}]
        full_messages.extend(messages)

        # 记录 LLM 调用耗时指标
        llm_start = time.monotonic()
        model_name = getattr(client, "model", None) or "unknown"
        _push("llm_start", model=model_name, status="running")
        response = client.chat_with_tools(
            messages=full_messages,
            tools=tool_schemas,
        )
        llm_duration = time.monotonic() - llm_start
        _push("llm_start", model=model_name, status="completed", duration_ms=round(llm_duration * 1000))
        _persist("save_llm_call", model_name, duration_ms=round(llm_duration * 1000),
                 tool_count=len(response.tool_calls or []))

        # 记录 Prometheus LLM 指标
        try:
            from app.monitoring.metrics import observe_llm_request
            observe_llm_request(llm_duration)
            # #region agent log
            try:
                import json as _json, time as _time
                from pathlib import Path as _P
                with open(_P(__file__).resolve().parents[2] / "debug-c5f825.log", "a", encoding="utf-8") as _f:
                    _f.write(_json.dumps({"sessionId":"c5f825","runId":"v32-debug","hypothesisId":"H2","location":"app/agent/agent.py:observe_llm","message":"observe_llm_request ok","data":{"duration_s":round(llm_duration,3),"tool_calls":len(response.tool_calls or [])},"timestamp":int(_time.time()*1000)}, ensure_ascii=False)+"\n")
            except Exception:
                pass
            # #endregion
        except ImportError:
            pass
        except Exception as e:
            # #region agent log
            try:
                import json as _json, time as _time
                from pathlib import Path as _P
                with open(_P(__file__).resolve().parents[2] / "debug-c5f825.log", "a", encoding="utf-8") as _f:
                    _f.write(_json.dumps({"sessionId":"c5f825","runId":"v32-debug","hypothesisId":"H2","location":"app/agent/agent.py:observe_llm","message":"observe_llm_request failed","data":{"err":type(e).__name__,"msg":str(e)[:200]},"timestamp":int(_time.time()*1000)}, ensure_ascii=False)+"\n")
            except Exception:
                pass
            # #endregion
            raise

        if response.tool_calls:
            import json

            tool_names = [tc.function.name for tc in response.tool_calls]
            logger.info("LLM 请求调用工具: %s", tool_names)

            tool_calls = []
            for tc in response.tool_calls:
                try:
                    args = json.loads(tc.function.arguments)
                except (json.JSONDecodeError, AttributeError):
                    args = {}

                tool_calls.append({
                    "tool": tc.function.name,
                    "args": args,
                    "result": None,
                    "success": False,
                })

                # 记录工具调用轨迹（初始状态为 running）
                new_trace.append({
                    "step": f"调用 {tc.function.name}",
                    "status": "running",
                    "tool": tc.function.name,
                    "duration_ms": 0,
                })
                _push("tool_call", tool=tc.function.name, status="running",
                      args=json.dumps(args, ensure_ascii=False)[:200])
                _persist("save_tool_call", tc.function.name, args=args)

                # 记录工具调用 Prometheus 指标
                try:
                    from app.monitoring.metrics import record_tool_call
                    record_tool_call(tc.function.name)
                except ImportError:
                    pass

            assistant_msg = {
                "role": "assistant",
                "content": response.content or "",
                "tool_calls": [
                    {
                        "id": tc.id,
                        "type": "function",
                        "function": {
                            "name": tc.function.name,
                            "arguments": tc.function.arguments,
                        },
                    }
                    for tc in response.tool_calls
                ],
            }

            return {
                "messages": [assistant_msg],
                "tool_calls": tool_calls,
                "trace": new_trace,
            }

        else:
            reply = response.content or ""
            logger.info("LLM 直接回答 (%d chars)", len(reply))

            # 记录 AI 生成报告步骤
            new_trace.append({
                "step": "AI 生成报告",
                "status": "completed",
                "tool": "",
                "duration_ms": round((time.monotonic() - node_start) * 1000, 1),
            })
            _persist("save_final_answer", reply, total_duration_ms=round((time.monotonic() - node_start) * 1000, 1))
            _push("final_answer", content=reply[:800], status="completed")

            return {
                "messages": [{"role": "assistant", "content": reply}],
                "final_report": reply,
                "trace": new_trace,
            }

    return agent_node