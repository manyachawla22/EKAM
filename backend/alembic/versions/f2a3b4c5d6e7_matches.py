"""create matches table (tournament bracket, Task 3 Stage 5c)

Revision ID: f2a3b4c5d6e7
Revises: e1f2a3b4c5d6
Create Date: 2026-06-15

"""
from typing import Sequence, Union

from alembic import op


revision: str = "f2a3b4c5d6e7"
down_revision: Union[str, Sequence[str], None] = "e1f2a3b4c5d6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS matches (
            id              UUID PRIMARY KEY,
            event_id        UUID NOT NULL REFERENCES events(id) ON DELETE CASCADE,
            round_id        UUID REFERENCES rounds(id) ON DELETE CASCADE,
            round_number    INTEGER NOT NULL DEFAULT 1,
            match_index     INTEGER NOT NULL DEFAULT 0,
            side_a_team_id  UUID REFERENCES teams(id) ON DELETE SET NULL,
            side_b_team_id  UUID REFERENCES teams(id) ON DELETE SET NULL,
            scheduled_at    TIMESTAMPTZ,
            match_link      VARCHAR,
            status          VARCHAR NOT NULL DEFAULT 'pending',
            winner_team_id  UUID REFERENCES teams(id) ON DELETE SET NULL,
            score_a         DOUBLE PRECISION,
            score_b         DOUBLE PRECISION,
            next_match_id   UUID REFERENCES matches(id) ON DELETE SET NULL,
            next_slot       VARCHAR,
            created_at      TIMESTAMPTZ DEFAULT now()
        )
        """
    )
    op.execute("CREATE INDEX IF NOT EXISTS ix_matches_event_id ON matches (event_id)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_matches_round_id ON matches (round_id)")


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS matches")
