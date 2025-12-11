"""add_is_private_to_pto_requests

Revision ID: ef06ced76495
Revises: 7a10c44fef3f
Create Date: 2025-12-10 21:01:02.966126

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'ef06ced76495'
down_revision: Union[str, None] = '7a10c44fef3f'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('pto_requests', sa.Column('is_private', sa.Boolean(), nullable=False, server_default='0'))


def downgrade() -> None:
    op.drop_column('pto_requests', 'is_private')
