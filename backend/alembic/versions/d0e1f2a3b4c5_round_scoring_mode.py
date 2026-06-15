"""add rounds.scoring_mode (automated scoring, Task 3 Stage 5)

Revision ID: d0e1f2a3b4c5
Revises: c9d0e1f2a3b4
Create Date: 2026-06-15

"""
from typing import Sequence, Union

from alembic import op


revision: str = "d0e1f2a3b4c5"
down_revision: Union[str, Sequence[str], None] = "c9d0e1f2a3b4"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(
        "ALTER TABLE rounds ADD COLUMN IF NOT EXISTS "
        "scoring_mode VARCHAR NOT NULL DEFAULT 'human'"
    )


def downgrade() -> None:
    op.execute("ALTER TABLE rounds DROP COLUMN IF EXISTS scoring_mode")
