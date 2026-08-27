"""AI 智能运维助手 — FastAPI 应用入口

- 静态文件服务
- POST /api/chat — Agent 对话接口（支持 JWT + 会话历史保存）
- GET /api/server/status — 本机服务器实时状态
- GET /health — 健康检查
- GET /metrics — Prometheus 指标接口
- /api/auth/* — 用户认证接口
- /api/conversations/* — 会话管理接口
- /api/servers/* — 远程服务器管理 CRUD
- /api/monitoring/* — 监控指标接口
- /api/alerts/* — 告警管理接口
- /api/agent/executions/* — Agent 执行记录接口
- /ws/chat/{conversation_id} — WebSocket 实时 Agent 执行轨迹
"""

import asyncio
import json
import logging
import os
import time
from collections import defaultdict
from contextlib import asynccontextmanager
from typing import Optional

from fastapi import FastAPI, Request, WebSocket, WebSocketDisconnect, Depends, Query, HTTPException, Header
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.exception_handlers import http_exception_handler
from starlette.exceptions import HTTPException as StarletteHTTPException
from pydantic import BaseModel, Field
from pathlib import Path
from starlette.concurrency import run_in_threadpool
from sqlalchemy import func, text as sa_text
from sqlalchemy.orm import Session as SASession

from app.agent.graph import create_agent_graph
from app.config import settings, APP_VERSION
from app.logging_config import setup_logging
from app.llm.client import DeepSeekClient
from app.database.session import init_db, get_db, get_local_session
from app.database.models import (
    User, Conversation, Message, ManagedServer, AgentExecution, ExecutionStatus,
)
from app.auth.router import router as auth_router
from app.auth.dependencies import get_current_user, get_chat_user, require_system_status_user
from app.auth.jwt import decode_access_token
from app.security.secrets import encrypt_secret
from app.streaming.events import stream_manager, StreamEvent
from app.trace.service import trace_service
from sse_starlette.sse import EventSourceResponse

# ============================================================
# 日志初始化
# ============================================================
setup_logging(settings.log_level)
logger = logging.getLogger(__name__)

# ============================================================
# 限流器（内存版）
# ============================================================
_rate_limit_store: dict[str, list[float]] = defaultdict(list)
_RATE_LIMIT = settings.rate_limit_per_minute
_RATE_WINDOW = 60  # seconds
_RATE_MAX_KEYS = 5000


def _prune_rate_bucket(client_ip: str, now: float) -> list[float]:
    hits = [t for t in _rate_limit_store.get(client_ip, []) if now - t < _RATE_WINDOW]
    if hits:
        _rate_limit_store[client_ip] = hits
    else:
        _rate_limit_store.pop(client_ip, None)
    if len(_rate_limit_store) > _RATE_MAX_KEYS:
        stale = min(_rate_limit_store, key=lambda k: _rate_limit_store[k][0] if _rate_limit_store[k] else now)
        _rate_limit_store.pop(stale, None)
    return _rate_limit_store.get(client_ip, [])


@asynccontextmanager
async def lifespan(_app: FastAPI):
    """应用启动 / 关闭：数据库、监控、MCP、遥测。"""
    try:
        settings.validate_production_security()
    except RuntimeError:
        logger.critical("生产安全检查失败，拒绝启动")
        raise

    try:
        init_db()
        logger.info("数据库初始化完成")
    except Exception as e:
        logger.warning("数据库初始化失败: %s", e)

    try:
        from app.monitoring.collector import start_collector
        start_collector(interval=settings.metrics_collect_interval)
        logger.info("指标采集线程已启动")
    except Exception as e:
        logger.warning("指标采集线程启动失败: %s", e)

    try:
        from app.alert.manager import start_alert_evaluator
        start_alert_evaluator(interval=settings.alert_evaluate_interval)
        logger.info("告警评估线程已启动")
    except Exception as e:
        logger.warning("告警评估线程启动失败: %s", e)

    try:
        from app.mcp.manager import mcp_manager
        if mcp_manager.start():
            logger.info("MCP Client 已连接: %s", mcp_manager.status())
        else:
            logger.info("MCP 未启用或连接失败，使用内置工具")
    except Exception as e:
        logger.warning("MCP 启动异常，降级到内置工具: %s", e)

    try:
        from app.telemetry.setup import setup_telemetry
        setup_telemetry(app=_app, service_version=APP_VERSION)
        logger.info("OpenTelemetry 已初始化")
    except Exception as e:
        logger.warning("OpenTelemetry 初始化失败: %s", e)

    yield

    try:
        from app.mcp.manager import mcp_manager
        mcp_manager.stop()
        logger.info("MCP Client 已关闭")
    except Exception as e:
        logger.warning("MCP 关闭异常: %s", e)

    try:
        from app.tools.ssh_ops import close_all_ssh_connections
        close_all_ssh_connections()
        logger.info("SSH 连接已关闭")
    except Exception as e:
        logger.warning("SSH 关闭异常: %s", e)

    try:
        from app.monitoring.collector import stop_collector
        stop_collector()
        logger.info("指标采集线程已停止")
    except Exception as e:
        logger.warning("指标采集线程停止异常: %s", e)

    try:
        from app.alert.manager import stop_alert_evaluator
        stop_alert_evaluator()
        logger.info("告警评估线程已停止")
    except Exception as e:
        logger.warning("告警评估线程停止异常: %s", e)


# ============================================================
# 初始化 FastAPI
# ============================================================
_prod = settings.is_production()
app = FastAPI(
    title="AI 智能运维助手 API",
    description="Enterprise AI DevOps Agent — MCP-powered 企业级智能运维平台 REST API",
    version=APP_VERSION,
    docs_url=None if _prod else "/docs",
    redoc_url=None if _prod else "/redoc",
    openapi_url=None if _prod else "/openapi.json",
    lifespan=lifespan,
)

# ============================================================
# CORS 配置
# ============================================================
origins = [o.strip() for o in settings.cors_origins.split(",") if o.strip()]
if settings.is_production() and not origins:
    origins = []
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins if origins else (["*"] if not settings.is_production() else []),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ============================================================
# 中间件 — API 限流
# ============================================================
_redis_rl_ok: Optional[bool] = None
_redis_rl_checked = 0.0


def _redis_rate_limit_ready() -> bool:
    global _redis_rl_ok, _redis_rl_checked
    now = time.monotonic()
    if _redis_rl_ok is not None and now - _redis_rl_checked < 15:
        return _redis_rl_ok
    from app.cache.redis import ping_redis
    _redis_rl_ok = ping_redis()
    _redis_rl_checked = now
    return _redis_rl_ok


