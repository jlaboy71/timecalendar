"""add_wfh_day_swap_table

Revision ID: 10519844fdc1
Revises: h8i9j0k1l2m3
Create Date: 2025-12-21 14:31:03.060407

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '10519844fdc1'
down_revision: Union[str, None] = 'h8i9j0k1l2m3'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create wfh_day_swap_requests table
    op.create_table(
        'wfh_day_swap_requests',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('requester_id', sa.Integer(), nullable=False),
        sa.Column('target_user_id', sa.Integer(), nullable=False),
        sa.Column('swap_date', sa.Date(), nullable=False),
        sa.Column('requester_original_day', sa.String(10), nullable=False),
        sa.Column('target_original_day', sa.String(10), nullable=False),
        sa.Column('status', sa.String(20), nullable=False, server_default='pending'),
        sa.Column('request_message', sa.Text(), nullable=False),
        sa.Column('response_message', sa.Text(), nullable=True),
        sa.Column('requested_at', sa.DateTime(), nullable=False),
        sa.Column('responded_at', sa.DateTime(), nullable=True),
        sa.Column('expires_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['requester_id'], ['users.id']),
        sa.ForeignKeyConstraint(['target_user_id'], ['users.id']),
        sa.PrimaryKeyConstraint('id')
    )

    # Create indexes for performance
    op.create_index('ix_wfh_swap_id', 'wfh_day_swap_requests', ['id'])
    op.create_index('ix_wfh_swap_requester_id', 'wfh_day_swap_requests', ['requester_id'])
    op.create_index('ix_wfh_swap_target_user_id', 'wfh_day_swap_requests', ['target_user_id'])
    op.create_index('ix_wfh_swap_swap_date', 'wfh_day_swap_requests', ['swap_date'])
    op.create_index('ix_wfh_swap_status', 'wfh_day_swap_requests', ['status'])
    op.create_index('ix_wfh_swap_requested_at', 'wfh_day_swap_requests', ['requested_at'])
    op.create_index('idx_wfh_swap_date_status', 'wfh_day_swap_requests', ['swap_date', 'status'])
    op.create_index('idx_wfh_swap_requester_status', 'wfh_day_swap_requests', ['requester_id', 'status'])
    op.create_index('idx_wfh_swap_target_status', 'wfh_day_swap_requests', ['target_user_id', 'status'])


def downgrade() -> None:
    # Drop indexes first
    op.drop_index('idx_wfh_swap_target_status', table_name='wfh_day_swap_requests')
    op.drop_index('idx_wfh_swap_requester_status', table_name='wfh_day_swap_requests')
    op.drop_index('idx_wfh_swap_date_status', table_name='wfh_day_swap_requests')
    op.drop_index('ix_wfh_swap_requested_at', table_name='wfh_day_swap_requests')
    op.drop_index('ix_wfh_swap_status', table_name='wfh_day_swap_requests')
    op.drop_index('ix_wfh_swap_swap_date', table_name='wfh_day_swap_requests')
    op.drop_index('ix_wfh_swap_target_user_id', table_name='wfh_day_swap_requests')
    op.drop_index('ix_wfh_swap_requester_id', table_name='wfh_day_swap_requests')
    op.drop_index('ix_wfh_swap_id', table_name='wfh_day_swap_requests')

    # Drop the table
    op.drop_table('wfh_day_swap_requests')
