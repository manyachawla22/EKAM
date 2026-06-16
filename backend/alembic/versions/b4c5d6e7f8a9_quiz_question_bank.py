"""quiz / question-bank: questions + question_papers + round flags (Task 3 #8)

Revision ID: b4c5d6e7f8a9
Revises: a3b4c5d6e7f8
Create Date: 2026-06-15
"""
from typing import Sequence, Union

from alembic import op


revision: str = "b4c5d6e7f8a9"
down_revision: Union[str, Sequence[str], None] = "a3b4c5d6e7f8"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(
        "ALTER TABLE rounds ADD COLUMN IF NOT EXISTS "
        "is_quiz BOOLEAN NOT NULL DEFAULT false"
    )
    op.execute(
        "ALTER TABLE rounds ADD COLUMN IF NOT EXISTS "
        "questions_per_paper INTEGER NOT NULL DEFAULT 0"
    )
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS questions (
            id UUID PRIMARY KEY,
            round_id UUID NOT NULL REFERENCES rounds(id),
            text VARCHAR NOT NULL,
            options JSONB,
            correct_answer VARCHAR,
            marks DOUBLE PRECISION NOT NULL DEFAULT 1,
            position INTEGER DEFAULT 0,
            created_at TIMESTAMPTZ DEFAULT now()
        )
        """
    )
    op.execute("CREATE INDEX IF NOT EXISTS ix_questions_round_id ON questions(round_id)")
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS question_papers (
            id UUID PRIMARY KEY,
            round_id UUID NOT NULL REFERENCES rounds(id),
            team_id UUID NOT NULL REFERENCES teams(id),
            question_ids JSONB NOT NULL,
            created_at TIMESTAMPTZ DEFAULT now()
        )
        """
    )
    op.execute("CREATE INDEX IF NOT EXISTS ix_question_papers_round_id ON question_papers(round_id)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_question_papers_team_id ON question_papers(team_id)")


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS question_papers")
    op.execute("DROP TABLE IF EXISTS questions")
    op.execute("ALTER TABLE rounds DROP COLUMN IF EXISTS questions_per_paper")
    op.execute("ALTER TABLE rounds DROP COLUMN IF EXISTS is_quiz")
