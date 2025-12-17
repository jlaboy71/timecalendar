"""add_pending_fields_and_soft_delete

Revision ID: a1b2c3d4e5f6
Revises: bb309210e94e
Create Date: 2025-12-14 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a1b2c3d4e5f6'
down_revision: Union[str, None] = 'bb309210e94e'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add sick_pending and personal_pending to pto_balances table
    with op.batch_alter_table('pto_balances') as batch_op:
        batch_op.add_column(sa.Column('sick_pending', sa.Numeric(5, 2), nullable=False, server_default='0.00'))
        batch_op.add_column(sa.Column('personal_pending', sa.Numeric(5, 2), nullable=False, server_default='0.00'))

    # Add deleted_at to users table for soft delete
    with op.batch_alter_table('users') as batch_op:
        batch_op.add_column(sa.Column('deleted_at', sa.DateTime(), nullable=True))
        batch_op.create_index('ix_users_deleted_at', ['deleted_at'])


def downgrade() -> None:
    # Remove deleted_at from users table
    with op.batch_alter_table('users') as batch_op:
        batch_op.drop_index('ix_users_deleted_at')
        batch_op.drop_column('deleted_at')

    # Remove sick_pending and personal_pending from pto_balances table
    with op.batch_alter_table('pto_balances') as batch_op:
        batch_op.drop_column('personal_pending')
        batch_op.drop_column('sick_pending')
