"""知识源权限：viewer 可搜，admin/devops 可配源与同步。"""
from __future__ import annotations

from fastapi import Depends, HTTPException, status
from sqlalchemy.orm import Session as SASession

from app.auth.dependencies import get_current_user, _role_name
from app.database.models import OrganizationMember, User
from app.database.session import get_db

_MANAGER_ROLES = {"admin", "devops"}


def user_can_manage_sources(user: User, db: SASession) -> bool:
    if _role_name(user.role) in _MANAGER_ROLES:
        return True
    if not user.organization_id:
        return False
    member = (
        db.query(OrganizationMember)
        .filter(
            OrganizationMember.organization_id == user.organization_id,
            OrganizationMember.user_id == user.id,
        )
        .first()
    )
    return bool(member and _role_name(member.role) in _MANAGER_ROLES)


def require_source_manager(
    current_user: User = Depends(get_current_user),
    db: SASession = Depends(get_db),
) -> User:
    if not user_can_manage_sources(current_user, db):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="配置知识源需要 admin 或 devops 角色",
        )
    if not current_user.organization_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="用户不属于任何企业，无法配置企业知识源",
        )
    return current_user


def document_visible(doc, user: User) -> bool:
    status_val = getattr(doc, "status", None) or "active"
    if status_val == "deleted":
        return False
    if doc.user_id == user.id:
        return True
    if doc.source_id and user.organization_id and doc.organization_id == user.organization_id:
        return True
    return False
