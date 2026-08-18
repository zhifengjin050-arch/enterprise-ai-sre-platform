"""CloudShop 科技有限公司 — Demo 用户数据

创建多角色用户用于演示：
- admin: 运维主管
- user: 普通运维工程师
- viewer: 只读观察员
"""

import logging

from app.database.database import engine, Base
from app.database.models import User, UserRole
from app.database.session import get_local_session
from app.auth.password import hash_password

logger = logging.getLogger(__name__)

# ============================================================
# Demo 用户定义
# ============================================================
DEMO_USERS = [
    {
        "username": "cloudshop_admin",
        "email": "admin@cloudshop.com",
        "password": "Admin@2024!",
        "role": UserRole.admin,
        "description": "运维主管 — 拥有全部管理权限",
    },
    {
        "username": "cloudshop_ops",
        "email": "ops@cloudshop.com",
        "password": "Ops@2024!",
        "role": UserRole.user,
        "description": "运维工程师 — 日常运维操作",
    },
    {
        "username": "cloudshop_viewer",
        "email": "viewer@cloudshop.com",
        "password": "View@2024!",
        "role": UserRole.viewer,
        "description": "监控观察员 — 只读查看",
    },
]


def create_demo_users(db_session=None) -> list[User]:
    """创建 Demo 用户，返回用户列表"""
    Base.metadata.create_all(bind=engine)
    created_users = []
    close_session = db_session is None
    db = db_session or get_local_session()

    try:
        for user_data in DEMO_USERS:
            existing = db.query(User).filter(
                User.username == user_data["username"]
            ).first()

            if existing:
                logger.info("用户已存在，跳过: %s", user_data["username"])
                created_users.append(existing)
                continue

            user = User(
                username=user_data["username"],
                email=user_data["email"],
                password_hash=hash_password(user_data["password"]),
                role=user_data["role"],
            )
            db.add(user)
            db.commit()
            db.refresh(user)
            created_users.append(user)
            logger.info(
                "创建 Demo 用户: id=%d username=%s role=%s",
                user.id, user.username, user.role.value,
            )

        logger.info("Demo 用户创建完成: %d 个用户", len(created_users))
        return created_users

    except Exception as e:
        if close_session:
            db.rollback()
        logger.error("创建 Demo 用户失败: %s", e)
        raise
    finally:
        if close_session:
            db.close()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    print("=" * 60)
    print("  CloudShop 科技有限公司 — Demo 用户初始化")
    print("=" * 60)

    users = create_demo_users()
    print(f"\n[OK] 成功创建 {len(users)} 个 Demo 用户：")
    for u in users:
        print(f"   - {u.username} ({u.email}) [{u.role.value}]")