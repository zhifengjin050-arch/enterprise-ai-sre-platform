"""Background Agent execution using RQ"""
from __future__ import annotations
import logging
from redis import Redis
from rq import Queue
from rq.job import Job
from rq.job import JobStatus as RQJobStatus

from app.config import settings

logger = logging.getLogger("tasks")

_redis_conn = None
_agent_queue = None


def _get_queue():
    global _redis_conn, _agent_queue
    if _agent_queue is None:
        _redis_conn = Redis.from_url(settings.redis_url or "redis://localhost:6379/0")
        _agent_queue = Queue("agent", connection=_redis_conn, default_timeout=600)
    return _agent_queue


def enqueue_agent(message: str, stream_id: str = "", user_id: int = None,
                  conversation_id: int = None) -> str:
    """Enqueue Agent execution and return job ID"""
    queue = _get_queue()
    job = queue.enqueue(
        "app.tasks.agent_task._execute_agent",
        args=(message, stream_id, user_id, conversation_id),
        job_timeout=600,
        result_ttl=3600,
    )
    logger.info("Agent task enqueued: job=%s message=%s", job.id, message[:50])
    return job.id


def get_job_status(job_id: str) -> dict:
    """Get job status and result"""
    try:
        job = Job.fetch(job_id, connection=_redis_conn)
        status = "queued" if job.is_queued else \
                 "started" if job.is_started else \
                 "finished" if job.is_finished else \
                 "failed" if job.is_failed else "unknown"
        result = None
        if job.is_finished:
            result = job.result
        error = None
        if job.is_failed:
            error = str(job.exc_info)[:500] if job.exc_info else "Unknown error"
        return {
            "job_id": job_id,
            "status": status,
            "result": result,
            "error": error,
            "enqueued_at": str(job.enqueued_at) if job.enqueued_at else None,
            "started_at": str(job.started_at) if job.started_at else None,
            "ended_at": str(job.ended_at) if job.ended_at else None,
        }
    except Exception as e:
        return {"job_id": job_id, "status": "not_found", "error": str(e)}


def _execute_agent(message: str, stream_id: str = "", user_id: int = None,
                   conversation_id: int = None) -> dict:
    """Execute agent in background worker"""
    from app.agent.graph import create_agent_graph
    from app.database.session import get_local_session
    import time

    graph = create_agent_graph()
    db = get_local_session() if user_id else None

    try:
        initial_state = {
            "messages": [{"role": "user", "content": message}],
            "tool_calls": [],
            "tool_results": [],
            "final_report": "",
            "trace": [],
            "_db": db,
            "_user_id": user_id,
            "_stream_id": stream_id,
        }
        start = time.monotonic()
        result = graph.invoke(initial_state)
        duration = time.monotonic() - start

        return {
            "report": result.get("final_report", ""),
            "trace": result.get("trace", []),
            "duration": round(duration, 2),
        }
    except Exception as e:
        logger.exception("后台 Agent 任务失败")
        return {
            "report": "Agent 执行失败，请稍后重试。",
            "trace": [],
            "duration": 0,
            "error": str(e)[:200],
        }
    finally:
        if db:
            db.close()


def rq_health_check() -> str:
    """RQ worker 健康探测任务（验收用，无业务副作用）。"""
    return "ok"


class JobStatus:
    """Job status constants matching rq.job.JobStatus"""
    QUEUED = RQJobStatus.QUEUED
    STARTED = RQJobStatus.STARTED
    FINISHED = RQJobStatus.FINISHED
    FAILED = RQJobStatus.FAILED
    DEFERRED = RQJobStatus.DEFERRED
    SCHEDULED = RQJobStatus.SCHEDULED
    CANCELLED = "cancelled"
