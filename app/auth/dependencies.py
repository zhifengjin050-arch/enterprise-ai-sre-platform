"""FastAPI 依赖注入 — 认证与权限

- get_current_user: 从 JWT Token 解析当前用户
- require_role: 角色权限校验装饰器
"""

import logging
from typing import Optional
from functools import wraps

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session as SASession

from app.database.session import get_db
from app.database.models import User, OrganizationMember
from app.auth.jwt import decode_access_token

logger = logging.getLogger(__name__)

# HTTP Bearer 认证方案
security = HTTPBearer(auto_error=False)


async def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    db: SASession = Depends(get_db),
) -> User:
    """从 JWT Token 获取当前用户

    Args:
        credentials: Bearer Token 凭证
        db: 数据库会话

    Returns:
        User 对象

    Raises:
        HTTPException 401: Token 缺失或无效
    """
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="未提供认证凭证",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = credentials.credentials
    payload = decode_access_token(token)

    if payload is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token 无效或已过期",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user_id = payload.get("sub")
    if user_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token 中缺少用户标识",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user = db.query(User).filter(User.id == int(user_id)).first()
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="用户不存在",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return user


def require_role(*roles: str):
    """角色权限校验装饰器

    用于 FastAPI 路由，校验当前用户是否具有指定角色。

    Args:
        roles: 允许的角色列表

    Returns:
        装饰器函数

    Usage:
        @router.get("/admin")
        @require_role("admin")
        async def admin_only(current_user: User = Depends(get_current_user)):
            ...
    """
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # 从 kwargs 中查找 current_user
            user = kwargs.get("current_user")
            if user is None:
                for arg in args:
                    if isinstance(arg, User):
                        user = arg
                        break
            if user is None:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="未找到用户信息",
                )
            if user.role not in roles:
                logger.warning(
                    "权限不足: user=%s role=%s required=%s",
                    user.username, user.role, roles,
                )
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"权限不足，需要以下角色之一: {', '.join(roles)}",
                )
            return await func(*args, **kwargs)
        return wrapper
    return decorator


def _role_name(value) -> str:
    if value is None:
        return ""
    return str(value.value if hasattr(value, "value") else value).strip().lower()


async def require_system_status_user(
    current_user: User = Depends(get_current_user),
    db: SASession = Depends(get_db),
) -> User:
    """诊断接口鉴权：JWT 必填。

    development：任意已登录用户。
    production：User.role 或企业角色为 admin / devops。
    """
    from app.config import settings

    if not settings.is_production():
        return current_user

    allowed = {"admin", "devops"}
    if _role_name(current_user.role) in allowed:
        return current_user

    if current_user.organization_id:
        member = (
            db.query(OrganizationMember)
            .filter(
                OrganizationMember.organization_id == current_user.organization_id,
                OrganizationMember.user_id == current_user.id,
            )
            .first()
        )
        if member and _role_name(member.role) in allowed:
            return current_user

    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="权限不足，生产环境诊断接口需要 admin 或 devops 角色",
    )


# 可选认证（不强制要求 Token）
async def get_optional_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    db: SASession = Depends(get_db),
) -> Optional[User]:
    """可选获取当前用户（没有 Token 也可以）"""
    if credentials is None:
        return None
    try:
        return await get_current_user(credentials, db)
    except HTTPException:
        return None


async def get_chat_user(
    current_user: Optional[User] = Depends(get_optional_user),
) -> Optional[User]:
    """对话接口鉴权：开发环境允许匿名；生产环境必须登录。"""
    from app.config import settings

    if settings.is_production() and current_user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="未提供认证凭证",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return current_user
