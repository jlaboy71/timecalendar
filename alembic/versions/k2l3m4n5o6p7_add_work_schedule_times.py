"""add_work_schedule_times

Revision ID: k2l3m4n5o6p7
Revises: j1k2l3m4n5o6
Create Date: 2025-12-21 18:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'k2l3m4n5o6p7'
down_revision: Union[str, None] = 'j1k2l3m4n5o6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add work_start_time and work_end_time columns to users table
    op.add_column('users', sa.Column('work_start_time', sa.Time(), nullable=True))
    op.add_column('users', sa.Column('work_end_time', sa.Time(), nullable=True))


def downgrade() -> None:
    op.drop_column('users', 'work_end_time')
    op.drop_column('users', 'work_start_time')
