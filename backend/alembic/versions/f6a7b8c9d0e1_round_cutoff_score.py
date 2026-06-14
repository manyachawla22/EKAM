"""add cutoff_score to rounds (single source of truth for advancement cutoff, #13)

Revision ID: f6a7b8c9d0e1
Revises: e5f6a7b8c9d0
Create Date: 2026-06-14

"""
from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = "f6a7b8c9d0e1"
down_revision: Union[str, Sequence[str], None] = "e5f6a7b8c9d0"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("ALTER TABLE rounds ADD COLUMN IF NOT EXISTS cutoff_score DOUBLE PRECISION")


def downgrade() -> None:
    op.execute("ALTER TABLE rounds DROP COLUMN IF EXISTS cutoff_score")
