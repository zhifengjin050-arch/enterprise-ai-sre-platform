"""修复审批 API

提供 /api/repair/approve 和 /api/repair/reject 端点，
用于批准或拒绝 Agent 提出的自动修复操作。

属于 v3.0.0 Production Edition — Phase 4: Agent Auto-Repair with Approval
"""
from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session as SASession
from app.database.session import get_db
from app.database.models import User
from app.auth.dependencies import get_current_user
from app.agent.approval import approve_action, reject_action, execute_approved_action

router = APIRouter(prefix="/api/repair", tags=["自动修复"])


class ApproveRequest(BaseModel):
    token: str = Field(..., min_length=1, description="审批令牌")


class RejectRequest(BaseModel):
    token: str = Field(..., min_length=1, description="审批令牌")


@router.post("/approve")
async def approve_repair(
    req: ApproveRequest,
    current_user: User = Depends(get_current_user),
    db: SASession = Depends(get_db),
):
    """批准修复操作

    用户通过此接口确认执行 Agent 提出的修复方案。
    - 需要 JWT 认证
    - token 由 Agent 在修复方案中提供
    """
    if approve_action(req.token):
        result = execute_approved_action(req.token, db=db)
        return {"status": "approved", "result": result}
    return {"status": "error", "detail": "审批令牌无效或已处理"}


@router.post("/reject")
async def reject_repair(
    req: RejectRequest,
    current_user: User = Depends(get_current_user),
):
    """拒绝修复操作

    用户通过此接口拒绝 Agent 提出的修复方案。
    - 需要 JWT 认证
    - token 由 Agent 在修复方案中提供
    """
    if reject_action(req.token):
        return {"status": "rejected"}
    return {"status": "error", "detail": "审批令牌无效或已处理"}