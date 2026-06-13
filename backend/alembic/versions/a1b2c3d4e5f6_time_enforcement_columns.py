"""time enforcement columns

Adds the registration window to events and disqualification flags to teams,
supporting strict time enforcement (Task 2).

Revision ID: a1b2c3d4e5f6
Revises: 47320f90e008
Create Date: 2026-06-13

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "a1b2c3d4e5f6"
down_revision: Union[str, Sequence[str], None] = "47320f90e008"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Event registration window (UTC), nullable → events without a window stay
    # always-open.
    op.add_column(
        "events",
        sa.Column("registration_opens_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "events",
        sa.Column("registration_closes_at", sa.DateTime(timezone=True), nullable=True),
    )

    # Team disqualification. server_default='false' backfills existing rows;
    # the column is NOT NULL to match the model.
    op.add_column(
        "teams",
        sa.Column(
            "disqualified",
            sa.Boolean(),
            nullable=False,
            server_default=sa.false(),
        ),
    )
    op.add_column(
        "teams",
        sa.Column("disqualified_reason", sa.String(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("teams", "disqualified_reason")
    op.drop_column("teams", "disqualified")
    op.drop_column("events", "registration_closes_at")
    op.drop_column("events", "registration_opens_at")
