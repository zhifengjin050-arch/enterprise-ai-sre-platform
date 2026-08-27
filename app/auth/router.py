"""认证路由

- POST /api/auth/register — 用户注册
- POST /api/auth/login — 用户登录
- GET /api/auth/me — 获取当前用户信息
"""

import logging

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session as SASession

from app.config import settings
from app.database.session import get_db
from app.database.models import User
from app.auth.jwt import create_access_token
from app.auth.password import hash_password, verify_password
from app.auth.dependencies import get_current_user

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/auth", tags=["认证管理"])


# ============================================================
# 请求/响应模型
# ============================================================
class RegisterRequest(BaseModel):
    username: str = Field(..., min_length=2, max_length=50, description="用户名")
    email: str = Field(..., max_length=120, description="邮箱地址")
    password: str = Field(..., min_length=6, max_length=128, description="密码")


class LoginRequest(BaseModel):
    username: str = Field(..., min_length=1, description="用户名")
    password: str = Field(..., min_length=1, description="密码")


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class UserResponse(BaseModel):
    id: int
    username: str
    email: str
    role: str

    model_config = {"from_attributes": True}


# ============================================================
# 路由
# ============================================================
@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register(req: RegisterRequest, db: SASession = Depends(get_db)):
    """用户注册

    创建新用户，密码使用 bcrypt 加密存储。
    生产环境默认关闭公开注册（ALLOW_REGISTER=false）。
    """
    if settings.is_production() and not settings.allow_register:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="生产环境已关闭公开注册",
        )

    # 检查用户名是否已存在
    existing = db.query(User).filter(
        (User.username == req.username) | (User.email == req.email)
    ).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="用户名或邮箱已被注册",
        )

    # 创建用户
    hashed_pwd = hash_password(req.password)
    user = User(
        username=req.username,
        email=req.email,
        password_hash=hashed_pwd,
        role="user",
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    logger.info("新用户注册: id=%d username=%s", user.id, user.username)
    return user


@router.post("/login")
async def login(req: LoginRequest, db: SASession = Depends(get_db)):
    """用户登录

    验证用户名和密码，返回 JWT Token + 用户信息。
    """
    user = db.query(User).filter(User.username == req.username).first()
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="用户名或密码错误",
        )

    if not verify_password(req.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="用户名或密码错误",
        )

    # 生成 Token
    token = create_access_token(data={"sub": str(user.id)})
    logger.info("用户登录: id=%d username=%s", user.id, user.username)
    return {
        "access_token": token,
        "token_type": "bearer",
        "user": {
            "id": user.id,
            "username": user.username,
            "email": user.email,
            "role": user.role,
        },
    }


@router.get("/me", response_model=UserResponse)
async def get_me(current_user: User = Depends(get_current_user)):
    """获取当前用户信息

    需要 JWT Token（Authorization: Bearer <token>）。
    """
    return current_user
