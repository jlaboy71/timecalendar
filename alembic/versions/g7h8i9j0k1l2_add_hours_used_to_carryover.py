"""add_hours_used_to_carryover

Revision ID: g7h8i9j0k1l2
Revises: f6g7h8i9j0k1
Create Date: 2025-12-17 16:00:00.000000

Adds hours_used field to carryover_requests table.
This tracks how much of the approved carryover has been consumed,
allowing deduction from the FROM year's balance.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'g7h8i9j0k1l2'
down_revision: Union[str, None] = 'f6g7h8i9j0k1'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Get connection to check if table/column exists
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    existing_tables = inspector.get_table_names()

    if 'carryover_requests' in existing_tables:
        existing_columns = [col['name'] for col in inspector.get_columns('carryover_requests')]

        if 'hours_used' not in existing_columns:
            op.add_column('carryover_requests', sa.Column(
                'hours_used',
                sa.Numeric(5, 2),
                nullable=False,
                server_default='0.00'
            ))


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    existing_tables = inspector.get_table_names()

    if 'carryover_requests' in existing_tables:
        existing_columns = [col['name'] for col in inspector.get_columns('carryover_requests')]

        if 'hours_used' in existing_columns:
            op.drop_column('carryover_requests', 'hours_used')
