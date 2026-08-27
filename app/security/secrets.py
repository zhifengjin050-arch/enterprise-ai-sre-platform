"""敏感字段加解密。

与知识源 Hub 共用同一套 Fernet 密钥（由 JWT_SECRET 派生）。
存盘格式：``enc:v1:`` + Fernet token。无前缀视为历史明文，读取时原样返回。
"""
from __future__ import annotations

import base64
import hashlib
import logging

from cryptography.fernet import Fernet, InvalidToken

from app.config import settings

logger = logging.getLogger(__name__)

SECRET_PREFIX = "enc:v1:"


def get_fernet() -> Fernet:
    digest = hashlib.sha256(settings.jwt_secret.encode("utf-8")).digest()
    key = base64.urlsafe_b64encode(digest)
    return Fernet(key)


def is_encrypted_secret(value: str | None) -> bool:
    return bool(value) and value.startswith(SECRET_PREFIX)


def encrypt_secret(plain: str | None) -> str | None:
    """加密明文。空值原样返回；已加密则不再套一层。"""
    if plain is None or plain == "":
        return plain
    if is_encrypted_secret(plain):
        return plain
    token = get_fernet().encrypt(plain.encode("utf-8")).decode("utf-8")
    return f"{SECRET_PREFIX}{token}"


def decrypt_secret(value: str | None) -> str | None:
    """解密。无前缀视为历史明文，保持兼容。"""
    if value is None or value == "":
        return value
    if not is_encrypted_secret(value):
        return value
    token = value[len(SECRET_PREFIX) :]
    try:
        return get_fernet().decrypt(token.encode("utf-8")).decode("utf-8")
    except (InvalidToken, TypeError, ValueError) as exc:
        logger.error("凭据解密失败: %s", type(exc).__name__)
        raise ValueError("凭据解密失败，请重新保存该服务器的认证信息") from exc
