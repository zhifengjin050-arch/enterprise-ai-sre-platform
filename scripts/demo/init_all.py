"""CloudShop 科技有限公司 — Demo 全量数据初始化

一键初始化所有 Demo 数据：
1. 创建 Demo 用户（cloudshop_admin, cloudshop_ops, cloudshop_viewer）
2. 创建 Demo 服务器（prod-web-01/02, prod-db-01, prod-cache-01）
3. 创建 Demo 历史事件与告警记录
"""

import logging
import os
import sys

# 将项目根目录加入 sys.path
_project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, _project_root)

from app.database.database import engine, Base
from app.database.session import get_local_session

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)

logger = logging.getLogger("demo_init")


def ensure_tables():
    """确保数据库表已创建"""
    import app.database.models  # noqa: F401
    Base.metadata.create_all(bind=engine)
    logger.info("数据库表已就绪")


def init_all():
    """全量初始化 Demo 数据"""
    print("=" * 70)
    print("  CloudShop 科技有限公司 -- Demo 环境全量初始化")
    print("=" * 70)

    # 1. 确保数据库表
    ensure_tables()

    # 使用共享会话
    db = get_local_session()

    try:
        # 2. 创建 Demo 用户
        print()
        print("[Step 1] 创建 Demo 用户...")
        from scripts.demo.demo_users import create_demo_users
        users = create_demo_users(db_session=db)
        admin_user = next((u for u in users if u.username == "cloudshop_admin"), None)
        print(f"   [OK] {len(users)} 个用户已创建")

        # 3. 创建 Demo 服务器
        print()
        print("[Step 2] 创建 Demo 服务器...")
        from scripts.demo.demo_servers import create_demo_servers
        servers = create_demo_servers(db_session=db)
        print(f"   [OK] {len(servers)} 台服务器已创建")

        # 4. 创建 Demo 历史事件
        print()
        print("[Step 3] 创建 Demo 历史事件...")
        from scripts.demo.demo_incidents import create_demo_history
        items = create_demo_history(admin_user=admin_user, db_session=db)
        print(f"   [OK] {len(items)} 条历史记录已创建")

        db.commit()

        # 5. 输出汇总
        print()
        print("=" * 70)
        print("  [DONE] CloudShop Demo 环境初始化完成！")
        print("=" * 70)
        print()
        print("数据汇总：")
        print(f"   - 用户: {len(users)} 个")
        print(f"   - 服务器: {len(servers)} 台")
        print(f"   - 历史事件: {len(items)} 条")
        print()
        print("测试账号：")
        print("   - admin: cloudshop_admin / Admin@2024!")
        print("   - ops:   cloudshop_ops / Ops@2024!")
        print("   - viewer: cloudshop_viewer / View@2024!")
        print()

    except Exception as e:
        db.rollback()
        logger.error("Demo 初始化失败: %s", e)
        raise
    finally:
        db.close()


if __name__ == "__main__":
    init_all()
