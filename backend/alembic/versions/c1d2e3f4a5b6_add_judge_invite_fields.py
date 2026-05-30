"""add_judge_invite_fields

Revision ID: c1d2e3f4a5b6
Revises: e028d17a2b40
Create Date: 2026-05-31 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = 'c1d2e3f4a5b6'
down_revision: Union[str, Sequence[str], None] = 'e028d17a2b40'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        'judges',
        sa.Column('invite_token', postgresql.UUID(as_uuid=True), nullable=True)
    )
    op.add_column(
        'judges',
        sa.Column('invite_status', sa.String(), server_default='pending', nullable=False)
    )
    op.create_index('ix_judges_invite_token', 'judges', ['invite_token'], unique=True)


def downgrade() -> None:
    op.drop_index('ix_judges_invite_token', table_name='judges')
    op.drop_column('judges', 'invite_status')
    op.drop_column('judges', 'invite_token')
