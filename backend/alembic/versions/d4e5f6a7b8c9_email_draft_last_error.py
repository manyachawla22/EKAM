"""add last_error column to email_drafts (record Resend failure reason)

Lets a failed send store the Resend exception text on the draft row so failures
are diagnosable from the DB, not only the backend console.

Revision ID: d4e5f6a7b8c9
Revises: c3d4e5f6a7b8
Create Date: 2026-06-14

"""
from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = "d4e5f6a7b8c9"
down_revision: Union[str, Sequence[str], None] = "c3d4e5f6a7b8"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Idempotent: a no-op if create_all already added the column on a fresh DB.
    op.execute("ALTER TABLE email_drafts ADD COLUMN IF NOT EXISTS last_error VARCHAR")


def downgrade() -> None:
    op.execute("ALTER TABLE email_drafts DROP COLUMN IF EXISTS last_error")
