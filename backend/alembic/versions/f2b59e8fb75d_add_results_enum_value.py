"""add results enum value

Revision ID: f2b59e8fb75d
Revises: 66914dc449f0
Create Date: 2026-06-01 01:01:56.363989

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'f2b59e8fb75d'
down_revision: Union[str, Sequence[str], None] = '66914dc449f0'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade():
    op.execute(
        "ALTER TYPE eventstage ADD VALUE IF NOT EXISTS 'results' BEFORE 'completed'"
    )


def downgrade() -> None:
    """Downgrade schema."""
    pass