def _memory_allow(client_ip: str) -> tuple[bool, int]:
    now = time.monotonic()
    hits = _prune_rate_bucket(client_ip, now)
    if len(hits) >= _RATE_LIMIT:
        return False, _RATE_WINDOW
    _rate_limit_store.setdefault(client_ip, []).append(now)
    return True, 0


def _mark_redis_rl_down() -> None:
    global _redis_rl_ok
    _redis_rl_ok = False


@app.middleware("http")
async def rate_limit_middleware(request: Request, call_next):
    path = request.url.path
    if path in ("/health", "/metrics", "/docs", "/redoc", "/openapi.json") or path.startswith("/ws/"):
        return await call_next(request)
    if (settings.environment or "").strip().lower() in ("test", "testing") or os.environ.get("PYTEST_CURRENT_TEST"):
        return await call_next(request)

    client_ip = request.client.host if request.client else "unknown"
    allowed, retry_after = True, 0
    used_redis = False
    if _redis_rate_limit_ready():
        from app.cache.rate_limiter import rate_limiter
        result = rate_limiter.check(client_ip, _RATE_LIMIT, _RATE_WINDOW)
        if result is None:
            _mark_redis_rl_down()
        else:
            allowed, retry_after = result
            used_redis = True
    if not used_redis:
        allowed, retry_after = _memory_allow(client_ip)

    if not allowed:
        logger.warning("限流触发: %s (%d 次/分钟)", client_ip, _RATE_LIMIT)
        return JSONResponse(
            status_code=429,
            content={"detail": "请求过于频繁，请稍后再试", "retry_after": retry_after or _RATE_WINDOW},
        )
    return await call_next(request)


# ============================================================
# 中间件 — 请求日志 + Prometheus 指标
# ============================================================
@app.middleware("http")
async def log_requests(request: Request, call_next):
    start = time.monotonic()
    response = await call_next(request)
    elapsed_ms = (time.monotonic() - start) * 1000
    logger.info(
        "%s %s → %s (%.0fms)",
        request.method,
        request.url.path,
        response.status_code,
        elapsed_ms,
    )

    # 记录 Prometheus HTTP 指标
    try:
        from app.monitoring.metrics import record_http_request
        record_http_request(request.method, request.url.path, response.status_code, elapsed_ms / 1000)
    except ImportError:
        pass

    return response


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    if isinstance(exc, (HTTPException, StarletteHTTPException)):
        return await http_exception_handler(request, exc)
    logger.exception("未处理异常: %s %s", request.method, request.url.path)
    return JSONResponse(status_code=500, content={"detail": "服务器内部错误"})


# ============================================================
# Agent 单例
# ============================================================
_agent_graph = create_agent_graph()
_static_dir = Path(__file__).parent / "static"


# ============================================================
# 请求模型
# ============================================================
class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=2000, description="用户消息")
    session_id: str = Field("default", description="会话 ID（用于多轮对话）")
    conversation_id: Optional[int] = Field(None, description="会话 ID（关联数据库会话）")


# ============================================================
# Agent 调用（同步包装）
# ============================================================
def _run_agent(message: str, db=None, user_id=None, stream_id="", conversation_id=None) -> dict:
    """同步 Agent 调用，返回 report 和 trace"""
    agent_logger = logging.getLogger("agent")
    agent_logger.info("[Agent Start] 用户请求: %s", message[:100])

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
        agent_logger.info(
            "[Agent End] 报告生成完成 (%d chars, %d trace steps)",
            len(report), len(trace),
        )

        # 记录 Prometheus Agent 指标
        try:
            from app.monitoring.metrics import observe_agent_execution
            observe_agent_execution(
                duration=result.get("_duration", 0),
                success=True,
                tools_called=len(result.get("tool_calls", [])),
            )
        except ImportError:
            pass

        # 检查用户消息是否为审批确认响应（v3.0.0 自动修复）
        try:
            from app.agent.approval import parse_approval_response, execute_approved_action
            approval_token = parse_approval_response(message, user_id=user_id)
            if approval_token:
                result = execute_approved_action(approval_token, db=db)
                if result["success"]:
                    report = f"## ✅ 自动修复执行成功\n\n**操作**: {result.get('action_id', '')}\n\n**结果**:\n```\n{result.get('result', '')}\n```\n\n修复耗时: {result.get('duration_ms', 0)}ms"
                else:
                    report = f"## ❌ 自动修复执行失败\n\n**错误**: {result.get('error', '未知错误')}"
        except Exception as e:
            logger.debug("审批解析跳过: %s", e)

        return {"report": report, "trace": trace}
    except Exception:
        import traceback
        error_detail = traceback.format_exc()
        agent_logger.error("[Agent Error] %s", error_detail)

        try:
            from app.monitoring.metrics import observe_agent_execution
            observe_agent_execution(duration=0, success=False, tools_called=0)
        except ImportError:
            pass

        return {
            "report": "抱歉，Agent 执行失败，请稍后重试。",
            "trace": [],
        }


def _save_messages(db: SASession, conversation_id: int, user_message: str, report: str, trace: list):
    """保存用户消息和 Agent 回复到数据库"""
    try:
        # 保存用户消息
        user_msg = Message(
            conversation_id=conversation_id,
            role="user",
            content=user_message,
            trace_json=None,
        )
        db.add(user_msg)

        # 保存 Agent 回复
        assistant_msg = Message(
            conversation_id=conversation_id,
            role="assistant",
            content=report,
            trace_json=trace,
        )
        db.add(assistant_msg)
        db.commit()
        logger.info("保存会话消息: conversation_id=%d", conversation_id)
    except Exception as e:
        logger.warning("保存消息失败: %s", e)
        db.rollback()


def _save_agent_execution(db: SASession, user_id: int, conversation_id: Optional[int],
                          status: str, duration: float, tools_called: int, error: Optional[str] = None):
    """保存 Agent 执行记录到数据库"""
    try:
        execution = AgentExecution(
            user_id=user_id,
            conversation_id=conversation_id,
            status=status,
            duration=duration,
            tools_called=tools_called,
            error_message=error,
        )
        db.add(execution)
        db.commit()
    except Exception as e:
        logger.warning("保存 Agent 执行记录失败: %s", e)
        db.rollback()


def _agent_failed(report: str) -> bool:
    return (report or "").startswith("抱歉，Agent 执行失败")


def _execution_status_for(report: str) -> ExecutionStatus:
    return ExecutionStatus.failed if _agent_failed(report) else ExecutionStatus.success


# ============================================================
# 注册认证路由
# ============================================================
app.include_router(auth_router)

