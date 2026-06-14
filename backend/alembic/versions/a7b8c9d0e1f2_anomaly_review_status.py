"""add review_status to anomalies (organizer approval gate, #2)

Revision ID: a7b8c9d0e1f2
Revises: f6a7b8c9d0e1
Create Date: 2026-06-15

"""
from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = "a7b8c9d0e1f2"
down_revision: Union[str, Sequence[str], None] = "f6a7b8c9d0e1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # New column defaults to 'pending' for future rows.
    op.execute(
        "ALTER TABLE anomalies ADD COLUMN IF NOT EXISTS "
        "review_status VARCHAR NOT NULL DEFAULT 'pending'"
    )
    # Existing anomalies pre-date the approval gate; treat them as already
    # approved so they don't silently disappear from judges' pages.
    op.execute(
        "UPDATE anomalies SET review_status = 'approved' "
        "WHERE review_status = 'pending'"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_anomalies_review_status "
        "ON anomalies (review_status)"
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_anomalies_review_status")
    op.execute("ALTER TABLE anomalies DROP COLUMN IF EXISTS review_status")
