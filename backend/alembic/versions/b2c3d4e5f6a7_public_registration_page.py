"""public registration page columns + registration_form approval type

Task 6 — public, no-login registration page.

- events: registration_form_fields (JSON), participants_model, individual_registration_allowed, eligibility (JSON)
- participants: registration_data (JSON), resume_url
- requesttype enum: add 'registration_form' and 'event_deploy' values

Revision ID: b2c3d4e5f6a7
Revises: a1b2c3d4e5f6
Create Date: 2026-06-13

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = "b2c3d4e5f6a7"
down_revision: Union[str, Sequence[str], None] = "a1b2c3d4e5f6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ── events: public-form spec (all nullable / defaulted so existing rows backfill) ──
    op.add_column(
        "events",
        sa.Column("registration_form_fields", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    )
    op.add_column(
        "events",
        sa.Column("participants_model", sa.String(), nullable=True, server_default="individual"),
    )
    op.add_column(
        "events",
        sa.Column(
            "individual_registration_allowed",
            sa.Boolean(),
            nullable=True,
            server_default=sa.true(),
        ),
    )
    op.add_column(
        "events",
        sa.Column("eligibility", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    )

    # ── participants: custom answers + resume ──
    op.add_column(
        "participants",
        sa.Column("registration_data", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    )
    op.add_column(
        "participants",
        sa.Column("resume_url", sa.String(), nullable=True),
    )

    # ── requesttype enum: add 'registration_form' + 'event_deploy' ──
    # ALTER TYPE ... ADD VALUE can't run inside a transaction block on older PG;
    # autocommit_block() is the Alembic-blessed way to step outside the migration
    # transaction. IF NOT EXISTS makes it safe to re-run.
    with op.get_context().autocommit_block():
        op.execute("ALTER TYPE requesttype ADD VALUE IF NOT EXISTS 'registration_form'")
        op.execute("ALTER TYPE requesttype ADD VALUE IF NOT EXISTS 'event_deploy'")


def downgrade() -> None:
    # Note: Postgres cannot drop an enum value; the 'registration_form' value is
    # left in place on downgrade (harmless — nothing references it once columns
    # are dropped).
    op.drop_column("participants", "resume_url")
    op.drop_column("participants", "registration_data")
    op.drop_column("events", "eligibility")
    op.drop_column("events", "individual_registration_allowed")
    op.drop_column("events", "participants_model")
    op.drop_column("events", "registration_form_fields")
