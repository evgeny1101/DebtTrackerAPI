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
    bind = op.get_bind()
    has_null_password = bind.scalar(
        sa.text("SELECT COUNT(*) FROM users WHERE passwordHash IS NULL")
    )
    if has_null_password:
        raise RuntimeError(
            "Cannot downgrade: VK-only users with NULL passwordHash exist. "
            "Remove or convert them before downgrading."
        )

    op.drop_index("ix_users_vkId", table_name="users")

    with op.batch_alter_table("users") as batch_op:
        batch_op.drop_column("vkId")
        batch_op.drop_column("email")
        batch_op.drop_column("fullName")
        batch_op.alter_column("passwordHash", existing_type=sa.String(), nullable=False)
