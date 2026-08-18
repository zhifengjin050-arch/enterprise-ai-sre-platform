"""v3.3 Knowledge Hub tables and document columns

Revision ID: 002_knowledge_hub
Revises: 001_initial_schema
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = "002_knowledge_hub"
down_revision: Union[str, None] = "001_initial_schema"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "knowledge_sources",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("organization_id", sa.Integer(), nullable=False),
        sa.Column("type", sa.String(length=40), nullable=False),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("status", sa.String(length=40), nullable=False, server_default="disconnected"),
        sa.Column("config_enc", sa.Text(), nullable=True),
        sa.Column("last_sync_at", sa.DateTime(), nullable=True),
        sa.Column("last_error", sa.Text(), nullable=True),
        sa.Column("created_by", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"]),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_knowledge_sources_organization_id", "knowledge_sources", ["organization_id"])

    op.create_table(
        "sync_tasks",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("source_id", sa.Integer(), nullable=False),
        sa.Column("trigger", sa.String(length=20), nullable=False, server_default="manual"),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="queued"),
        sa.Column("stats_json", sa.JSON(), nullable=True),
        sa.Column("started_at", sa.DateTime(), nullable=True),
        sa.Column("finished_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["source_id"], ["knowledge_sources.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_sync_tasks_source_id", "sync_tasks", ["source_id"])

    op.create_table(
        "sync_logs",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("task_id", sa.Integer(), nullable=False),
        sa.Column("level", sa.String(length=20), nullable=False, server_default="info"),
        sa.Column("external_id", sa.String(length=200), nullable=True),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["task_id"], ["sync_tasks.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_sync_logs_task_id", "sync_logs", ["task_id"])

    op.add_column("knowledge_documents", sa.Column("organization_id", sa.Integer(), nullable=True))
    op.add_column("knowledge_documents", sa.Column("source_id", sa.Integer(), nullable=True))
    op.add_column("knowledge_documents", sa.Column("external_id", sa.String(length=200), nullable=True))
    op.add_column("knowledge_documents", sa.Column("external_url", sa.String(length=500), nullable=True))
    op.add_column("knowledge_documents", sa.Column("checksum", sa.String(length=64), nullable=True))
    op.add_column("knowledge_documents", sa.Column("status", sa.String(length=20), server_default="active", nullable=False))
    op.create_index("ix_knowledge_documents_organization_id", "knowledge_documents", ["organization_id"])
    op.create_index("ix_knowledge_documents_source_id", "knowledge_documents", ["source_id"])
    op.create_index("ix_knowledge_documents_external_id", "knowledge_documents", ["external_id"])
    op.create_unique_constraint("uq_kb_source_external", "knowledge_documents", ["source_id", "external_id"])
    op.create_foreign_key("fk_kb_docs_org", "knowledge_documents", "organizations", ["organization_id"], ["id"])
    op.create_foreign_key("fk_kb_docs_source", "knowledge_documents", "knowledge_sources", ["source_id"], ["id"])


def downgrade() -> None:
    op.drop_constraint("fk_kb_docs_source", "knowledge_documents", type_="foreignkey")
    op.drop_constraint("fk_kb_docs_org", "knowledge_documents", type_="foreignkey")
    op.drop_constraint("uq_kb_source_external", "knowledge_documents", type_="unique")
    op.drop_index("ix_knowledge_documents_external_id", table_name="knowledge_documents")
    op.drop_index("ix_knowledge_documents_source_id", table_name="knowledge_documents")
    op.drop_index("ix_knowledge_documents_organization_id", table_name="knowledge_documents")
    op.drop_column("knowledge_documents", "status")
    op.drop_column("knowledge_documents", "checksum")
    op.drop_column("knowledge_documents", "external_url")
    op.drop_column("knowledge_documents", "external_id")
    op.drop_column("knowledge_documents", "source_id")
    op.drop_column("knowledge_documents", "organization_id")
    op.drop_table("sync_logs")
    op.drop_table("sync_tasks")
    op.drop_table("knowledge_sources")
