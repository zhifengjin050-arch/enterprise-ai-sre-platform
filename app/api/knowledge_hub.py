"""企业知识连接中心 API。凭据加密存储，响应不含 secret。"""
from __future__ import annotations

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session as SASession

from app.auth.dependencies import get_current_user
from app.database.models import KnowledgeSource, SyncLog, SyncTask, User
from app.database.session import get_db
from app.knowledge.access import require_source_manager
from app.knowledge.connectors.registry import UPCOMING_TYPES, get_connector
from app.knowledge.crypto import decrypt_config, encrypt_config
from app.knowledge.pipeline import enqueue_sync, run_sync_task

router = APIRouter(prefix="/api/knowledge", tags=["知识连接中心"])


class CreateSourceRequest(BaseModel):
    type: str = Field(..., min_length=2, max_length=40)
    name: str = Field(..., min_length=1, max_length=200)
    space_id: str = Field("", max_length=200)
    app_id: str = Field("", max_length=200)
    app_secret: str = Field("", max_length=500)


def _source_public(src: KnowledgeSource) -> dict:
    return {
        "id": src.id,
        "organization_id": src.organization_id,
        "type": src.type,
        "name": src.name,
        "status": src.status,
        "last_sync_at": src.last_sync_at.isoformat() if src.last_sync_at else None,
        "last_error": src.last_error,
        "created_at": src.created_at.isoformat() if src.created_at else None,
        "upcoming": src.type in UPCOMING_TYPES,
    }


def _owned_source(db: SASession, source_id: int, user: User) -> KnowledgeSource:
    src = db.query(KnowledgeSource).filter(KnowledgeSource.id == source_id).first()
    if src is None or src.organization_id != user.organization_id:
        raise HTTPException(status_code=404, detail="知识源不存在")
    return src


@router.post("/sources")
async def create_source(
    req: CreateSourceRequest,
    current_user: User = Depends(require_source_manager),
    db: SASession = Depends(get_db),
):
    source_type = req.type.strip().lower()
    try:
        connector = get_connector(source_type, {
            "app_id": req.app_id,
            "app_secret": req.app_secret,
            "space_id": req.space_id,
        })
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    src = KnowledgeSource(
        organization_id=current_user.organization_id,
        type=source_type,
        name=req.name.strip(),
        status="disconnected",
        created_by=current_user.id,
        config_enc=encrypt_config({
            "app_id": req.app_id,
            "app_secret": req.app_secret,
            "space_id": req.space_id,
        }),
    )
    if source_type in UPCOMING_TYPES:
        src.status = "disconnected"
        src.last_error = f"{source_type} 即将推出"
    else:
        result = connector.connect({
            "app_id": req.app_id,
            "app_secret": req.app_secret,
            "space_id": req.space_id,
        })
        src.status = "connected" if result.ok else "error"
        src.last_error = None if result.ok else result.message
    db.add(src)
    db.commit()
    db.refresh(src)
    return _source_public(src)


@router.get("/sources")
async def list_sources(
    current_user: User = Depends(get_current_user),
    db: SASession = Depends(get_db),
):
    if not current_user.organization_id:
        return []
    rows = (
        db.query(KnowledgeSource)
        .filter(KnowledgeSource.organization_id == current_user.organization_id)
        .order_by(KnowledgeSource.created_at.desc())
        .all()
    )
    return [_source_public(s) for s in rows]


@router.get("/sources/{source_id}")
async def get_source(
    source_id: int,
    current_user: User = Depends(get_current_user),
    db: SASession = Depends(get_db),
):
    if not current_user.organization_id:
        raise HTTPException(status_code=404, detail="知识源不存在")
    return _source_public(_owned_source(db, source_id, current_user))


@router.delete("/sources/{source_id}")
async def delete_source(
    source_id: int,
    current_user: User = Depends(require_source_manager),
    db: SASession = Depends(get_db),
):
    src = _owned_source(db, source_id, current_user)
    from app.database.models import KnowledgeDocument
    docs = db.query(KnowledgeDocument).filter(KnowledgeDocument.source_id == src.id).all()
    for doc in docs:
        doc.status = "deleted"
        doc.source_id = None
        for chunk in list(doc.chunks):
            db.delete(chunk)
    db.delete(src)
    db.commit()
    return {"detail": "知识源已删除，关联文档已停用"}