# ============================================================
# 注册企业管理路由
# ============================================================
from app.api.org_router import router as org_router
from app.api.knowledge_hub import router as knowledge_hub_router
app.include_router(org_router)
app.include_router(knowledge_hub_router)

# ============================================================
# 注册自动修复审批路由
# ============================================================
from app.api.repair_router import router as repair_router
app.include_router(repair_router)


# ============================================================
# Prometheus 指标接口
# ============================================================
@app.get("/metrics", tags=["系统监控"])
async def metrics_endpoint(
    authorization: Optional[str] = Header(None),
    token: Optional[str] = Query(None, description="可选：METRICS_TOKEN"),
):
    """Prometheus 指标。若配置了 METRICS_TOKEN，需 Bearer 或 ?token=。"""
    from app.monitoring.metrics import get_metrics
    from fastapi.responses import PlainTextResponse

    expected = (settings.metrics_token or "").strip()
    if expected:
        provided = (token or "").strip()
        header = authorization or ""
        if header.lower().startswith("bearer "):
            provided = header[7:].strip()
        if provided != expected:
            raise HTTPException(status_code=401, detail="未授权")
    return PlainTextResponse(content=get_metrics(), media_type="text/plain; charset=utf-8")


# ============================================================
# 路由
# ============================================================
@app.get("/", tags=["静态文件"])
async def root():
    """返回前端主页面"""
    index_path = _static_dir / "index.html"
    if index_path.exists():
        return HTMLResponse(content=index_path.read_text(encoding="utf-8"))
    return HTMLResponse(content="<h1>AI 智能运维助手</h1><p>前端页面未找到。</p>")


@app.post("/api/chat", tags=["聊天接口"])
async def chat(
    req: ChatRequest,
    db: SASession = Depends(get_db),
    current_user: Optional[User] = Depends(get_chat_user),
):
    """Agent 对话接口 — 返回报告和执行轨迹"""
    # 如果用户已认证，处理会话
    conversation_id = req.conversation_id
    user_id = current_user.id if current_user else None
    if current_user is not None and conversation_id is None:
        # 查找已有会话或创建新会话
        conv = None
        sid = req.session_id
        if sid and sid != "default":
            try:
                sid_int = int(sid)
                conv = db.query(Conversation).filter(
                    Conversation.id == sid_int,
                    Conversation.user_id == current_user.id,
                ).first()
            except (ValueError, TypeError):
                conv = None
        if conv is None:
            conv = Conversation(
                user_id=current_user.id,
                title=req.message[:100],
            )
            db.add(conv)
            db.commit()
            db.refresh(conv)
        conversation_id = conv.id

    # 执行 Agent
    agent_start = time.monotonic()
    result = await run_in_threadpool(_run_agent, req.message, db, user_id, "", conversation_id)
    agent_duration = time.monotonic() - agent_start
    report = result["report"]
    trace = result.get("trace", [])

    # 如果已认证，保存消息和执行记录
    if current_user is not None and conversation_id is not None:
        _save_messages(db, conversation_id, req.message, report, trace)
        failed = _agent_failed(report)
        _save_agent_execution(
            db, current_user.id, conversation_id,
            status=_execution_status_for(report), duration=agent_duration,
            tools_called=len([t for t in trace if t.get("status") == "completed" and "调用" in t.get("step", "")]),
            error=report[:200] if failed else None,
        )

    return {
        "report": report,
        "session_id": req.session_id,
        "trace": trace,
        "conversation_id": conversation_id,
    }


@app.get("/api/server/status", tags=["系统监控"])
async def server_status(_: User = Depends(get_current_user)):
    """获取服务器实时状态（需要 JWT 认证）"""
    import app.tools.server_health as sh
    try:
        result = await run_in_threadpool(sh.server_health.invoke, {})
        return {
            "cpu": result.get("cpu", {}),
            "memory": result.get("memory", {}),
            "disks": result.get("disks", []),
        }
    except Exception as e:
        logger.error("获取服务器状态失败: %s", e)
        return {"error": str(e), "cpu": {}, "memory": {}, "disks": []}


@app.get("/health", tags=["系统管理"])
async def health():
    """服务健康检查。进程可用返回 200；数据库不可用返回 503。"""
    llm_ok = DeepSeekClient().is_configured

    db_ok = False
    servers_count = 0
    try:
        db_session = next(get_db())
        try:
            db_session.execute(sa_text("SELECT 1"))
            servers_count = db_session.query(ManagedServer).count()
            db_ok = True
        finally:
            db_session.close()
    except Exception as e:
        logger.warning("数据库健康检查失败: %s", e)

    monitoring_ok = False
    try:
        from app.monitoring.collector import _collector_thread
        monitoring_ok = _collector_thread is not None and _collector_thread.is_alive()
    except Exception:
        pass

    mcp_status: dict = {"enabled": False, "connected": False}
    try:
        from app.mcp.manager import mcp_manager
        mcp_status = mcp_manager.status()
    except Exception:
        pass

    payload = {
        "status": "healthy" if db_ok else "unhealthy",
        "version": APP_VERSION,
        "environment": settings.environment,
        "services": {
            "api": "ok",
            "llm": "ok" if llm_ok else "unconfigured",
            "database": "ok" if db_ok else "unavailable",
            "monitoring": "ok" if monitoring_ok else "inactive",
            "mcp": "ok" if mcp_status.get("connected") else (
                "disabled" if not mcp_status.get("enabled") else "disconnected"
            ),
        },
        "mcp": {
            "enabled": mcp_status.get("enabled"),
            "connected": mcp_status.get("connected"),
            "tool_count": mcp_status.get("tool_count", 0),
            "error": mcp_status.get("error"),
        },
        "agent": "ready" if llm_ok else "unconfigured",
        "servers_managed": servers_count,
    }
    return JSONResponse(status_code=200 if db_ok else 503, content=payload)


def _database_kind() -> str:
    url = (settings.database_url or "").strip().lower()
    if url.startswith("postgres"):
        return "postgresql"
    if url.startswith("sqlite"):
        return "sqlite"
    return "other"


def _build_system_status() -> dict:
    """管理员诊断快照。禁止包含 URL / secret / 路径。"""
    mcp_enabled = bool(settings.enable_mcp)
    mcp_tools = 0
    try:
        from app.mcp.manager import mcp_manager
        st = mcp_manager.status()
        mcp_tools = int(st.get("tool_count") or 0)
        if st.get("connected"):
            mcp_enabled = True
    except Exception:
        pass

    redis_ok = False
    try:
        from app.cache.redis import ping_redis
        redis_ok = bool(ping_redis())
    except Exception:
        redis_ok = False

    otel_ok = False
    try:
        from app.telemetry import setup as tel
        otel_ok = tel._tracer is not None
    except Exception:
        otel_ok = False

    return {
        "version": APP_VERSION,
        "environment": settings.environment,
        "database": _database_kind(),
        "llm_provider": settings.llm_provider,
        "mcp_enabled": mcp_enabled,
        "mcp_tools": mcp_tools,
        "redis_connected": redis_ok,
        "otel_enabled": otel_ok,
    }


