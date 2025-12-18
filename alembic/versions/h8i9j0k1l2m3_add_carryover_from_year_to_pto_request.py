"""add_carryover_from_year_to_pto_request

Revision ID: h8i9j0k1l2m3
Revises: g7h8i9j0k1l2
Create Date: 2025-12-17 18:00:00.000000

Adds carryover_from_year field to pto_requests table.
This tracks when a vacation request uses a previous year's balance
(e.g., a 2026 request that deducts from 2025 balance).
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'h8i9j0k1l2m3'
down_revision: Union[str, None] = 'g7h8i9j0k1l2'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Get connection to check if table/column exists
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    existing_tables = inspector.get_table_names()

    if 'pto_requests' in existing_tables:
        existing_columns = [col['name'] for col in inspector.get_columns('pto_requests')]

        if 'carryover_from_year' not in existing_columns:
            op.add_column('pto_requests', sa.Column(
                'carryover_from_year',
                sa.Integer(),
                nullable=True,
                comment="Year from which vacation balance was deducted (if different from request year)"
            ))


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    existing_tables = inspector.get_table_names()

    if 'pto_requests' in existing_tables:
        existing_columns = [col['name'] for col in inspector.get_columns('pto_requests')]

        if 'carryover_from_year' in existing_columns:
            op.drop_column('pto_requests', 'carryover_from_year')
