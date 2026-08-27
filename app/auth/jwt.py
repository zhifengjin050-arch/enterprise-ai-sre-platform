"""JWT Token 生成与验证

使用 pyjwt (PyJWT) 库进行 HS256 签名。
"""

import time
import logging
from typing import Optional

import jwt as pyjwt

from app.config import settings

logger = logging.getLogger(__name__)

# JWT 配置
JWT_SECRET = settings.jwt_secret
JWT_ALGORITHM = "HS256"
JWT_EXPIRE_MINUTES = settings.jwt_expire_minutes


def create_access_token(data: dict, expires_delta: Optional[int] = None) -> str:
    """创建 JWT Access Token

    Args:
        data: 要编码的数据（必须包含 'sub' 字段，即用户 ID）
        expires_delta: 过期时间（分钟），默认使用配置值

    Returns:
        JWT 字符串
    """
    to_encode = data.copy()
    expire = time.time() + (expires_delta or JWT_EXPIRE_MINUTES) * 60
    to_encode.update({"exp": expire, "iat": time.time()})
    token = pyjwt.encode(to_encode, JWT_SECRET, algorithm=JWT_ALGORITHM)
    return token


def decode_access_token(token: str) -> Optional[dict]:
    """解码并验证 JWT Token

    Args:
        token: JWT 字符串

    Returns:
        解码后的 payload 字典，验证失败返回 None
    """
    try:
        payload = pyjwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        return payload
    except pyjwt.ExpiredSignatureError:
        logger.warning("JWT token 已过期")
        return None
    except pyjwt.InvalidTokenError as e:
        logger.warning("JWT token 无效: %s", e)
        return None
