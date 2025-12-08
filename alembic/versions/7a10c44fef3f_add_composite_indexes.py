"""add_composite_indexes

Revision ID: 7a10c44fef3f
Revises: ddb4525455a7
Create Date: 2025-12-07 21:11:26.210387

Adds composite indexes for common query patterns:
- pto_requests (user_id, status) - for fetching user requests by status
- pto_requests (status, start_date, end_date) - for date range queries by status
- audit_logs (action, created_at) - for filtered audit log queries
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '7a10c44fef3f'
down_revision: Union[str, None] = 'ddb4525455a7'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add composite indexes to pto_requests table
    with op.batch_alter_table('pto_requests', schema=None) as batch_op:
        batch_op.create_index('ix_pto_requests_user_status', ['user_id', 'status'], unique=False)
        batch_op.create_index('ix_pto_requests_status_dates', ['status', 'start_date', 'end_date'], unique=False)

    # Add composite index to audit_logs for filtered queries
    with op.batch_alter_table('audit_logs', schema=None) as batch_op:
        batch_op.create_index('ix_audit_logs_action_created', ['action', 'created_at'], unique=False)


def downgrade() -> None:
    # Remove composite indexes from audit_logs table
    with op.batch_alter_table('audit_logs', schema=None) as batch_op:
        batch_op.drop_index('ix_audit_logs_action_created')

    # Remove composite indexes from pto_requests table
    with op.batch_alter_table('pto_requests', schema=None) as batch_op:
        batch_op.drop_index('ix_pto_requests_status_dates')
        batch_op.drop_index('ix_pto_requests_user_status')
