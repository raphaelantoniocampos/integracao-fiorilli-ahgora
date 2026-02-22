"""empty message

Revision ID: e0ffc93aa593
Revises: 6f9b6a2a7856
Create Date: 2026-02-19 20:07:22.447942

"""

from typing import Sequence, Union


# revision identifiers, used by Alembic.
revision: str = "e0ffc93aa593"
down_revision: Union[str, Sequence[str], None] = "6f9b6a2a7856"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
