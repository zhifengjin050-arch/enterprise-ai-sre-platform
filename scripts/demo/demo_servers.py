"""CloudShop 科技有限公司 — Demo 服务器数据

模拟企业生产环境服务器架构：
- prod-web-01/02: Web 服务节点
- prod-db-01: 数据库主节点
- prod-cache-01: 缓存节点

关联到 cloudshop_admin 用户。
"""

import logging

from app.database.database import engine, Base
from app.database.models import User, ManagedServer
from app.database.session import get_local_session
from app.security.secrets import encrypt_secret

logger = logging.getLogger(__name__)

# ============================================================
# Demo 服务器定义
# ============================================================
DEMO_SERVERS = [
    {
        "name": "prod-web-01",
        "host": "192.168.1.10",
        "port": 22,
        "username": "opsadmin",
        "auth_type": "password",
        "auth_credential": "CloudShop@Prod!",
        "description": "生产环境 Web 服务器节点 1 — 运行 Nginx + Node.js 应用",
    },
    {
        "name": "prod-web-02",
        "host": "192.168.1.11",
        "port": 22,
        "username": "opsadmin",
        "auth_type": "password",
        "auth_credential": "CloudShop@Prod!",
        "description": "生产环境 Web 服务器节点 2 — 运行 Nginx + Node.js 应用",
    },
    {
        "name": "prod-db-01",
        "host": "192.168.1.20",
        "port": 22,
        "username": "opsadmin",
        "auth_type": "password",
        "auth_credential": "CloudShop@Prod!",
        "description": "生产环境数据库主节点 — 运行 PostgreSQL 主库",
    },
    {
        "name": "prod-cache-01",
        "host": "192.168.1.30",
        "port": 22,
        "username": "opsadmin",
        "auth_type": "password",
        "auth_credential": "CloudShop@Prod!",
        "description": "生产环境缓存节点 — 运行 Redis 集群",
    },
]


def get_admin_user(db):
    """获取 cloudshop_admin 用户"""
    return db.query(User).filter(User.username == "cloudshop_admin").first()


def create_demo_servers(db_session=None) -> list[ManagedServer]:
    """创建 Demo 服务器，返回服务器列表"""
    Base.metadata.create_all(bind=engine)
    created_servers = []
    close_session = db_session is None
    db = db_session or get_local_session()

    try:
        admin = get_admin_user(db)
        if not admin:
            logger.warning("admin 用户不存在，请先运行 demo_users.py")
            return []

        for server_data in DEMO_SERVERS:
            existing = db.query(ManagedServer).filter(
                ManagedServer.name == server_data["name"],
                ManagedServer.user_id == admin.id,
            ).first()

            if existing:
                logger.info("服务器已存在，跳过: %s", server_data["name"])
                created_servers.append(existing)
                continue

            server = ManagedServer(
                user_id=admin.id,
                name=server_data["name"],
                host=server_data["host"],
                port=server_data["port"],
                username=server_data["username"],
                auth_type=server_data["auth_type"],
                auth_credential=encrypt_secret(server_data["auth_credential"]),
                description=server_data["description"],
                is_active=True,
            )
            db.add(server)
            db.commit()
            db.refresh(server)
            created_servers.append(server)
            logger.info(
                "创建 Demo 服务器: id=%d name=%s host=%s:%d",
                server.id, server.name, server.host, server.port,
            )

        logger.info("Demo 服务器创建完成: %d 台服务器", len(created_servers))
        return created_servers

    except Exception as e:
        if close_session:
            db.rollback()
        logger.error("创建 Demo 服务器失败: %s", e)
        raise
    finally:
        if close_session:
            db.close()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    print("=" * 60)
    print("  CloudShop 科技有限公司 — Demo 服务器初始化")
    print("=" * 60)

    servers = create_demo_servers()
    print(f"\n[OK] 成功创建 {len(servers)} 台 Demo 服务器：")
    for s in servers:
        print(f"   - {s.name} ({s.host}:{s.port})")
