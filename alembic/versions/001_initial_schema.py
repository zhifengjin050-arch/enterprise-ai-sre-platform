"""Initialize all tables for v3.0.0 Production Edition

Creates: organizations, organization_members, users, conversations, messages,
managed_servers, agent_executions, agent_traces, alerts,
knowledge_documents, knowledge_chunks

Revision ID: 001_initial_schema
Revises: None
Create Date: 2026-08-17 23:13:00.000000
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = "001_initial_schema"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ============================================================
    # Organizations (企业/组织) — no FK dependencies
    # ============================================================
    op.create_table(
        "organizations",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("name", sa.String(length=200), nullable=False, comment="企业名称"),
        sa.Column("slug", sa.String(length=100), nullable=False, comment="企业唯一标识"),
        sa.Column("plan", sa.String(length=50), server_default="free", comment="套餐: free/pro/enterprise"),
        sa.Column("is_active", sa.Boolean(), server_default="true"),
        sa.Column("settings", sa.JSON(), nullable=True, comment="企业设置"),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_organizations_id"), "organizations", ["id"])
    op.create_index(op.f("ix_organizations_slug"), "organizations", ["slug"], unique=True)

    # ============================================================
    # Users — no FK dependencies
    # ============================================================
    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("username", sa.String(length=50), nullable=False),
        sa.Column("email", sa.String(length=120), nullable=False),
        sa.Column("password_hash", sa.String(length=255), nullable=False),
        sa.Column("role", sa.Enum("admin", "user", "viewer", name="userrole"), nullable=False, server_default="user"),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_users_email"), "users", ["email"], unique=True)
    op.create_index(op.f("ix_users_id"), "users", ["id"])
    op.create_index(op.f("ix_users_username"), "users", ["username"], unique=True)

    # ============================================================
    # Organization Members (FK → organizations, users)
    # ============================================================
    op.create_table(
        "organization_members",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("organization_id", sa.Integer(), sa.ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column(
            "role", sa.Enum("admin", "devops", "viewer", name="organizationrole"),
            nullable=False, server_default="viewer",
        ),
        sa.Column("joined_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("organization_id", "user_id", name="uq_org_user"),
    )
    op.create_index(op.f("ix_organization_members_id"), "organization_members", ["id"])
    op.create_index(op.f("ix_organization_members_organization_id"), "organization_members", ["organization_id"])
    op.create_index(op.f("ix_organization_members_user_id"), "organization_members", ["user_id"])

    # ============================================================
    # Conversations (FK → users)
    # ============================================================
    op.create_table(
        "conversations",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("title", sa.String(length=200), server_default="新会话", nullable=False),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_conversations_id"), "conversations", ["id"])
    op.create_index(op.f("ix_conversations_user_id"), "conversations", ["user_id"])

    # ============================================================
    # Messages (FK → conversations)
    # ============================================================
    op.create_table(
        "messages",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("conversation_id", sa.Integer(), sa.ForeignKey("conversations.id", ondelete="CASCADE"), nullable=False),
        sa.Column("role", sa.Enum("user", "assistant", "tool", name="messagerole"), nullable=False),
        sa.Column("content", sa.Text(), nullable=False, server_default=""),
        sa.Column("trace_json", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_messages_conversation_id"), "messages", ["conversation_id"])
    op.create_index(op.f("ix_messages_id"), "messages", ["id"])

    # ============================================================
    # Managed Servers (FK → users)
    # ============================================================
    op.create_table(
        "managed_servers",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("name", sa.String(length=100), nullable=False, comment="服务器别名"),
        sa.Column("host", sa.String(length=255), nullable=False, comment="服务器 IP 或域名"),
        sa.Column("port", sa.Integer(), server_default="22", nullable=False, comment="SSH 端口"),
        sa.Column("username", sa.String(length=100), nullable=False, comment="SSH 登录用户名"),
        sa.Column("auth_type", sa.Enum("password", "key", name="sshkeytype"), nullable=False, server_default="password", comment="认证类型"),
        sa.Column("auth_credential", sa.String(length=1024), nullable=True, comment="密码或密钥路径（加密存储）"),
        sa.Column("description", sa.String(length=500), server_default="", comment="服务器描述"),
        sa.Column("is_active", sa.Boolean(), server_default="true", comment="是否启用"),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_managed_servers_id"), "managed_servers", ["id"])
    op.create_index(op.f("ix_managed_servers_user_id"), "managed_servers", ["user_id"])

    # ============================================================
    # Agent Executions (FK → users, conversations)
    # ============================================================
    op.create_table(
        "agent_executions",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("conversation_id", sa.Integer(), sa.ForeignKey("conversations.id", ondelete="SET NULL"), nullable=True),
        sa.Column("status", sa.Enum("running", "success", "failed", name="executionstatus"), nullable=False, server_default="running", comment="执行状态"),
        sa.Column("duration", sa.Float(), server_default="0.0", comment="执行耗时（秒）"),
        sa.Column("tools_called", sa.Integer(), server_default="0", comment="调用工具数量"),
        sa.Column("error_message", sa.Text(), nullable=True, comment="错误信息"),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_agent_executions_conversation_id"), "agent_executions", ["conversation_id"])
    op.create_index(op.f("ix_agent_executions_id"), "agent_executions", ["id"])
    op.create_index(op.f("ix_agent_executions_user_id"), "agent_executions", ["user_id"])

    # ============================================================
    # Agent Traces (FK → conversations)
    # ============================================================
    op.create_table(
        "agent_traces",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("conversation_id", sa.Integer(), sa.ForeignKey("conversations.id", ondelete="CASCADE"), nullable=False),
        sa.Column("step", sa.Integer(), server_default="0", nullable=False, comment="执行步骤序号"),
        sa.Column("event_type", sa.String(length=50), nullable=False, comment="事件类型: agent_start/rag_search/memory_load/llm_start/tool_call/tool_result/final_answer"),
        sa.Column("content", sa.Text(), nullable=True, comment="事件内容/描述"),
        sa.Column("tool_name", sa.String(length=100), nullable=True, comment="工具名称（如果是工具调用事件）"),
        sa.Column("duration", sa.Float(), server_default="0.0", comment="耗时（毫秒）"),
        sa.Column("meta_info", sa.JSON(), nullable=True, comment="附加元数据"),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_agent_traces_conversation_id"), "agent_traces", ["conversation_id"])
    op.create_index(op.f("ix_agent_traces_id"), "agent_traces", ["id"])

    # ============================================================
    # Alerts
    # ============================================================
    op.create_table(
        "alerts",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("level", sa.Enum("info", "warning", "critical", name="alertlevel"), nullable=False, server_default="warning", comment="告警等级"),
        sa.Column("title", sa.String(length=200), nullable=False, comment="告警标题"),
        sa.Column("message", sa.Text(), nullable=False, comment="告警消息"),
        sa.Column("source", sa.String(length=100), server_default="system", nullable=False, comment="告警来源"),
        sa.Column("status", sa.Enum("firing", "resolved", name="alertstatus"), nullable=False, server_default="firing", comment="告警状态"),
        sa.Column("ai_analysis", sa.JSON(), nullable=True, comment="AI 分析结果"),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.Column("resolved_at", sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_alerts_id"), "alerts", ["id"])
    op.create_index(op.f("ix_alerts_status"), "alerts", ["status"])

    # ============================================================
    # Knowledge Documents (FK → users)
    # ============================================================
    op.create_table(
        "knowledge_documents",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("title", sa.String(length=200), nullable=False, comment="文档标题"),
        sa.Column("content", sa.Text(), nullable=False, comment="文档内容（原始）"),
        sa.Column("source", sa.String(length=100), server_default="manual", comment="来源: manual/file/import"),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_knowledge_documents_id"), "knowledge_documents", ["id"])
    op.create_index(op.f("ix_knowledge_documents_user_id"), "knowledge_documents", ["user_id"])

    # ============================================================
    # Knowledge Chunks (FK → knowledge_documents)
    # ============================================================
    op.create_table(
        "knowledge_chunks",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("document_id", sa.Integer(), sa.ForeignKey("knowledge_documents.id", ondelete="CASCADE"), nullable=False),
        sa.Column("content", sa.Text(), nullable=False, comment="文本块内容"),
        sa.Column("embedding", sa.Text(), nullable=True, comment="向量（JSON 格式存储）"),
        sa.Column("meta_info", sa.JSON(), nullable=True, comment="附加元数据"),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_knowledge_chunks_document_id"), "knowledge_chunks", ["document_id"])
    op.create_index(op.f("ix_knowledge_chunks_id"), "knowledge_chunks", ["id"])


def downgrade() -> None:
    # Drop in reverse order of dependencies
    op.drop_table("knowledge_chunks")
    op.drop_table("knowledge_documents")
    op.drop_table("alerts")
    op.drop_table("agent_traces")
    op.drop_table("agent_executions")
    op.drop_table("managed_servers")
    op.drop_table("messages")
    op.drop_table("conversations")
    op.drop_table("organization_members")
    op.drop_table("users")
    op.drop_table("organizations")

    # Drop enum types (PostgreSQL needs explicit cleanup)
    op.execute("DROP TYPE IF EXISTS organizationrole")
    op.execute("DROP TYPE IF EXISTS userrole")
    op.execute("DROP TYPE IF EXISTS messagerole")
    op.execute("DROP TYPE IF EXISTS sshkeytype")
    op.execute("DROP TYPE IF EXISTS executionstatus")
    op.execute("DROP TYPE IF EXISTS alertlevel")
    op.execute("DROP TYPE IF EXISTS alertstatus")