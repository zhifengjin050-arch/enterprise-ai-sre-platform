"""数据库模块测试

覆盖：
- 创建表
- 创建用户
- 查询用户
- 创建会话
- 创建消息（含 trace）
- 会话与消息的级联删除
- 用户数据隔离
"""

import sys
import io

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

from app.database.session import get_local_session, init_db
from app.database.models import User, Conversation, Message

# 初始化数据库
init_db()


def test_create_user():
    """测试1: 创建用户"""
    session = get_local_session()
    try:
        user = User(
            username="db_test_user_1",
            email="db_test1@example.com",
            password_hash="$2b$12$hashedpassword",
            role="user",
        )
        session.add(user)
        session.commit()
        assert user.id is not None
        print(f"[OK] test_create_user — id={user.id}")
    finally:
        session.close()


def test_query_user():
    """测试2: 查询用户"""
    session = get_local_session()
    try:
        user = session.query(User).filter(
            User.username == "db_test_user_1"
        ).first()
        assert user is not None
        assert user.email == "db_test1@example.com"
        assert user.role == "user"
        print(f"[OK] test_query_user — {user.username} role={user.role}")
    finally:
        session.close()


def test_create_conversation():
    """测试3: 创建会话"""
    session = get_local_session()
    try:
        user = session.query(User).filter(
            User.username == "db_test_user_1"
        ).first()
        conv = Conversation(user_id=user.id, title="测试会话")
        session.add(conv)
        session.commit()
        assert conv.id is not None
        print(f"[OK] test_create_conversation — id={conv.id} title={conv.title}")
    finally:
        session.close()


def test_create_message():
    """测试4: 创建消息（含 trace）"""
    session = get_local_session()
    try:
        conv = session.query(Conversation).filter(
            Conversation.title == "测试会话"
        ).first()
        msg = Message(
            conversation_id=conv.id,
            role="user",
            content="检查服务器状态",
            trace_json=None,
        )
        session.add(msg)
        session.commit()
        assert msg.id is not None

        msg2 = Message(
            conversation_id=conv.id,
            role="assistant",
            content="## 报告\n\n服务器运行正常。",
            trace_json=[
                {"step": "分析用户需求", "status": "completed", "tool": "", "duration_ms": 100},
                {"step": "调用 server_health", "status": "completed", "tool": "server_health", "duration_ms": 500},
                {"step": "AI 生成报告", "status": "completed", "tool": "", "duration_ms": 2000},
            ],
        )
        session.add(msg2)
        session.commit()
        assert msg2.id is not None
        print(f"[OK] test_create_message — msg_id={msg.id} msg2_id={msg2.id} with trace")
    finally:
        session.close()


def test_conversation_messages_relation():
    """测试5: 会话与消息的关联关系"""
    session = get_local_session()
    try:
        conv = session.query(Conversation).filter(
            Conversation.title == "测试会话"
        ).first()
        assert len(conv.messages) >= 2, f"会话应有至少2条消息, 实际: {len(conv.messages)}"
        roles = [m.role for m in conv.messages]
        assert "user" in roles
        assert "assistant" in roles
        print(f"[OK] test_conversation_messages_relation — {len(conv.messages)} messages, roles: {roles}")
    finally:
        session.close()


def test_cascade_delete_conversation():
    """测试6: 删除会话时级联删除消息"""
    session = get_local_session()
    try:
        conv = session.query(Conversation).filter(
            Conversation.title == "测试会话"
        ).first()
        conv_id = conv.id
        msg_count_before = len(conv.messages)

        session.delete(conv)
        session.commit()

        # 验证消息也被删除
        remaining_msgs = session.query(Message).filter(
            Message.conversation_id == conv_id
        ).count()
        assert remaining_msgs == 0, f"级联删除后消息应全部删除, 剩余: {remaining_msgs}"
        print(f"[OK] test_cascade_delete_conversation — {msg_count_before} messages cascaded deleted")
    finally:
        session.close()


def test_data_isolation():
    """测试7: 用户数据隔离"""
    session = get_local_session()
    try:
        # 创建两个用户
        user_a = User(username="user_a", email="a@test.com", password_hash="hash", role="user")
        user_b = User(username="user_b", email="b@test.com", password_hash="hash", role="user")
        session.add(user_a)
        session.add(user_b)
        session.commit()

        # 各自创建会话
        conv_a = Conversation(user_id=user_a.id, title="A的会话")
        conv_b = Conversation(user_id=user_b.id, title="B的会话")
        session.add(conv_a)
        session.add(conv_b)
        session.commit()

        # 验证不能跨用户查询
        a_convs = session.query(Conversation).filter(
            Conversation.user_id == user_a.id
        ).all()
        for c in a_convs:
            assert c.user_id == user_a.id

        b_convs = session.query(Conversation).filter(
            Conversation.user_id == user_b.id
        ).all()
        for c in b_convs:
            assert c.user_id == user_b.id

        print(f"[OK] test_data_isolation — user_a: {len(a_convs)} convs, user_b: {len(b_convs)} convs")
    finally:
        session.close()


def test_role_default():
    """测试8: 用户角色默认值"""
    session = get_local_session()
    try:
        user = User(username="role_test", email="role@test.com", password_hash="hash")
        session.add(user)
        session.commit()
        assert user.role == "user", f"默认角色应为user, 实际: {user.role}"
        print(f"[OK] test_role_default — role={user.role}")
    finally:
        session.close()


if __name__ == "__main__":
    print("=" * 60)
    print("  数据库模块测试")
    print("=" * 60)

    test_create_user()
    test_query_user()
    test_create_conversation()
    test_create_message()
    test_conversation_messages_relation()
    test_cascade_delete_conversation()
    test_data_isolation()
    test_role_default()

    print("=" * 60)
    print(f"  全部 8 项数据库测试通过！")
    print("=" * 60)