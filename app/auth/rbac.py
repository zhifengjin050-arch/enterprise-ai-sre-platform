"""RBAC Service — Multi-tenant permission management"""
from __future__ import annotations
from typing import Optional
from fastapi import Depends, HTTPException, status
from sqlalchemy.orm import Session as SASession
from app.database.models import User, Organization, OrganizationMember, OrganizationRole
from app.auth.dependencies import get_current_user
from app.database.session import get_db


class RBACService:
    @staticmethod
    def get_user_organization(user: User, db: SASession) -> Optional[Organization]:
        """Get user's organization"""
        if user.organization_id:
            return db.query(Organization).filter(Organization.id == user.organization_id).first()
        return None

    @staticmethod
    def get_user_role_in_org(user: User, org: Organization, db: SASession) -> OrganizationRole:
        """Get user's role within an organization"""
        member = db.query(OrganizationMember).filter(
            OrganizationMember.organization_id == org.id,
            OrganizationMember.user_id == user.id,
        ).first()
        return member.role if member else OrganizationRole.viewer

    @staticmethod
    def check_org_access(user: User, db: SASession, required_role: OrganizationRole = OrganizationRole.viewer):
        """Check if user has required role in their organization. Raises 403 if not."""
        org = RBACService.get_user_organization(user, db)
        if not org:
            raise HTTPException(status_code=403, detail="用户不属于任何企业")
        role = RBACService.get_user_role_in_org(user, org, db)
        role_hierarchy = {
            OrganizationRole.admin: 3,
            OrganizationRole.devops: 2,
            OrganizationRole.viewer: 1,
        }
        if role_hierarchy.get(role, 0) < role_hierarchy.get(required_role, 1):
            raise HTTPException(status_code=403, detail="权限不足")

    @staticmethod
    def require_admin(user: User = Depends(get_current_user), db: SASession = Depends(get_db)):
        """Dependency: require org admin role"""
        RBACService.check_org_access(user, db, OrganizationRole.admin)
        return user


rbac = RBACService()