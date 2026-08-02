"""Initial schema: users, refresh_tokens, debts, payments

Revision ID: 001
Revises:
Create Date: 2026-08-01
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("username", sa.String(), nullable=False),
        sa.Column("passwordHash", sa.String(), nullable=False),
        sa.Column("createdAt", sa.BigInteger(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("username"),
    )
    op.create_index("ix_users_username", "users", ["username"])

    op.create_table(
        "debts",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("type", sa.String(), nullable=False),
        sa.Column("initialAmount", sa.BigInteger(), nullable=False),
        sa.Column("currentAmount", sa.BigInteger(), nullable=False),
        sa.Column("createdAt", sa.BigInteger(), nullable=False),
        sa.Column("reminderIntervalDays", sa.Integer(), nullable=True),
        sa.Column("lastReminderTimestamp", sa.BigInteger(), nullable=True),
        sa.Column("userId", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["userId"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "payments",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("amount", sa.BigInteger(), nullable=False),
        sa.Column("dateMillis", sa.BigInteger(), nullable=False),
        sa.Column("debtId", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["debtId"], ["debts.id"]),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "refresh_tokens",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("token", sa.String(), nullable=False),
        sa.Column("userId", sa.Integer(), nullable=False),
        sa.Column("expiresAt", sa.BigInteger(), nullable=False),
        sa.Column("createdAt", sa.BigInteger(), nullable=False),
        sa.ForeignKeyConstraint(["userId"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("token"),
    )
    op.create_index("ix_refresh_tokens_token", "refresh_tokens", ["token"])


def downgrade() -> None:
    op.drop_table("refresh_tokens")
    op.drop_table("payments")
    op.drop_table("debts")
    op.drop_table("users")
