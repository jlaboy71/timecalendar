"""add_performance_indexes

Revision ID: ddb4525455a7
Revises: d1d45e7991f9
Create Date: 2025-12-07 19:36:19.886118

Adds indexes on frequently queried columns for performance optimization:
- users.department_id - for team/department queries
- users.role - for role-based access control queries
- users.is_active - for filtering active employees
- carryover_requests.status - for filtering pending requests
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'ddb4525455a7'
down_revision: Union[str, None] = 'd1d45e7991f9'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add indexes to users table
    with op.batch_alter_table('users', schema=None) as batch_op:
        batch_op.create_index('ix_users_department_id', ['department_id'], unique=False)
        batch_op.create_index('ix_users_role', ['role'], unique=False)
        batch_op.create_index('ix_users_is_active', ['is_active'], unique=False)

    # Add index to carryover_requests table
    with op.batch_alter_table('carryover_requests', schema=None) as batch_op:
        batch_op.create_index('ix_carryover_requests_status', ['status'], unique=False)


def downgrade() -> None:
    # Remove indexes from carryover_requests table
    with op.batch_alter_table('carryover_requests', schema=None) as batch_op:
        batch_op.drop_index('ix_carryover_requests_status')

    # Remove indexes from users table
    with op.batch_alter_table('users', schema=None) as batch_op:
        batch_op.drop_index('ix_users_is_active')
        batch_op.drop_index('ix_users_role')
        batch_op.drop_index('ix_users_department_id')
