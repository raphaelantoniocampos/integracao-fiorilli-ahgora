"""empty message

Revision ID: 6f9b6a2a7856
Revises: 659cc03fca68
Create Date: 2026-02-19 18:34:28.106644

"""

from typing import Sequence, Union


# revision identifiers, used by Alembic.
revision: str = "6f9b6a2a7856"
down_revision: Union[str, Sequence[str], None] = "659cc03fca68"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
