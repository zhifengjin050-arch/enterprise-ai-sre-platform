"""Connector 注册表。"""
from __future__ import annotations

from typing import Any

from app.knowledge.connectors.feishu import FeishuConnector
from app.knowledge.connectors.stubs import ConfluenceConnector, GitLabConnector, YuqueConnector

_CONNECTORS: dict[str, type] = {
    "feishu": FeishuConnector,
    "yuque": YuqueConnector,
    "gitlab": GitLabConnector,
    "confluence": ConfluenceConnector,
}

UPCOMING_TYPES = ("yuque", "gitlab", "confluence")


def get_connector(source_type: str, credentials: dict | None = None, **kwargs: Any):
    cls = _CONNECTORS.get(source_type)
    if cls is None:
        raise ValueError(f"不支持的知识源类型: {source_type}")
    return cls(credentials, **kwargs) if source_type == "feishu" else cls(credentials)


def register_connector(source_type: str, cls: type) -> None:
    _CONNECTORS[source_type] = cls


def supported_types() -> list[str]:
    return list(_CONNECTORS.keys())
