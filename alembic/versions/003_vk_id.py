"""Add VK ID sign-in columns to users

Revision ID: 003
Revises: 002
Create Date: 2026-09-10
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "003"
down_revision: str | None = "002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("users", sa.Column("vkId", sa.String(), nullable=True))
    op.add_column("users", sa.Column("email", sa.String(), nullable=True))
    op.add_column("users", sa.Column("fullName", sa.String(), nullable=True))
    op.create_index("ix_users_vkId", "users", ["vkId"], unique=True)

    with op.batch_alter_table("users") as batch_op:
        batch_op.alter_column("passwordHash", nullable=True)


def downgrade() -> None:
    op.drop_index("ix_users_vkId", table_name="users")
    op.drop_column("users", "fullName")
    op.drop_column("users", "email")
    op.drop_column("users", "vkId")
