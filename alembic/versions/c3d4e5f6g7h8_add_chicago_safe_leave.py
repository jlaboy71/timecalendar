"""add_chicago_safe_leave

Revision ID: c3d4e5f6g7h8
Revises: b2c3d4e5f6g7
Create Date: 2025-12-14 16:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c3d4e5f6g7h8'
down_revision: Union[str, None] = 'b2c3d4e5f6g7'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Get connection to check if tables/columns exist
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    existing_tables = inspector.get_table_names()

    # Add Chicago Safe Leave columns to pto_balances table
    if 'pto_balances' in existing_tables:
        existing_columns = [col['name'] for col in inspector.get_columns('pto_balances')]

        if 'chicago_safe_leave_total' not in existing_columns:
            op.add_column('pto_balances', sa.Column(
                'chicago_safe_leave_total',
                sa.Numeric(5, 2),
                nullable=False,
                server_default='0.00',
                comment='Chicago Safe Leave hours allocated for the year'
            ))

        if 'chicago_safe_leave_used' not in existing_columns:
            op.add_column('pto_balances', sa.Column(
                'chicago_safe_leave_used',
                sa.Numeric(5, 2),
                nullable=False,
                server_default='0.00',
                comment='Chicago Safe Leave hours used'
            ))

        if 'chicago_safe_leave_pending' not in existing_columns:
            op.add_column('pto_balances', sa.Column(
                'chicago_safe_leave_pending',
                sa.Numeric(5, 2),
                nullable=False,
                server_default='0.00',
                comment='Chicago Safe Leave hours in pending requests'
            ))

        if 'chicago_safe_leave_carryover' not in existing_columns:
            op.add_column('pto_balances', sa.Column(
                'chicago_safe_leave_carryover',
                sa.Numeric(5, 2),
                nullable=False,
                server_default='0.00',
                comment='Chicago Safe Leave hours carried over (max 16 hrs per ordinance)'
            ))

    # Create system_settings table for feature toggles
    if 'system_settings' not in existing_tables:
        op.create_table(
            'system_settings',
            sa.Column('id', sa.Integer(), primary_key=True),
            sa.Column('key', sa.String(100), unique=True, nullable=False, index=True),
            sa.Column('value', sa.Text(), nullable=False),
            sa.Column('description', sa.Text(), nullable=True),
            sa.Column('updated_by', sa.Integer(), nullable=True),
            sa.Column('updated_at', sa.DateTime(), server_default=sa.func.now(), onupdate=sa.func.now()),
            sa.Column('created_at', sa.DateTime(), server_default=sa.func.now())
        )

        # Insert default Chicago Safe Leave toggle (disabled by default)
        op.execute(
            "INSERT INTO system_settings (key, value, description) VALUES "
            "('chicago.safe_leave_enabled', 'false', 'Enable Chicago Paid Sick and Safe Leave feature for Chicago employees')"
        )


def downgrade() -> None:
    # Get connection to check if tables/columns exist
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    existing_tables = inspector.get_table_names()

    # Drop system_settings table
    if 'system_settings' in existing_tables:
        op.drop_table('system_settings')

    # Remove Chicago Safe Leave columns from pto_balances
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