@router.post("/sources/{source_id}/test")
async def test_source(
    source_id: int,
    current_user: User = Depends(require_source_manager),
    db: SASession = Depends(get_db),
):
    src = _owned_source(db, source_id, current_user)
    creds = decrypt_config(src.config_enc)
    connector = get_connector(src.type, creds)
    health = connector.health_check()
    src.status = "connected" if health.ok else "error"
    src.last_error = None if health.ok else health.message
    db.commit()
    return {"ok": health.ok, "message": health.message, "status": src.status}


@router.post("/sources/{source_id}/sync")
async def sync_source(
    source_id: int,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(require_source_manager),
    db: SASession = Depends(get_db),
):
    src = _owned_source(db, source_id, current_user)
    if src.type in UPCOMING_TYPES:
        raise HTTPException(status_code=400, detail=f"{src.type} 即将推出")
    task = enqueue_sync(db, src, trigger="manual")
    background_tasks.add_task(run_sync_task, task.id)
    return {
        "task_id": task.id,
        "status": task.status,
        "source_id": src.id,
    }


@router.get("/sync/tasks")
async def list_sync_tasks(
    source_id: int | None = None,
    current_user: User = Depends(get_current_user),
    db: SASession = Depends(get_db),
):
    if not current_user.organization_id:
        return []
    q = (
        db.query(SyncTask)
        .join(KnowledgeSource, SyncTask.source_id == KnowledgeSource.id)
        .filter(KnowledgeSource.organization_id == current_user.organization_id)
    )
    if source_id is not None:
        q = q.filter(SyncTask.source_id == source_id)
    rows = q.order_by(SyncTask.created_at.desc()).limit(50).all()
    return [
        {
            "id": t.id,
            "source_id": t.source_id,
            "trigger": t.trigger,
            "status": t.status,
            "stats": t.stats_json or {},
            "started_at": t.started_at.isoformat() if t.started_at else None,
            "finished_at": t.finished_at.isoformat() if t.finished_at else None,
            "created_at": t.created_at.isoformat() if t.created_at else None,
        }
        for t in rows
    ]


@router.get("/sync/tasks/{task_id}")
async def get_sync_task(
    task_id: int,
    current_user: User = Depends(get_current_user),
    db: SASession = Depends(get_db),
):
    task = (
        db.query(SyncTask)
        .join(KnowledgeSource, SyncTask.source_id == KnowledgeSource.id)
        .filter(
            SyncTask.id == task_id,
            KnowledgeSource.organization_id == current_user.organization_id,
        )
        .first()
    )
    if task is None:
        raise HTTPException(status_code=404, detail="同步任务不存在")
    return {
        "id": task.id,
        "source_id": task.source_id,
        "trigger": task.trigger,
        "status": task.status,
        "stats": task.stats_json or {},
        "started_at": task.started_at.isoformat() if task.started_at else None,
        "finished_at": task.finished_at.isoformat() if task.finished_at else None,
    }


@router.get("/sync/tasks/{task_id}/logs")
async def get_sync_task_logs(
    task_id: int,
    current_user: User = Depends(get_current_user),
    db: SASession = Depends(get_db),
):
    task = (
        db.query(SyncTask)
        .join(KnowledgeSource, SyncTask.source_id == KnowledgeSource.id)
        .filter(
            SyncTask.id == task_id,
            KnowledgeSource.organization_id == current_user.organization_id,
        )
        .first()
    )
    if task is None:
        raise HTTPException(status_code=404, detail="同步任务不存在")
    logs = (
        db.query(SyncLog)
        .filter(SyncLog.task_id == task.id)
        .order_by(SyncLog.created_at.asc())
        .all()
    )
    return [
        {
            "id": log.id,
            "level": log.level,
            "external_id": log.external_id,
            "message": log.message,
            "created_at": log.created_at.isoformat() if log.created_at else None,
        }
        for log in logs
    ]
