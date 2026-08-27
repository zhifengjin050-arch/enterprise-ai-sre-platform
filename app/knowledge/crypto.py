"""知识源凭据加密。API 永不回传明文。"""
from __future__ import annotations

import json
from typing import Any

from cryptography.fernet import InvalidToken

from app.security.secrets import get_fernet


def encrypt_config(payload: dict[str, Any]) -> str:
    raw = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    return get_fernet().encrypt(raw).decode("utf-8")


def decrypt_config(token: str | None) -> dict[str, Any]:
    if not token:
        return {}
    try:
        raw = get_fernet().decrypt(token.encode("utf-8"))
        data = json.loads(raw.decode("utf-8"))
        return data if isinstance(data, dict) else {}
    except (InvalidToken, json.JSONDecodeError, TypeError, ValueError):
        return {}
