"""add 'anomaly_review' value to requesttype enum (#2)

Revision ID: b8c9d0e1f2a3
Revises: a7b8c9d0e1f2
Create Date: 2026-06-15

ALTER TYPE ... ADD VALUE cannot run inside a transaction block on older
PostgreSQL, so we use Alembic's autocommit_block. IF NOT EXISTS makes it
idempotent (PG 10+).
"""
from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = "b8c9d0e1f2a3"
down_revision: Union[str, Sequence[str], None] = "a7b8c9d0e1f2"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.get_context().autocommit_block():
        op.execute("ALTER TYPE requesttype ADD VALUE IF NOT EXISTS 'anomaly_review'")


def downgrade() -> None:
    # Postgres has no DROP VALUE for enums; leaving the label in place is harmless.
    pass
