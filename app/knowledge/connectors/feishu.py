"""飞书 Wiki Connector（企业自建应用 tenant_access_token）。"""
from __future__ import annotations

import hashlib
import logging
import time
from datetime import datetime, timezone
from typing import Any, Optional

import httpx

from app.knowledge.connectors.base import (
    ConnectResult,
    HealthResult,
    Page,
    RemoteDoc,
    RemoteDocContent,
    SyncBatch,
)

logger = logging.getLogger("knowledge.feishu")

FEISHU_BASE = "https://open.feishu.cn/open-apis"
MAX_DOCS_PER_SOURCE = 500
SUPPORTED_OBJ_TYPES = {"docx", "doc"}


def _parse_ts(value: Any) -> datetime | None:
    if value is None or value == "":
        return None
    try:
        if isinstance(value, (int, float)) or (isinstance(value, str) and value.isdigit()):
            ts = int(value)
            if ts > 10_000_000_000:
                ts = ts / 1000
            return datetime.fromtimestamp(ts, tz=timezone.utc).replace(tzinfo=None)
        text = str(value).replace("Z", "+00:00")
        return datetime.fromisoformat(text).replace(tzinfo=None)
    except (TypeError, ValueError, OSError):
        return None


class FeishuConnector:
    type = "feishu"

    def __init__(self, credentials: dict | None = None, http_client: httpx.Client | None = None):
        creds = credentials or {}
        self.app_id = (creds.get("app_id") or "").strip()
        self.app_secret = (creds.get("app_secret") or "").strip()
        self.space_id = (creds.get("space_id") or "").strip()
        self._http = http_client
        self._owns_client = http_client is None
        self._token: str | None = None
        self._token_expire_at = 0.0
        self._node_index: dict[str, RemoteDoc] = {}

    def _client(self) -> httpx.Client:
        if self._http is None:
            self._http = httpx.Client(timeout=30.0)
        return self._http

    def close(self) -> None:
        if self._owns_client and self._http is not None:
            self._http.close()
            self._http = None

    def connect(self, credentials: dict) -> ConnectResult:
        self.app_id = (credentials.get("app_id") or "").strip()
        self.app_secret = (credentials.get("app_secret") or "").strip()
        self.space_id = (credentials.get("space_id") or "").strip()
        health = self.health_check()
        return ConnectResult(ok=health.ok, message=health.message)

    def health_check(self) -> HealthResult:
        if not self.app_id or not self.app_secret:
            return HealthResult(ok=False, message="缺少 App ID 或 App Secret")
        if not self.space_id:
            return HealthResult(ok=False, message="缺少 Wiki space_id")
        try:
            self._ensure_token()
            data = self._request("GET", f"/wiki/v2/spaces/{self.space_id}")
            name = (data.get("space") or {}).get("name") or self.space_id
            return HealthResult(ok=True, message=f"已连接 Wiki 空间：{name}")
        except Exception as exc:
            return HealthResult(ok=False, message=str(exc)[:300])

    def list_documents(self, cursor: str | None = None) -> Page:
        docs, _truncated = self._walk_nodes(limit=MAX_DOCS_PER_SOURCE)
        if cursor:
            start = int(cursor)
            page_items = docs[start:start + 50]
            nxt = str(start + 50) if start + 50 < len(docs) else None
            return Page(items=page_items, cursor=nxt)
        return Page(items=docs[:50], cursor="50" if len(docs) > 50 else None)

    def fetch_document(self, external_id: str) -> RemoteDocContent:
        node = self._node_index.get(external_id)
        if node is None:
            docs, _ = self._walk_nodes(limit=MAX_DOCS_PER_SOURCE)
            for item in docs:
                self._node_index[item.external_id] = item
            node = self._node_index.get(external_id)
        if node is None:
            raise ValueError(f"未找到 Wiki 节点: {external_id}")
        obj_token = node.obj_token or external_id
        data = self._request("GET", f"/docx/v1/documents/{obj_token}/raw_content")
        content = (data.get("content") or "").strip()
        checksum = hashlib.sha256(content.encode("utf-8")).hexdigest()
        return RemoteDocContent(
            external_id=external_id,
            title=node.title,
            content=content,
            url=node.url,
            checksum=checksum,
            updated_at=node.updated_at,
        )

    def sync(self, since: datetime | None = None) -> SyncBatch:
        docs, truncated = self._walk_nodes(limit=MAX_DOCS_PER_SOURCE)
        if since:
            filtered = []
            for doc in docs:
                if doc.updated_at is None or doc.updated_at >= since:
                    filtered.append(doc)
            docs = filtered
        return SyncBatch(docs=docs, truncated=truncated)

    def _ensure_token(self) -> str:
        now = time.time()
        if self._token and now < self._token_expire_at - 60:
            return self._token
        client = self._client()
        resp = client.post(
            f"{FEISHU_BASE}/auth/v3/tenant_access_token/internal",
            json={"app_id": self.app_id, "app_secret": self.app_secret},
        )
        payload = resp.json() if resp.content else {}
        if resp.status_code >= 400 or payload.get("code") not in (0, None):
            msg = payload.get("msg") or payload.get("message") or resp.text[:200]
            raise RuntimeError(f"获取 tenant_access_token 失败: {msg}")
        token = payload.get("tenant_access_token")
        if not token:
            raise RuntimeError("飞书未返回 tenant_access_token，请检查应用权限")
        expire = int(payload.get("expire") or 7200)
        self._token = token
        self._token_expire_at = now + expire
        return token

    def _request(self, method: str, path: str, params: Optional[dict] = None) -> dict:
        client = self._client()
        delay = 1.0
        last_error = "飞书 API 调用失败"
        for attempt in range(5):
            token = self._ensure_token()
            resp = client.request(
                method,
                f"{FEISHU_BASE}{path}",
                headers={"Authorization": f"Bearer {token}"},
                params=params,
            )
            if resp.status_code in (429, 500, 502, 503, 504):
                last_error = f"飞书 HTTP {resp.status_code}"
                time.sleep(delay)
                delay = min(delay * 2, 16)
                continue
            payload = resp.json() if resp.content else {}
            code = payload.get("code")
            if code not in (0, None):
                last_error = payload.get("msg") or payload.get("message") or str(code)
                if code in (99991400, 99991401) or "rate" in str(last_error).lower():
                    time.sleep(delay)
                    delay = min(delay * 2, 16)
                    continue
                raise RuntimeError(f"飞书 API 错误: {last_error}")
            if resp.status_code >= 400:
                raise RuntimeError(f"飞书 HTTP {resp.status_code}: {resp.text[:200]}")
            return payload.get("data") or {}
        raise RuntimeError(f"{last_error}（已重试）")

    def _walk_nodes(self, limit: int) -> tuple[list[RemoteDoc], bool]:
        collected: list[RemoteDoc] = []
        truncated = False
        queue: list[str | None] = [None]
        seen_parents: set[str] = set()

        while queue:
            parent = queue.pop(0)
            parent_key = parent or ""
            if parent_key in seen_parents:
                continue
            seen_parents.add(parent_key)
            page_token = None
            while True:
                params: dict[str, Any] = {"page_size": 50}
                if parent:
                    params["parent_node_token"] = parent
                if page_token:
                    params["page_token"] = page_token
                data = self._request("GET", f"/wiki/v2/spaces/{self.space_id}/nodes", params=params)
                items = data.get("items") or []
                for node in items:
                    obj_type = str(node.get("obj_type") or "")
                    node_token = node.get("node_token") or node.get("obj_token")
                    if not node_token:
                        continue
                    if node.get("has_child"):
                        queue.append(node_token)
                    if obj_type not in SUPPORTED_OBJ_TYPES:
                        continue
                    if len(collected) >= limit:
                        truncated = True
                        break
                    doc = RemoteDoc(
                        external_id=str(node_token),
                        title=node.get("title") or "未命名文档",
                        updated_at=_parse_ts(node.get("obj_edit_time") or node.get("node_edit_time")),
                        url=f"https://feishu.cn/wiki/{node_token}",
                        parent_id=node.get("parent_node_token"),
                        obj_token=str(node.get("obj_token") or node_token),
                        obj_type=obj_type,
                    )
                    collected.append(doc)
                    self._node_index[doc.external_id] = doc
                if truncated:
                    break
                if not data.get("has_more"):
                    break
                page_token = data.get("page_token")
                if not page_token:
                    break
            if truncated:
                break
        return collected, truncated
