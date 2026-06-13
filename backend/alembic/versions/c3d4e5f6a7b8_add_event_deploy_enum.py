"""add event_deploy to requesttype enum (gated AI deploy, option C)

Stacked as its own revision because b2c3d4e5f6a7 may already have been applied
*before* the event_deploy value was added to it — and Alembic never re-runs an
applied migration. This guarantees `event_deploy` exists regardless of when the
prior upgrade ran. Idempotent (IF NOT EXISTS), so it's a no-op on a fresh DB
that already got the value from b2c3d4e5f6a7.

Revision ID: c3d4e5f6a7b8
Revises: b2c3d4e5f6a7
Create Date: 2026-06-13

"""
from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = "c3d4e5f6a7b8"
down_revision: Union[str, Sequence[str], None] = "b2c3d4e5f6a7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ALTER TYPE ... ADD VALUE must run outside the migration transaction.
    with op.get_context().autocommit_block():
        op.execute("ALTER TYPE requesttype ADD VALUE IF NOT EXISTS 'event_deploy'")


def downgrade() -> None:
    # Postgres cannot drop an enum value — leave it in place (harmless).
    pass