@app.get("/api/system/status", tags=["系统管理"])
async def system_status(
    current_user: User = Depends(require_system_status_user),
):
    """开发/运维诊断。JWT 必填；production 需要 admin 或 devops。不返回密钥。"""
    return _build_system_status()


# ============================================================
# 会话管理 API
# ============================================================
class CreateConversationRequest(BaseModel):
    title: str = Field("新会话", max_length=200, description="会话标题")


@app.post("/api/conversations", tags=["会话管理"])
async def create_conversation(
    req: CreateConversationRequest,
    current_user: User = Depends(get_current_user),
    db: SASession = Depends(get_db),
):
    """创建新会话（需要 JWT 认证）"""
    conv = Conversation(
        user_id=current_user.id,
        title=req.title,
    )
    db.add(conv)
    db.commit()
    db.refresh(conv)
    logger.info("创建会话: id=%d user=%s", conv.id, current_user.username)
    return {
        "id": conv.id,
        "title": conv.title,
        "created_at": conv.created_at.isoformat() if conv.created_at else None,
    }


@app.get("/api/conversations", tags=["会话管理"])
async def list_conversations(
    current_user: User = Depends(get_current_user),
    db: SASession = Depends(get_db),
):
    """获取当前用户的所有会话列表（需要 JWT 认证）"""
    convs = db.query(Conversation).filter(
        Conversation.user_id == current_user.id
    ).order_by(Conversation.updated_at.desc()).all()

    counts = dict(
        db.query(Message.conversation_id, func.count(Message.id))
        .join(Conversation, Conversation.id == Message.conversation_id)
        .filter(Conversation.user_id == current_user.id)
        .group_by(Message.conversation_id)
        .all()
    )

    return [
        {
            "id": c.id,
            "title": c.title,
            "created_at": c.created_at.isoformat() if c.created_at else None,
            "updated_at": c.updated_at.isoformat() if c.updated_at else None,
            "message_count": int(counts.get(c.id, 0)),
        }
        for c in convs
    ]


@app.get("/api/conversations/{conversation_id}", tags=["会话管理"])
async def get_conversation(
    conversation_id: int,
    current_user: User = Depends(get_current_user),
    db: SASession = Depends(get_db),
):
    """获取会话完整聊天记录（需要 JWT 认证）"""
    conv = db.query(Conversation).filter(
        Conversation.id == conversation_id,
        Conversation.user_id == current_user.id,
    ).first()

    if conv is None:
        return JSONResponse(
            status_code=404,
            content={"detail": "会话不存在"},
        )

    messages = []
    for msg in conv.messages:
        messages.append({
            "id": msg.id,
            "role": msg.role,
            "content": msg.content,
            "trace": msg.trace_json,
            "created_at": msg.created_at.isoformat() if msg.created_at else None,
        })

    return {
        "id": conv.id,
        "title": conv.title,
        "created_at": conv.created_at.isoformat() if conv.created_at else None,
        "messages": messages,
    }


@app.delete("/api/conversations/{conversation_id}", tags=["会话管理"])
async def delete_conversation(
    conversation_id: int,
    current_user: User = Depends(get_current_user),
    db: SASession = Depends(get_db),
):
    """删除会话及其所有消息（需要 JWT 认证）"""
    conv = db.query(Conversation).filter(
        Conversation.id == conversation_id,
        Conversation.user_id == current_user.id,
    ).first()

    if conv is None:
        return JSONResponse(
            status_code=404,
            content={"detail": "会话不存在"},
        )

    db.delete(conv)
    db.commit()
    logger.info("删除会话: id=%d user=%s", conversation_id, current_user.username)
    return {"detail": "会话已删除"}


