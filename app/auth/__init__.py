"""认证模块

- jwt.py: JWT Token 生成与验证
- password.py: 密码加密与验证
- dependencies.py: FastAPI 依赖注入
- router.py: 认证路由
"""
from app.auth.router import router as auth_router
from app.auth.dependencies import get_current_user, require_role

__all__ = ["auth_router", "get_current_user", "require_role"]
