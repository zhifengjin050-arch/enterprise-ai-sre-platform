"""知识源凭据加密。API 永不回传明文。"""
from __future__ import annotations

import base64
import hashlib
import json
from typing import Any

from cryptography.fernet import Fernet, InvalidToken

from app.config import settings


def _fernet() -> Fernet:
    digest = hashlib.sha256(settings.jwt_secret.encode("utf-8")).digest()
    key = base64.urlsafe_b64encode(digest)
    return Fernet(key)


def encrypt_config(payload: dict[str, Any]) -> str:
    raw = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    return _fernet().encrypt(raw).decode("utf-8")


def decrypt_config(token: str | None) -> dict[str, Any]:
    if not token:
        return {}
    try:
        raw = _fernet().decrypt(token.encode("utf-8"))
        data = json.loads(raw.decode("utf-8"))
        return data if isinstance(data, dict) else {}
    except (InvalidToken, json.JSONDecodeError, TypeError, ValueError):
        return {}
