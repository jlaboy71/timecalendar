"""remove_chicago_safe_leave

Revision ID: e5f6g7h8i9j0
Revises: d4e5f6g7h8i9
Create Date: 2025-12-17 12:00:00.000000

Removes the deprecated chicago_safe_leave_* columns from pto_balances.
These columns were redundant because:
- Company Sick Leave = Chicago Sick & Safe Leave (same bank, uses sick_* fields)
- Only Chicago Paid Leave (chicago_paid_leave_*) is a separate bank
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'e5f6g7h8i9j0'
down_revision: Union[str, None] = 'd4e5f6g7h8i9'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Get connection to check if columns exist
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    existing_tables = inspector.get_table_names()

    # Remove deprecated chicago_safe_leave_* columns from pto_balances
    if 'pto_balances' in existing_tables:
        existing_columns = [col['name'] for col in inspector.get_columns('pto_balances')]

        if 'chicago_safe_leave_carryover' in existing_columns:
            op.drop_column('pto_balances', 'chicago_safe_leave_carryover')
        if 'chicago_safe_leave_pending' in existing_columns:
            op.drop_column('pto_balances', 'chicago_safe_leave_pending')
        if 'chicago_safe_leave_used' in existing_columns:
            op.drop_column('pto_balances', 'chicago_safe_leave_used')
        if 'chicago_safe_leave_total' in existing_columns:
            op.drop_column('pto_balances', 'chicago_safe_leave_total')


def downgrade() -> None:
    # Re-add the columns if needed (for rollback)
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    existing_tables = inspector.get_table_names()

    if 'pto_balances' in existing_tables:
        existing_columns = [col['name'] for col in inspector.get_columns('pto_balances')]

        if 'chicago_safe_leave_total' not in existing_columns:
            op.add_column('pto_balances', sa.Column(
                'chicago_safe_leave_total',
                sa.Numeric(5, 2),
                nullable=False,
                server_default='0.00'
            ))

        if 'chicago_safe_leave_used' not in existing_columns:
            op.add_column('pto_balances', sa.Column(
                'chicago_safe_leave_used',
                sa.Numeric(5, 2),
                nullable=False,
                server_default='0.00'
            ))

        if 'chicago_safe_leave_pending' not in existing_columns:
            op.add_column('pto_balances', sa.Column(
                'chicago_safe_leave_pending',
                sa.Numeric(5, 2),
                nullable=False,
                server_default='0.00'
            ))

        if 'chicago_safe_leave_carryover' not in existing_columns:
            op.add_column('pto_balances', sa.Column(
                'chicago_safe_leave_carryover',
                sa.Numeric(5, 2),
                nullable=False,
                server_default='0.00'
            ))
