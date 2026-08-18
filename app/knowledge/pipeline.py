"""知识同步 Pipeline：list → fetch → ingest_text。不在 Connector 内做 embedding。"""
from __future__ import annotations

import datetime
import hashlib
import logging
from typing import Any

from app.database.models import KnowledgeDocument, KnowledgeSource, SyncLog, SyncTask
from app.database.session import get_local_session
from app.knowledge.connectors.feishu import MAX_DOCS_PER_SOURCE
from app.knowledge.connectors.registry import get_connector
from app.knowledge.crypto import decrypt_config
from app.rag.service import rag_service

logger = logging.getLogger("knowledge.pipeline")


def _log(db, task_id: int, level: str, message: str, external_id: str | None = None) -> None:
    db.add(SyncLog(task_id=task_id, level=level, message=message[:2000], external_id=external_id))
    db.flush()


def enqueue_sync(db, source: KnowledgeSource, trigger: str = "manual") -> SyncTask:
    task = SyncTask(source_id=source.id, trigger=trigger, status="queued")
    db.add(task)
    source.status = "syncing"
    source.last_error = None
    db.commit()
    db.refresh(task)
    return task


def run_sync_task(task_id: int) -> dict[str, Any]:
    db = get_local_session()
    stats = {"fetched": 0, "upserted": 0, "skipped": 0, "deleted": 0, "failed": 0}
    try:
        task = db.query(SyncTask).filter(SyncTask.id == task_id).first()
        if task is None:
            return {"error": "task not found"}
        source = db.query(KnowledgeSource).filter(KnowledgeSource.id == task.source_id).first()
        if source is None:
            task.status = "failed"
            db.commit()
            return {"error": "source not found"}

        task.status = "running"
        task.started_at = datetime.datetime.utcnow()
        db.commit()

        creds = decrypt_config(source.config_enc)
        connector = get_connector(source.type, creds)
        health = connector.health_check()
        if not health.ok:
            task.status = "failed"
            task.finished_at = datetime.datetime.utcnow()
            task.stats_json = stats
            source.status = "error"
            source.last_error = health.message
            _log(db, task.id, "error", f"健康检查失败: {health.message}")
            db.commit()
            return {"status": "failed", "stats": stats, "error": health.message}

        try:
            batch = connector.sync(since=source.last_sync_at)
        except NotImplementedError as exc:
            task.status = "failed"
            task.finished_at = datetime.datetime.utcnow()
            source.status = "error"
            source.last_error = str(exc)
            _log(db, task.id, "error", str(exc))
            db.commit()
            return {"status": "failed", "error": str(exc)}

        if batch.truncated:
            _log(db, task.id, "warning", f"已达单源文档上限 {MAX_DOCS_PER_SOURCE}，其余节点未同步")

        seen_ids: set[str] = set()
        created_by = source.created_by or 0
        for remote in batch.docs:
            seen_ids.add(remote.external_id)
            stats["fetched"] += 1
            existing = (
                db.query(KnowledgeDocument)
                .filter(
                    KnowledgeDocument.source_id == source.id,
                    KnowledgeDocument.external_id == remote.external_id,
                )
                .first()
            )
            try:
                content_obj = connector.fetch_document(remote.external_id)
            except Exception as exc:
                stats["failed"] += 1
                _log(db, task.id, "warning", f"拉取失败: {exc}", remote.external_id)
                continue

            checksum = content_obj.checksum or hashlib.sha256(
                content_obj.content.encode("utf-8")
            ).hexdigest()
            if existing and existing.checksum == checksum and existing.status == "active":
                stats["skipped"] += 1
                continue
            if not content_obj.content.strip():
                stats["skipped"] += 1
                _log(db, task.id, "warning", "正文为空，跳过入库", remote.external_id)
                continue
            owner_id = (existing.user_id if existing else None) or source.created_by
            if not owner_id:
                stats["failed"] += 1
                _log(db, task.id, "warning", "缺少创建者，无法入库", remote.external_id)
                continue
            try:
                rag_service.ingest_text(
                    title=content_obj.title or remote.title,
                    content=content_obj.content,
                    db=db,
                    user_id=owner_id,
                    source=source.type,
                    organization_id=source.organization_id,
                    source_id=source.id,
                    external_id=remote.external_id,
                    external_url=content_obj.url or remote.url,
                    checksum=checksum,
                    require_embedding=True,
                )
                stats["upserted"] += 1
            except Exception as exc:
                db.rollback()
                stats["failed"] += 1
                _log(db, task.id, "warning", f"索引失败（未使用 fallback）: {exc}", remote.external_id)

        local_docs = (
            db.query(KnowledgeDocument)
            .filter(
                KnowledgeDocument.source_id == source.id,
                KnowledgeDocument.status == "active",
            )
            .all()
        )
        for doc in local_docs:
            if doc.external_id and doc.external_id not in seen_ids:
                for chunk in list(doc.chunks):
                    db.delete(chunk)
                doc.status = "deleted"
                stats["deleted"] += 1
                _log(db, task.id, "info", "远端已删除，本地标记 deleted", doc.external_id)

        source.last_sync_at = datetime.datetime.utcnow()
        source.status = "connected" if stats["failed"] == 0 else "error"
        source.last_error = None if stats["failed"] == 0 else f"{stats['failed']} 篇文档同步失败"
        task.status = "success" if stats["failed"] == 0 else "failed"
        task.finished_at = datetime.datetime.utcnow()
        task.stats_json = stats
        _log(db, task.id, "info", f"同步完成 {stats}")
        db.commit()
        return {"status": task.status, "stats": stats}
    except Exception as exc:
        logger.exception("同步任务失败 task_id=%s", task_id)
        try:
            task = db.query(SyncTask).filter(SyncTask.id == task_id).first()
            if task:
                task.status = "failed"
                task.finished_at = datetime.datetime.utcnow()
                task.stats_json = stats
                source = db.query(KnowledgeSource).filter(KnowledgeSource.id == task.source_id).first()
                if source:
                    source.status = "error"
                    source.last_error = str(exc)[:500]
                _log(db, task.id, "error", str(exc)[:500])
                db.commit()
        except Exception:
            db.rollback()
        return {"status": "failed", "error": str(exc), "stats": stats}
    finally:
        db.close()
