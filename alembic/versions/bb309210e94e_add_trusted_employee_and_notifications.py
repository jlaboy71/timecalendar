"""add_trusted_employee_and_notifications

Revision ID: bb309210e94e
Revises: 778c50a4fe1c
Create Date: 2025-12-13 12:06:29.216907

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'bb309210e94e'
down_revision: Union[str, None] = '778c50a4fe1c'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add trusted employee fields to users table (using batch mode for SQLite FK support)
    with op.batch_alter_table('users') as batch_op:
        batch_op.add_column(sa.Column('is_trusted', sa.Boolean(), nullable=False, server_default='0'))
        batch_op.add_column(sa.Column('trusted_by_id', sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column('trusted_at', sa.DateTime(), nullable=True))

    # Create manager notification preferences table
    op.create_table(
        'manager_notification_preferences',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('manager_id', sa.Integer(), sa.ForeignKey('users.id'), unique=True, nullable=False),
        sa.Column('digest_frequency', sa.String(20), nullable=False, server_default='immediate'),
        sa.Column('preferred_hour', sa.Integer(), nullable=False, server_default='8'),
        sa.Column('preferred_day', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('export_format', sa.String(10), nullable=False, server_default='pdf'),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.func.now())
    )
    op.create_index('ix_manager_notification_preferences_manager_id', 'manager_notification_preferences', ['manager_id'])

    # Create pending notifications queue table
    op.create_table(
        'pending_notifications',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('manager_id', sa.Integer(), sa.ForeignKey('users.id'), nullable=False),
        sa.Column('pto_request_id', sa.Integer(), sa.ForeignKey('pto_requests.id'), nullable=False),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now()),
        sa.Column('sent', sa.Boolean(), nullable=False, server_default='0'),
        sa.Column('sent_at', sa.DateTime(), nullable=True)
    )
    op.create_index('ix_pending_notifications_manager_id', 'pending_notifications', ['manager_id'])
    op.create_index('ix_pending_notifications_pto_request_id', 'pending_notifications', ['pto_request_id'])
    op.create_index('ix_pending_notifications_manager_sent', 'pending_notifications', ['manager_id', 'sent'])


def downgrade() -> None:
    # Drop pending notifications table
    op.drop_index('ix_pending_notifications_manager_sent', 'pending_notifications')
    op.drop_index('ix_pending_notifications_pto_request_id', 'pending_notifications')
    op.drop_index('ix_pending_notifications_manager_id', 'pending_notifications')
    op.drop_table('pending_notifications')

    # Drop manager notification preferences table
    op.drop_index('ix_manager_notification_preferences_manager_id', 'manager_notification_preferences')
    op.drop_table('manager_notification_preferences')

    # Remove trusted employee fields from users table (using batch mode for SQLite)
    with op.batch_alter_table('users') as batch_op:
        batch_op.drop_column('trusted_at')
        batch_op.drop_column('trusted_by_id')
        batch_op.drop_column('is_trusted')
