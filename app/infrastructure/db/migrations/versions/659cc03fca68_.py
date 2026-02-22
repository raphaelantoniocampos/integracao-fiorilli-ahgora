"""empty message

Revision ID: 659cc03fca68
Revises: fea995189f9d
Create Date: 2026-02-19 18:33:41.370891

"""
from typing import Sequence, Union



# revision identifiers, used by Alembic.
revision: str = '659cc03fca68'
down_revision: Union[str, Sequence[str], None] = 'fea995189f9d'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
