"""merge heads

Revision ID: 26fb821af9c7
Revises: 285044eddddd, e7d4b09a7c01
Create Date: 2026-05-31 00:53:47.576198

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '26fb821af9c7'
down_revision: Union[str, Sequence[str], None] = ('285044eddddd', 'e7d4b09a7c01')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
