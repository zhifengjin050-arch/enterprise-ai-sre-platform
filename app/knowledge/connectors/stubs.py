"""非飞书源占位实现。前端显示「即将推出」。"""
from __future__ import annotations

from datetime import datetime

from app.knowledge.connectors.base import (
    ConnectResult,
    HealthResult,
    Page,
    RemoteDocContent,
    SyncBatch,
)


class _UpcomingConnector:
    type = "upcoming"

    def __init__(self, credentials: dict | None = None, label: str = "该知识源"):
        self.credentials = credentials or {}
        self.label = label

    def connect(self, credentials: dict) -> ConnectResult:
        return ConnectResult(ok=False, message=f"{self.label}即将推出")

    def health_check(self) -> HealthResult:
        return HealthResult(ok=False, message=f"{self.label}即将推出")

    def list_documents(self, cursor: str | None = None) -> Page:
        raise NotImplementedError(f"{self.label}即将推出")

    def fetch_document(self, external_id: str) -> RemoteDocContent:
        raise NotImplementedError(f"{self.label}即将推出")

    def sync(self, since: datetime | None = None) -> SyncBatch:
        raise NotImplementedError(f"{self.label}即将推出")


class YuqueConnector(_UpcomingConnector):
    type = "yuque"

    def __init__(self, credentials: dict | None = None):
        super().__init__(credentials, "语雀知识库")


class GitLabConnector(_UpcomingConnector):
    type = "gitlab"

    def __init__(self, credentials: dict | None = None):
        super().__init__(credentials, "GitLab Wiki")


class ConfluenceConnector(_UpcomingConnector):
    type = "confluence"

    def __init__(self, credentials: dict | None = None):
        super().__init__(credentials, "Confluence")
