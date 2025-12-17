"""add_chicago_paid_leave

Revision ID: d4e5f6g7h8i9
Revises: c3d4e5f6g7h8
Create Date: 2025-12-15 10:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'd4e5f6g7h8i9'
down_revision: Union[str, None] = 'c3d4e5f6g7h8'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Get connection to check if tables/columns exist
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    existing_tables = inspector.get_table_names()

    # Add Chicago Paid Leave columns to pto_balances table
    # This is the "Paid Leave for Any Reason" bucket with 16hr max carryover
    if 'pto_balances' in existing_tables:
        existing_columns = [col['name'] for col in inspector.get_columns('pto_balances')]

        if 'chicago_paid_leave_total' not in existing_columns:
            op.add_column('pto_balances', sa.Column(
                'chicago_paid_leave_total',
                sa.Numeric(5, 2),
                nullable=False,
                server_default='0.00',
                comment='Chicago Paid Leave hours allocated for the year (40hr max)'
            ))

        if 'chicago_paid_leave_used' not in existing_columns:
            op.add_column('pto_balances', sa.Column(
                'chicago_paid_leave_used',
                sa.Numeric(5, 2),
                nullable=False,
                server_default='0.00',
                comment='Chicago Paid Leave hours used'
            ))

        if 'chicago_paid_leave_pending' not in existing_columns:
            op.add_column('pto_balances', sa.Column(
                'chicago_paid_leave_pending',
                sa.Numeric(5, 2),
                nullable=False,
                server_default='0.00',
                comment='Chicago Paid Leave hours in pending requests'
            ))

        if 'chicago_paid_leave_carryover' not in existing_columns:
            op.add_column('pto_balances', sa.Column(
                'chicago_paid_leave_carryover',
                sa.Numeric(5, 2),
                nullable=False,
                server_default='0.00',
                comment='Chicago Paid Leave hours carried over (max 16 hrs per ordinance)'
            ))


def downgrade() -> None:
    # Get connection to check if tables/columns exist
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    existing_tables = inspector.get_table_names()

    # Remove Chicago Paid Leave columns from pto_balances
    if 'pto_balances' in existing_tables:
        existing_columns = [col['name'] for col in inspector.get_columns('pto_balances')]

        if 'chicago_paid_leave_carryover' in existing_columns:
            op.drop_column('pto_balances', 'chicago_paid_leave_carryover')
        if 'chicago_paid_leave_pending' in existing_columns:
            op.drop_column('pto_balances', 'chicago_paid_leave_pending')
        if 'chicago_paid_leave_used' in existing_columns:
            op.drop_column('pto_balances', 'chicago_paid_leave_used')
        if 'chicago_paid_leave_total' in existing_columns:
            op.drop_column('pto_balances', 'chicago_paid_leave_total')
