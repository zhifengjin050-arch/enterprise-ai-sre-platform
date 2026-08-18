"""Organization management API"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session as SASession
from pydantic import BaseModel, Field
from app.database.session import get_db
from app.database.models import User, Organization, OrganizationMember
from app.auth.dependencies import get_current_user

router = APIRouter(prefix="/api/org", tags=["企业管理"])


class CreateOrgRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    slug: str = Field(..., min_length=2, max_length=100, pattern=r"^[a-z0-9-]+$")


@router.post("/")
async def create_organization(
    req: CreateOrgRequest,
    current_user: User = Depends(get_current_user),
    db: SASession = Depends(get_db),
):
    existing = db.query(Organization).filter(Organization.slug == req.slug).first()
    if existing:
        raise HTTPException(status_code=409, detail="企业标识已存在")
    org = Organization(name=req.name, slug=req.slug)
    db.add(org)
    db.flush()
    member = OrganizationMember(
        organization_id=org.id, user_id=current_user.id, role="admin"
    )
    db.add(member)
    current_user.organization_id = org.id
    db.commit()
    db.refresh(org)
    return {"id": org.id, "name": org.name, "slug": org.slug, "role": "admin"}


@router.get("/me")
async def get_my_organization(
    current_user: User = Depends(get_current_user),
    db: SASession = Depends(get_db),
):
    if not current_user.organization_id:
        return {"organization": None}
    org = db.query(Organization).filter(Organization.id == current_user.organization_id).first()
    if not org:
        return {"organization": None}
    members = db.query(OrganizationMember).filter(
        OrganizationMember.organization_id == org.id
    ).all()
    return {
        "organization": {
            "id": org.id, "name": org.name, "slug": org.slug,
            "plan": org.plan, "is_active": org.is_active,
        },
        "members": [
            {"user_id": m.user_id, "role": m.role.value if hasattr(m.role, 'value') else m.role}
            for m in members
        ],
    }


@router.get("/members")
async def list_members(
    current_user: User = Depends(get_current_user),
    db: SASession = Depends(get_db),
):
    if not current_user.organization_id:
        raise HTTPException(status_code=403, detail="不属于任何企业")
    members = db.query(OrganizationMember).filter(
        OrganizationMember.organization_id == current_user.organization_id
    ).all()
    result = []
    for m in members:
        user = db.query(User).filter(User.id == m.user_id).first()
        if user:
            result.append({
                "user_id": user.id, "username": user.username,
                "email": user.email, "role": m.role.value if hasattr(m.role, 'value') else m.role,
            })
    return result