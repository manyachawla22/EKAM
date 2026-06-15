"""add rounds.live_judging (live-judged rounds, Task 3)

Revision ID: a3b4c5d6e7f8
Revises: f2a3b4c5d6e7
Create Date: 2026-06-15

A feature flag, OFF by default. False (default) = normal submit→evaluate flow, so
existing rounds are unaffected. True = a live-judged round: no participant
submission step; a referee/judge scores in real time and the pipeline auto-creates
a placeholder submission per active team.
"""
from typing import Sequence, Union

from alembic import op


revision: str = "a3b4c5d6e7f8"
down_revision: Union[str, Sequence[str], None] = "f2a3b4c5d6e7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(
        "ALTER TABLE rounds ADD COLUMN IF NOT EXISTS "
        "live_judging BOOLEAN NOT NULL DEFAULT false"
    )


def downgrade() -> None:
    op.execute("ALTER TABLE rounds DROP COLUMN IF EXISTS live_judging")
