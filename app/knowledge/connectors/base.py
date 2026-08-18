"""KnowledgeConnector 抽象。Connector 只负责鉴权、列举、拉取原文。"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Protocol, runtime_checkable


@dataclass
class RemoteDoc:
    external_id: str
    title: str
    updated_at: datetime | None = None
    checksum: str | None = None
    url: str | None = None
    parent_id: str | None = None
    obj_token: str | None = None
    obj_type: str = "docx"


@dataclass
class RemoteDocContent:
    external_id: str
    title: str
    content: str
    url: str | None = None
    checksum: str | None = None
    updated_at: datetime | None = None


@dataclass
class Page:
    items: list[RemoteDoc]
    cursor: str | None = None


@dataclass
class ConnectResult:
    ok: bool
    message: str = ""


@dataclass
class HealthResult:
    ok: bool
    message: str = ""


@dataclass
class SyncBatch:
    docs: list[RemoteDoc] = field(default_factory=list)
    truncated: bool = False


@runtime_checkable
class KnowledgeConnector(Protocol):
    type: str

    def connect(self, credentials: dict) -> ConnectResult: ...
    def health_check(self) -> HealthResult: ...
    def list_documents(self, cursor: str | None = None) -> Page: ...
    def fetch_document(self, external_id: str) -> RemoteDocContent: ...
    def sync(self, since: datetime | None = None) -> SyncBatch: ...