# ============================================================
# Agent 统计 API
# ============================================================
@app.get("/api/agent/stats", tags=["系统监控"])
async def agent_stats(
    db: SASession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """获取 Agent 运行统计数据（需要 JWT 认证）"""
    from app.tools.registry import get_all_tools, get_tool_stats

    total_convs = db.query(Conversation).filter(
        Conversation.user_id == current_user.id
    ).count()

    total_msgs = db.query(Message).join(Conversation).filter(
        Conversation.user_id == current_user.id
    ).count()

    total_servers = db.query(ManagedServer).filter(
        ManagedServer.user_id == current_user.id
    ).count()

    total_executions = db.query(AgentExecution).filter(
        AgentExecution.user_id == current_user.id
    ).count()

    success_executions = db.query(AgentExecution).filter(
        AgentExecution.user_id == current_user.id,
        AgentExecution.status == ExecutionStatus.success,
    ).count()

    tools = get_all_tools()
    tool_stats = get_tool_stats()

    return {
        "total_conversations": total_convs,
        "total_messages": total_msgs,
        "total_servers": total_servers,
        "total_executions": total_executions,
        "success_executions": success_executions,
        "tools_available": len(tools),
        "tool_stats": tool_stats,
    }


@app.get("/api/overview", tags=["系统监控"])
async def overview(
    db: SASession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Executive Dashboard 聚合：健康分 / SLA / 风险 / 趋势。

    健康分公式（文档化，非黑盒）：
    100 起分，LLM/DB 异常各 -15，每条 firing 告警 -8（上限 40），
    CPU>90 再 -10；下限 20。
    节省工时 = 成功执行次数 * 0.25h。
    """
    from datetime import datetime, timedelta
    from app.alert.manager import get_alerts
    import app.tools.server_health as sh

    stats_payload = await agent_stats(db=db, current_user=current_user)

    alerts = []
    try:
        alerts = get_alerts(limit=20) or []
    except Exception:
        alerts = []
    firing = [a for a in alerts if str(a.get("status", "")).lower() in ("firing", "open", "active")]

    llm_ok = DeepSeekClient().is_configured
    db_ok = True
    try:
        db.execute(sa_text("SELECT 1"))
    except Exception:
        db_ok = False

    resources = {"cpu": {"percent": 0, "cores": 0}, "memory": {"percent": 0, "total_gb": 0, "used_gb": 0}, "disks": []}
    try:
        resources = await run_in_threadpool(sh.server_health.invoke, {})
    except Exception:
        pass

    score = 100
    if not llm_ok:
        score -= 15
    if not db_ok:
        score -= 15
    score -= min(40, len(firing) * 8)
    cpu_pct = (resources.get("cpu") or {}).get("percent") or 0
    if cpu_pct > 90:
        score -= 10
    score = max(20, min(100, score))

    total_ex = stats_payload.get("total_executions") or 0
    success_ex = stats_payload.get("success_executions") or 0
    sla = round((success_ex / total_ex) * 100) if total_ex else 100
    since_24h = datetime.utcnow() - timedelta(hours=24)
    executions_24h = db.query(AgentExecution).filter(
        AgentExecution.user_id == current_user.id,
        AgentExecution.created_at >= since_24h,
    ).count()

    since = datetime.utcnow() - timedelta(days=7)
    runs = db.query(AgentExecution).filter(
        AgentExecution.user_id == current_user.id,
        AgentExecution.created_at >= since,
    ).all()
    buckets: dict[str, dict] = {}
    for e in runs:
        day = e.created_at.strftime("%m-%d") if e.created_at else "n/a"
        buckets.setdefault(day, {"day": day, "success": 0, "failed": 0})
        st = e.status.value if hasattr(e.status, "value") else str(e.status)
        if st == "success":
            buckets[day]["success"] += 1
        else:
            buckets[day]["failed"] += 1
    trend = list(buckets.values())

    repair_count = 0
    try:
        from app.monitoring.metrics import repair_success_total
        repair_count = int(repair_success_total._value.get())  # type: ignore[attr-defined]
    except Exception:
        repair_count = 0

    recent = db.query(AgentExecution).filter(
        AgentExecution.user_id == current_user.id
    ).order_by(AgentExecution.created_at.desc()).limit(8).all()

    monitoring_ok = False
    try:
        from app.monitoring.collector import _collector_thread
        monitoring_ok = _collector_thread is not None and _collector_thread.is_alive()
    except Exception:
        pass

    health = {
        "status": "healthy" if llm_ok and db_ok else "degraded",
        "version": APP_VERSION,
        "environment": settings.environment,
        "services": {
            "api": "ok",
            "llm": "ok" if llm_ok else "error",
            "database": "ok" if db_ok else "error",
            "monitoring": "ok" if monitoring_ok else "inactive",
        },
        "servers_managed": stats_payload.get("total_servers", 0),
    }

    return {
        "health_score": score,
        "sla_percent": sla,
        "risk_count": len(firing),
        "executions_24h": executions_24h,
        "repair_count": repair_count,
        "time_saved_hours": round(success_ex * 0.25, 1),
        "health": health,
        "resources": resources,
        "stats": stats_payload,
        "trend": trend,
        "incidents": alerts[:8],
        "recent_runs": [
            {
                "id": e.id,
                "status": e.status.value if hasattr(e.status, "value") else e.status,
                "duration": round(e.duration, 2),
                "tools_called": e.tools_called,
                "created_at": e.created_at.isoformat() if e.created_at else None,
            }
            for e in recent
        ],
        "formula": "health_score=100-15*llm/db-8*firing_alerts-10*cpu>90; time_saved=success*0.25h",
    }


# ============================================================
# Agent 执行记录 API
# ============================================================
@app.get("/api/agent/executions", tags=["系统监控"])
async def agent_executions(
    limit: int = Query(20, ge=1, le=100, description="返回条数"),
    current_user: User = Depends(get_current_user),
    db: SASession = Depends(get_db),
):
    """获取 Agent 执行记录（需要 JWT 认证）"""
    executions = db.query(AgentExecution).filter(
        AgentExecution.user_id == current_user.id
    ).order_by(AgentExecution.created_at.desc()).limit(limit).all()

    return [
        {
            "id": e.id,
            "conversation_id": e.conversation_id,
            "status": e.status.value if hasattr(e.status, 'value') else e.status,
            "duration": round(e.duration, 2),
            "tools_called": e.tools_called,
            "error_message": e.error_message,
            "created_at": e.created_at.isoformat() if e.created_at else None,
        }
        for e in executions
    ]


# ============================================================
# Kubernetes API
# ============================================================
@app.get("/api/k8s/pods", tags=["Kubernetes"])
async def k8s_get_pods(
    namespace: str = "",
    current_user: User = Depends(get_current_user),
):
    """获取 Kubernetes Pod 列表（需要 JWT 认证）"""
    from app.agent.k8s_tools import kubectl_get_pods
    return await run_in_threadpool(kubectl_get_pods.invoke, {"namespace": namespace})


@app.get("/api/k8s/nodes", tags=["Kubernetes"])
async def k8s_get_nodes(
    current_user: User = Depends(get_current_user),
):
    """获取 Kubernetes 节点列表（需要 JWT 认证）"""
    from app.agent.k8s_tools import kubectl_get_nodes
    return await run_in_threadpool(kubectl_get_nodes.invoke, {})


class DiagnosePodRequest(BaseModel):
    pod_name: str = Field(..., min_length=1, description="Pod 名称")
    namespace: str = Field("default", description="命名空间")


@app.post("/api/k8s/diagnose-pod", tags=["Kubernetes"])
async def k8s_diagnose_pod(
    req: DiagnosePodRequest,
    current_user: User = Depends(get_current_user),
):
    """Kubernetes Pod AI 故障诊断（需要 JWT 认证）"""
    from app.agent.k8s_tools import kubectl_describe_pod
    return await run_in_threadpool(
        kubectl_describe_pod.invoke,
        {"pod_name": req.pod_name, "namespace": req.namespace},
    )


# ============================================================
# 服务器管理 API
# ============================================================
class CreateServerRequest(BaseModel):
    """创建服务器请求"""
    name: str = Field(..., min_length=1, max_length=100, description="服务器别名")
    host: str = Field(..., min_length=1, max_length=255, description="服务器 IP 或域名")
    port: int = Field(22, ge=1, le=65535, description="SSH 端口")
    username: str = Field(..., min_length=1, max_length=100, description="SSH 登录用户名")
    auth_type: str = Field("password", description="认证类型: password 或 key")
    auth_credential: str = Field(..., min_length=1, max_length=16384, description="密码或密钥内容")
    description: str = Field("", max_length=500, description="服务器描述")


LOCAL_SERVER_ID = -1


def _localhost_server_dict() -> dict:
    """列表/详情共用的本机哨兵条目。"""
    import socket
    import platform

    return {
        "id": LOCAL_SERVER_ID,
        "name": "本机 (localhost)",
        "host": socket.gethostname() if socket.gethostname() else "127.0.0.1",
        "port": 0,
        "username": platform.node(),
        "auth_type": "local",
        "description": f"当前运行主机 · {platform.system()} {platform.release()}",
        "is_active": True,
        "created_at": None,
        "updated_at": None,
    }


def _reject_localhost_mutation():
    return JSONResponse(
        status_code=400,
        content={"detail": "本机条目不可修改或删除"},
    )


class UpdateServerRequest(BaseModel):
    """更新服务器请求"""
    name: Optional[str] = Field(None, max_length=100, description="服务器别名")
    host: Optional[str] = Field(None, max_length=255, description="服务器 IP 或域名")
    port: Optional[int] = Field(None, ge=1, le=65535, description="SSH 端口")
    username: Optional[str] = Field(None, max_length=100, description="SSH 登录用户名")
    auth_type: Optional[str] = Field(None, description="认证类型: password 或 key")
    auth_credential: Optional[str] = Field(None, max_length=16384, description="密码或密钥内容")
    description: Optional[str] = Field(None, max_length=500, description="服务器描述")
    is_active: Optional[bool] = Field(None, description="是否启用")


@app.post("/api/servers", tags=["服务器管理"])
async def create_server(
    req: CreateServerRequest,
    current_user: User = Depends(get_current_user),
    db: SASession = Depends(get_db),
):
    """注册新服务器（需要 JWT 认证）"""
    # 检查名称是否已存在
    existing = db.query(ManagedServer).filter(
        ManagedServer.name == req.name,
        ManagedServer.user_id == current_user.id,
    ).first()
    if existing:
        return JSONResponse(
            status_code=409,
            content={"detail": f"服务器名称 '{req.name}' 已存在"},
        )

    server = ManagedServer(
        user_id=current_user.id,
        name=req.name,
        host=req.host,
        port=req.port,
        username=req.username,
        auth_type=req.auth_type,
        auth_credential=encrypt_secret(req.auth_credential),
        description=req.description,
    )
    db.add(server)
    db.commit()
    db.refresh(server)
    logger.info("注册服务器: id=%d name=%s host=%s user=%s", server.id, server.name, server.host, current_user.username)
    return _server_to_dict(server)


@app.get("/api/servers", tags=["服务器管理"])
async def list_servers(
    current_user: User = Depends(get_current_user),
    db: SASession = Depends(get_db),
):
    """获取服务器列表 — 始终包含本机 + 当前用户注册的远程服务器。"""
    local = _localhost_server_dict()

    # 远程注册服务器
    servers = db.query(ManagedServer).filter(
        ManagedServer.user_id == current_user.id
    ).order_by(ManagedServer.created_at.desc()).all()

    payload = [local] + [_server_to_dict(s) for s in servers]
    return payload


@app.get("/api/servers/{server_id}", tags=["服务器管理"])
async def get_server(
    server_id: int,
    current_user: User = Depends(get_current_user),
    db: SASession = Depends(get_db),
):
    """获取指定服务器的详细信息（需要 JWT 认证）"""
    if server_id == LOCAL_SERVER_ID:
        return _localhost_server_dict()
    server = db.query(ManagedServer).filter(
        ManagedServer.id == server_id,
        ManagedServer.user_id == current_user.id,
    ).first()

    if server is None:
        return JSONResponse(
            status_code=404,
            content={"detail": "服务器不存在"},
        )

    return _server_to_dict(server)


@app.put("/api/servers/{server_id}", tags=["服务器管理"])
async def update_server(
    server_id: int,
    req: UpdateServerRequest,
    current_user: User = Depends(get_current_user),
    db: SASession = Depends(get_db),
):
    """更新服务器信息（需要 JWT 认证）"""
    if server_id == LOCAL_SERVER_ID:
        return _reject_localhost_mutation()
    server = db.query(ManagedServer).filter(
        ManagedServer.id == server_id,
        ManagedServer.user_id == current_user.id,
    ).first()

    if server is None:
        return JSONResponse(
            status_code=404,
            content={"detail": "服务器不存在"},
        )

    update_data = req.model_dump(exclude_unset=True)
    if update_data.get("auth_credential"):
        update_data["auth_credential"] = encrypt_secret(update_data["auth_credential"])
    for field, value in update_data.items():
        if value is not None:
            setattr(server, field, value)

    db.commit()
    db.refresh(server)
    logger.info("更新服务器: id=%d user=%s", server_id, current_user.username)
    return _server_to_dict(server)


@app.delete("/api/servers/{server_id}", tags=["服务器管理"])
async def delete_server(
    server_id: int,
    current_user: User = Depends(get_current_user),
    db: SASession = Depends(get_db),
):
    """删除服务器注册信息（需要 JWT 认证）"""
    if server_id == LOCAL_SERVER_ID:
        return _reject_localhost_mutation()
    server = db.query(ManagedServer).filter(
        ManagedServer.id == server_id,
        ManagedServer.user_id == current_user.id,
    ).first()

    if server is None:
        return JSONResponse(
            status_code=404,
            content={"detail": "服务器不存在"},
        )

    db.delete(server)
    db.commit()
    logger.info("删除服务器: id=%d name=%s user=%s", server_id, server.name, current_user.username)
    return {"detail": "服务器已删除"}


@app.post("/api/servers/{server_id}/test-connection", tags=["服务器管理"])
async def test_server_connection(
    server_id: int,
    current_user: User = Depends(get_current_user),
    db: SASession = Depends(get_db),
):
    """测试与远程服务器的 SSH 连接（需要 JWT 认证）"""
    if server_id == LOCAL_SERVER_ID:
        return _reject_localhost_mutation()
    server = db.query(ManagedServer).filter(
        ManagedServer.id == server_id,
        ManagedServer.user_id == current_user.id,
    ).first()

    if server is None:
        return JSONResponse(
            status_code=404,
            content={"detail": "服务器不存在"},
        )

    from app.tools.ssh_ops import _exec_ssh_command
    result = await run_in_threadpool(_exec_ssh_command, server.name, "uptime", 10)

    failure_marks = ("执行失败", "认证失败", "异常", "未找到", "连接错误", "失败")
    success = not any(mark in result for mark in failure_marks)

    return {
        "success": success,
        "server_name": server.name,
        "host": server.host,
        "output": result,
    }


def _server_to_dict(server: ManagedServer) -> dict:
    """将 ManagedServer 转换为字典（隐藏敏感字段）"""
    return {
        "id": server.id,
        "name": server.name,
        "host": server.host,
        "port": server.port,
        "username": server.username,
        "auth_type": server.auth_type,
        "description": server.description,
        "is_active": server.is_active,
        "created_at": server.created_at.isoformat() if server.created_at else None,
        "updated_at": server.updated_at.isoformat() if server.updated_at else None,
    }


# ============================================================
# 监控指标 API
# ============================================================
def _collect_monitoring_snapshot() -> dict:
    import psutil

    cpu_percent = psutil.cpu_percent(interval=0.3)
    cpu_info = {
        "percent": cpu_percent,
        "cores": psutil.cpu_count(),
    }
    mem = psutil.virtual_memory()
    memory_info = {
        "total_gb": round(mem.total / (1024**3), 1),
        "used_gb": round(mem.used / (1024**3), 1),
        "free_gb": round(mem.available / (1024**3), 1),
        "percent": mem.percent,
    }
    disks = []
    for p in psutil.disk_partitions():
        try:
            usage = psutil.disk_usage(p.mountpoint)
            disks.append({
                "mount": p.mountpoint,
                "total_gb": round(usage.total / (1024**3), 1),
                "used_gb": round(usage.used / (1024**3), 1),
                "free_gb": round(usage.free / (1024**3), 1),
                "percent": usage.percent,
            })
        except PermissionError:
            continue
    return {"cpu": cpu_info, "memory": memory_info, "disks": disks}


@app.get("/api/monitoring/current", tags=["系统监控"])
async def monitoring_current(
    current_user: User = Depends(get_current_user),
):
    """获取当前系统监控指标（需要 JWT 认证）"""
    return await run_in_threadpool(_collect_monitoring_snapshot)


# ============================================================
# 告警管理 API
# ============================================================
@app.get("/api/alerts", tags=["系统管理"])
async def list_alerts(
    status: Optional[str] = Query(None, description="过滤状态: firing/resolved"),
    limit: int = Query(50, ge=1, le=200, description="返回条数"),
    current_user: User = Depends(get_current_user),
):
    """获取告警列表（需要 JWT 认证）"""
    from app.alert.manager import get_alerts
    return get_alerts(status=status, limit=limit)


@app.post("/api/alerts/{alert_id}/resolve", tags=["系统管理"])
async def resolve_alert(
    alert_id: int,
    current_user: User = Depends(get_current_user),
):
    """关闭告警（需要 JWT 认证）"""
    from app.alert.manager import resolve_alert
    success = resolve_alert(alert_id)
    if not success:
        return JSONResponse(
            status_code=404,
            content={"detail": "告警不存在"},
        )
    return {"detail": "告警已关闭", "alert_id": alert_id}


# ============================================================
# SSE Streaming — Agent 实时执行轨迹
# ============================================================
class StreamChatRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=2000, description="用户消息")
    session_id: str = Field("default", description="会话 ID")
    conversation_id: Optional[int] = Field(None, description="会话 ID（关联数据库会话）")


@app.post("/api/chat/stream", tags=["聊天接口"])
async def chat_stream(
    req: StreamChatRequest,
    request: Request,
    db: SASession = Depends(get_db),
    current_user: Optional[User] = Depends(get_chat_user),
):
    """Agent 对话流式接口（SSE）— 实时推送 Agent 执行过程"""
    import uuid

    stream_id = str(uuid.uuid4())
    user_id = current_user.id if current_user else None
    conversation_id = req.conversation_id

    # 如果已认证，自动创建或获取会话
    if current_user is not None and conversation_id is None:
        conv = None
        sid = req.session_id
        if sid and sid != "default":
            try:
                sid_int = int(sid)
                conv = db.query(Conversation).filter(
                    Conversation.id == sid_int,
                    Conversation.user_id == current_user.id,
                ).first()
            except (ValueError, TypeError):
                conv = None
        if conv is None:
            conv = Conversation(
                user_id=current_user.id,
                title=req.message[:100],
            )
            db.add(conv)
            db.commit()
            db.refresh(conv)
        conversation_id = conv.id

    # 创建事件队列，边执行边把 RAG/Tool 事件推给前端
    stream_manager.create_stream(stream_id)
    agent_start = time.monotonic()

    def _run_agent_thread():
        from app.database.session import get_local_session
        from app.streaming.agent_stream import run_agent_with_streaming
        worker_db = get_local_session()
        try:
            return run_agent_with_streaming(
                message=req.message,
                stream_id=stream_id,
                db=worker_db,
                user_id=user_id,
                conversation_id=conversation_id,
            )
        finally:
            worker_db.close()

    async def _run_and_persist():
        try:
            result = await run_in_threadpool(_run_agent_thread)
            agent_duration = time.monotonic() - agent_start
            report = result.get("report", "")
            trace = result.get("trace", [])
            if conversation_id and current_user:
                try:
                    _save_messages(db, conversation_id, req.message, report, trace)
                    _save_agent_execution(
                        db, current_user.id, conversation_id,
                        status=_execution_status_for(report), duration=agent_duration,
                        tools_called=len([
                            t for t in trace
                            if t.get("status") == "completed" and "调用" in t.get("step", "")
                        ]),
                        error=(report[:200] if _agent_failed(report) else None),
                    )
                except Exception as e:
                    logger.warning("保存会话失败: %s", e)
            return result
        except Exception as e:
            logger.error("SSE stream error: %s", e)
            stream_manager.push_event(stream_id, StreamEvent.ERROR, message=str(e)[:200])
            return None

    async def event_generator():
        task = asyncio.create_task(_run_and_persist())
        try:
            async for chunk in stream_manager.event_generator(stream_id):
                yield chunk
        finally:
            try:
                await task
            except Exception:
                pass

    return EventSourceResponse(event_generator())


# ============================================================
# Agent Trace API
# ============================================================
@app.get("/api/agent/traces/{conversation_id}", tags=["系统监控"])
async def get_agent_traces(
    conversation_id: int,
    current_user: User = Depends(get_current_user),
    db: SASession = Depends(get_db),
):
    """获取 Agent 执行轨迹（类似 LangSmith Trace）"""
    # 验证会话属于当前用户
    conv = db.query(Conversation).filter(
        Conversation.id == conversation_id,
        Conversation.user_id == current_user.id,
    ).first()
    if not conv:
        return JSONResponse(status_code=404, content={"detail": "会话不存在或无权限"})

    traces = trace_service.get_traces(db, conversation_id)
    grouped = trace_service.get_conversation_trace_grouped(db, conversation_id)

    return {
        "conversation_id": conversation_id,
        "traces": traces,
        "steps": grouped.get("steps", []),
    }


# ============================================================
# WebSocket 实时 Agent Trace
# ============================================================
def _websocket_token(websocket: WebSocket) -> str:
    token = (websocket.query_params.get("token") or "").strip()
    if token:
        return token
    auth = websocket.headers.get("authorization") or websocket.headers.get("Authorization") or ""
    if auth.lower().startswith("bearer "):
        return auth[7:].strip()
    return ""


def _websocket_user(websocket: WebSocket, conversation_id: int) -> Optional[User]:
    """校验 JWT，并在会话已存在时确认归属。失败返回 None。"""
    token = _websocket_token(websocket)
    if not token:
        return None
    payload = decode_access_token(token)
    if not payload or payload.get("sub") is None:
        return None
    try:
        user_id = int(payload["sub"])
    except (TypeError, ValueError):
        return None

    db = get_local_session()
    try:
        user = db.query(User).filter(User.id == user_id).first()
        if user is None:
            return None
        if conversation_id:
            conv = db.query(Conversation).filter(Conversation.id == conversation_id).first()
            if conv is not None and conv.user_id != user.id:
                return None
        db.expunge(user)
        return user
    finally:
        db.close()


@app.websocket("/ws/chat/{conversation_id}")
async def websocket_chat_trace(
    websocket: WebSocket,
    conversation_id: int,
):
    """WebSocket 实时 Agent 执行轨迹推送（需要 JWT）"""
    user = _websocket_user(websocket, conversation_id)
    if user is None:
        await websocket.close(code=1008)
        return

    await websocket.accept()
    logger.info("WebSocket 连接: conversation_id=%d user=%s", conversation_id, user.username)

    try:
        while True:
            # 接收用户消息
            data = await websocket.receive_text()
            try:
                msg_data = json.loads(data)
                user_message = msg_data.get("message", data)
            except json.JSONDecodeError:
                user_message = data

            # 发送 agent_start
            await websocket.send_json({
                "type": "agent_start",
                "content": "开始分析用户需求...",
            })

            # 执行 Agent
            def _run_with_callbacks(msg: str = user_message):
                initial_state = {
                    "messages": [{"role": "user", "content": msg}],
                    "tool_calls": [],
                    "tool_results": [],
                    "final_report": "",
                    "trace": [],
                }
                try:
                    result = _agent_graph.invoke(initial_state)
                    return result
                except Exception:
                    logger.exception("WebSocket Agent 执行失败")
                    return {
                        "final_report": "Agent 执行失败，请稍后重试。",
                        "trace": [],
                    }

            result = await run_in_threadpool(_run_with_callbacks)
            trace = result.get("trace", [])
            report = result.get("final_report", "")

            # 推送 trace 步骤
            for step in trace:
                if not isinstance(step, dict):
                    continue
                step_name = step.get("step", "")
                step_type = "tool_call"
                if step_name == "分析用户需求":
                    step_type = "agent_start"
                elif step_name == "AI 生成报告":
                    step_type = "complete"

                await websocket.send_json({
                    "type": step_type,
                    "step": step_name,
                    "status": step.get("status", "completed"),
                    "tool": step.get("tool", ""),
                    "duration_ms": step.get("duration_ms", 0),
                })

            # 发送 complete
            await websocket.send_json({
                "type": "complete",
                "answer": report,
                "trace": trace,
            })

    except WebSocketDisconnect:
        logger.info("WebSocket 断开: conversation_id=%d", conversation_id)
    except Exception as e:
        logger.error("WebSocket 错误: %s", e)
        try:
            await websocket.send_json({
                "type": "error",
                "content": "内部错误",
            })
        except Exception:
            pass


# ============================================================
# 知识库 API
# ============================================================
class UploadKnowledgeRequest(BaseModel):
    title: str = Field(..., min_length=1, max_length=200, description="文档标题")
    content: str = Field(..., min_length=1, description="文档内容")

class SearchKnowledgeRequest(BaseModel):
    query: str = Field(..., min_length=1, max_length=500, description="搜索查询")
    top_k: int = Field(5, ge=1, le=20, description="返回结果数")


@app.post("/api/knowledge/upload", tags=["知识库"])
async def upload_knowledge(
    req: UploadKnowledgeRequest,
    current_user: User = Depends(get_current_user),
    db: SASession = Depends(get_db),
):
    """上传知识文档（需要 JWT 认证）"""
    from app.rag.service import rag_service
    doc_id = rag_service.ingest_text(
        title=req.title,
        content=req.content,
        db=db,
        user_id=current_user.id,
        source="manual",
    )
    logger.info("知识库上传: id=%d title=%s user=%s", doc_id, req.title, current_user.username)
    return {"id": doc_id, "title": req.title, "detail": "文档已上传并索引"}


@app.get("/api/knowledge", tags=["知识库"])
async def list_knowledge(
    current_user: User = Depends(get_current_user),
    db: SASession = Depends(get_db),
):
    """获取知识库文档列表（需要 JWT 认证）"""
    from app.database.models import KnowledgeDocument
    docs = db.query(KnowledgeDocument).filter(
        KnowledgeDocument.user_id == current_user.id
    ).order_by(KnowledgeDocument.created_at.desc()).all()

    return [
        {
            "id": d.id,
            "title": d.title,
            "source": d.source,
            "content_preview": d.content[:200],
            "created_at": d.created_at.isoformat() if d.created_at else None,
        }
        for d in docs
    ]


@app.delete("/api/knowledge/{knowledge_id}", tags=["知识库"])
async def delete_knowledge(
    knowledge_id: int,
    current_user: User = Depends(get_current_user),
    db: SASession = Depends(get_db),
):
    """删除知识文档和所有切片（需要 JWT 认证）"""
    from app.database.models import KnowledgeDocument
    doc = db.query(KnowledgeDocument).filter(
        KnowledgeDocument.id == knowledge_id,
        KnowledgeDocument.user_id == current_user.id,
    ).first()

    if doc is None:
        return JSONResponse(status_code=404, content={"detail": "文档不存在"})

    db.delete(doc)
    db.commit()
    logger.info("知识库删除: id=%d user=%s", knowledge_id, current_user.username)
    return {"detail": "文档已删除"}


@app.post("/api/knowledge/search", tags=["知识库"])
async def search_knowledge(
    req: SearchKnowledgeRequest,
    current_user: User = Depends(get_current_user),
    db: SASession = Depends(get_db),
):
    """搜索知识库（需要 JWT 认证）"""
    from app.rag.service import rag_service
    results = rag_service.search(
        query=req.query,
        db=db,
        top_k=req.top_k,
        user_id=current_user.id,
    )
    return results


# ============================================================
# 静态文件服务
# ============================================================
if _static_dir.exists():
    app.mount("/static", StaticFiles(directory=str(_static_dir)), name="static")
