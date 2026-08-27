"""Widen managed_servers.auth_credential for Fernet ciphertext

Revision ID: 003_encrypt_ssh_credentials
Revises: 002_knowledge_hub
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "003_encrypt_ssh_credentials"
down_revision: Union[str, None] = "002_knowledge_hub"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("managed_servers") as batch:
        batch.alter_column(
            "auth_credential",
            existing_type=sa.String(length=1024),
            type_=sa.Text(),
            existing_nullable=True,
            comment="密码或密钥（Fernet 加密存储）",
        )


def downgrade() -> None:
    with op.batch_alter_table("managed_servers") as batch:
        batch.alter_column(
            "auth_credential",
            existing_type=sa.Text(),
            type_=sa.String(length=1024),
            existing_nullable=True,
            comment="密码或密钥路径（加密存储）",
        )
