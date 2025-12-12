"""add_cancellation_request_fields

Revision ID: 778c50a4fe1c
Revises: ef06ced76495
Create Date: 2025-12-12 10:13:25.218506

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '778c50a4fe1c'
down_revision: Union[str, None] = 'ef06ced76495'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add cancellation request tracking fields to pto_requests
    op.add_column('pto_requests', sa.Column('cancellation_requested', sa.Boolean(), nullable=False, server_default='0'))
    op.add_column('pto_requests', sa.Column('cancellation_reason', sa.Text(), nullable=True))
    op.add_column('pto_requests', sa.Column('cancellation_requested_at', sa.DateTime(), nullable=True))


def downgrade() -> None:
    op.drop_column('pto_requests', 'cancellation_requested_at')
    op.drop_column('pto_requests', 'cancellation_reason')
    op.drop_column('pto_requests', 'cancellation_requested')
