"""CloudShop 科技有限公司 — Demo 历史事件与告警数据

模拟过去一周的生产事件记录，用于演示 AI Agent 故障分析能力。
"""

import logging
import json

from app.database.session import get_local_session
from app.database.models import AlertRecord, AlertLevel, AlertStatus, AgentExecution, ExecutionStatus, User, Conversation

logger = logging.getLogger(__name__)

# ============================================================
# Demo 历史事件定义
# ============================================================
DEMO_INCIDENTS = [
    {
        "time": "2026-08-14 14:30:00",
        "title": "订单服务响应超时",
        "level": "critical",
        "message": "order-service 接口 P99 延迟从 200ms 飙升到 5s，影响订单创建流程",
        "status": "resolved",
        "root_cause": "数据库连接池耗尽，由于突发流量导致连接数超过 max_connections",
        "resolution": "紧急扩容数据库连接池从 100 到 200，重启 order-service Pod",
        "duration": "45分钟",
    },
    {
        "time": "2026-08-13 09:15:00",
        "title": "支付网关回调延迟",
        "level": "warning",
        "message": "payment-service 处理支付回调延迟 > 30s，部分订单支付状态未及时更新",
        "status": "resolved",
        "root_cause": "第三方支付 API 响应变慢，导致回调处理线程阻塞",
        "resolution": "增加回调超时时间，添加异步重试机制",
        "duration": "30分钟",
    },
    {
        "time": "2026-08-12 22:00:00",
        "title": "prod-db-01 磁盘使用率告警",
        "level": "warning",
        "message": "prod-db-01 数据盘使用率超过 78%，预计 7 天内达到 90% 阈值",
        "status": "resolved",
        "root_cause": "数据库 WAL 日志未及时清理，历史数据增长",
        "resolution": "清理过期 WAL 日志，规划磁盘扩容",
        "duration": "2小时",
    },
    {
        "time": "2026-08-11 18:45:00",
        "title": "生产环境 Nginx 502 错误",
        "level": "critical",
        "message": "prod-web-01 Nginx 返回 502 Bad Gateway，影响用户访问",
        "status": "resolved",
        "root_cause": "node-app 容器因内存限制（OOMKilled）被重新调度",
        "resolution": "调整容器内存限制从 512Mi 到 1Gi，增加就绪探针延迟",
        "duration": "20分钟",
    },
]


def create_demo_history(admin_user=None, db_session=None) -> list:
    """创建 Demo 历史事件和告警记录"""
    created_items = []
    close_session = db_session is None
    db = db_session or get_local_session()

    try:
        # 查找 admin 用户
        if admin_user is None:
            admin_user = db.query(User).filter(User.username == "cloudshop_admin").first()

        if not admin_user:
            logger.warning("admin 用户不存在，请先运行 demo_users.py")
            return []

        # 创建会话
        conv = Conversation(
            user_id=admin_user.id,
            title="Demo 历史事件分析会话",
        )
        db.add(conv)
        db.commit()
        db.refresh(conv)

        # 创建历史告警
        for inc in DEMO_INCIDENTS:
            existing_alert = db.query(AlertRecord).filter(
                AlertRecord.source == "demo",
                AlertRecord.title == inc["title"],
            ).first()
            if existing_alert:
                created_items.append(existing_alert)
                logger.info("Demo 事件已存在，跳过: %s", inc["title"])
                continue
            alert = AlertRecord(
                level=AlertLevel(inc["level"]),
                title=inc["title"],
                message=json.dumps({
                    "description": inc["message"],
                    "root_cause": inc.get("root_cause", ""),
                    "resolution": inc.get("resolution", ""),
                    "duration": inc.get("duration", ""),
                }, ensure_ascii=False),
                source="demo",
                status=AlertStatus(inc["status"]),
                ai_analysis={
                    "problem": inc["message"],
                    "possible_reasons": [inc.get("root_cause", "")],
                    "suggestions": [inc.get("resolution", "")],
                },
            )
            db.add(alert)
            db.commit()
            created_items.append(alert)
            logger.info("创建 Demo 事件: %s [%s]", inc["title"], inc["level"])

        # 创建 Agent 执行记录
        execution = AgentExecution(
            user_id=admin_user.id,
            conversation_id=conv.id,
            status=ExecutionStatus.success,
            duration=12.5,
            tools_called=3,
        )
        db.add(execution)
        db.commit()
        created_items.append(execution)

        logger.info("Demo 历史事件创建完成: %d 条记录", len(created_items))
        return created_items

    except Exception as e:
        if close_session:
            db.rollback()
        logger.error("创建 Demo 历史事件失败: %s", e)
        raise
    finally:
        if close_session:
            db.close()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    print("=" * 60)
    print("  CloudShop 科技有限公司 — Demo 历史事件初始化")
    print("=" * 60)

    items = create_demo_history()
    alerts = [i for i in items if isinstance(i, AlertRecord)]
    print(f"\n[OK] 成功创建 {len(alerts)} 条历史事件：")
    for a in alerts:
        print(f"   [{a.level.value.upper()}] {a.title}")
    print("\n事件统计：")
    print(f"   - 严重: {sum(1 for a in alerts if a.level == AlertLevel.critical)}")
    print(f"   - 警告: {sum(1 for a in alerts if a.level == AlertLevel.warning)}")
    print(f"   - 已解决: {sum(1 for a in alerts if a.status == AlertStatus.resolved)}")
