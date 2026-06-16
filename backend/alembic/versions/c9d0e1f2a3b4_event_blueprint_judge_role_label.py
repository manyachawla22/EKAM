"""add Event.blueprint (JSONB) and Judge.role_label (Event OS, Task 3)

Revision ID: c9d0e1f2a3b4
Revises: b8c9d0e1f2a3
Create Date: 2026-06-15

"""
from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = "c9d0e1f2a3b4"
down_revision: Union[str, Sequence[str], None] = "b8c9d0e1f2a3"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Universal Event Blueprint persisted on the event (NULL = legacy/hackathon).
    op.execute("ALTER TABLE events ADD COLUMN IF NOT EXISTS blueprint JSONB")
    # Blueprint role label on the judge account (Reviewer/Investor/Jury/…).
    op.execute(
        "ALTER TABLE judges ADD COLUMN IF NOT EXISTS role_label VARCHAR DEFAULT 'Judge'"
    )


def downgrade() -> None:
    op.execute("ALTER TABLE judges DROP COLUMN IF EXISTS role_label")
    op.execute("ALTER TABLE events DROP COLUMN IF EXISTS blueprint")
