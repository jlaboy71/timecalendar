"""add_wfh_swap_eligible

Revision ID: j1k2l3m4n5o6
Revises: 10519844fdc1
Create Date: 2025-12-21 16:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'j1k2l3m4n5o6'
down_revision: Union[str, None] = '10519844fdc1'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add wfh_swap_eligible column to users table
    # Default to True so existing users can swap
    op.add_column('users', sa.Column(
        'wfh_swap_eligible',
        sa.Boolean(),
        nullable=False,
        server_default='1'  # SQLite uses 1 for True
    ))


def downgrade() -> None:
    op.drop_column('users', 'wfh_swap_eligible')
