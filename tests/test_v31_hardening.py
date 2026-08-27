"""v3.1.0 安全加固与 MCP Metadata 单元测试。"""

from app.config import Settings
from app.logging_config import SecretFilter
from app.mcp.metadata import get_tool_metadata, requires_approval
from app.agent.approval import classify_tool, RepairAction, create_approval, approve_action, reject_action


def test_jwt_production_rejects_default():
    s = Settings(environment="production", jwt_secret="change-me-to-a-random-secret")
    try:
        s.validate_production_security()
        assert False, "should raise"
    except RuntimeError as e:
        assert "JWT_SECRET" in str(e) or "change-me" in str(e)


def test_jwt_production_rejects_short():
    s = Settings(environment="production", jwt_secret="abcdefghijklmnop")
    try:
        s.validate_production_security()
        assert False
    except RuntimeError:
        pass


def test_jwt_production_rejects_secret_word():
    s = Settings(environment="production", jwt_secret="this-is-a-very-long-secret-key-value-32")
    try:
        s.validate_production_security()
        assert False
    except RuntimeError as e:
        assert "secret" in str(e).lower()


def test_jwt_dev_allows_default():
    s = Settings(environment="development", jwt_secret="change-me-to-a-random-secret")
    s.validate_production_security()


def test_jwt_production_accepts_strong():
    s = Settings(
        environment="production",
        jwt_secret="xk9mP2qR7wL4nV8bY3cH6jF1aD5tG0uZ",
    )
    s.validate_production_security()


def test_secret_filter_masks_sk():
    redacted = SecretFilter.redact("key=sk-abcdefghijklmnop")
    assert "sk-****mnop" in redacted
    assert "sk-abcdefghijklmnop" not in redacted


def test_secret_filter_masks_db_url():
    redacted = SecretFilter.redact("postgresql://user:hunter2@postgres:5432/db")
    assert "hunter2" not in redacted
    assert "postgresql://user:****@postgres:5432/db" == redacted


def test_cpu_tool_metadata_safe():
    meta = get_tool_metadata("get_cpu_usage")
    assert meta is not None
    assert meta.risk_level == "safe"
    assert meta.audit_required is False
    assert requires_approval("get_cpu_usage") is False


def test_docker_restart_metadata_dangerous():
    meta = get_tool_metadata("docker_restart")
    assert meta is not None
    assert meta.risk_level == "dangerous"
    assert meta.required_permission == "devops.admin"
    assert meta.audit_required is True
    assert classify_tool("docker_restart") == "dangerous"


def test_approval_lifecycle():
    action = RepairAction(
        tool_name="get_cpu_usage",
        tool_args={},
        description="noop",
        requires_approval=True,
    )
    token = create_approval(action)
    assert approve_action(token) is True
    assert reject_action(token) is False


def test_approval_bound_to_owner():
    from app.agent.approval import parse_approval_response

    action = RepairAction(
        tool_name="get_cpu_usage",
        tool_args={},
        description="noop-owned",
        requires_approval=True,
    )
    token = create_approval(action, user_id=7)
    assert approve_action(token, user_id=8) is False
    assert reject_action(token, user_id=8) is False
    assert parse_approval_response("确认", user_id=7) is None
    assert parse_approval_response(f"确认修复 {token}", user_id=8) is None
    assert parse_approval_response(f"确认修复 {token}", user_id=7) == token
    assert approve_action(token, user_id=7) is True
