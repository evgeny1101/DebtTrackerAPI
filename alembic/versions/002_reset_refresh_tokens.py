"""Reset refresh tokens: from now on only SHA-256 hashes are stored

Revision ID: 002
Revises: 001
Create Date: 2026-08-20
"""

from collections.abc import Sequence

from alembic import op

revision: str = "002"
down_revision: str | None = "001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute("DELETE FROM refresh_tokens")


def downgrade() -> None:
    pass
