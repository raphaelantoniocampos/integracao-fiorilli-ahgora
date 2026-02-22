"""add tasks

Revision ID: fea995189f9d
Revises: 8ac02544319a
Create Date: 2026-02-19 18:14:27.021616

"""

from typing import Sequence, Union


# revision identifiers, used by Alembic.
revision: str = "fea995189f9d"
down_revision: Union[str, Sequence[str], None] = "8ac02544319a"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
