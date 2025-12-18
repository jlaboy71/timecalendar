"""add_auto_notify_report_frequency

Revision ID: f6g7h8i9j0k1
Revises: e5f6g7h8i9j0
Create Date: 2025-12-17 14:00:00.000000

Adds auto_notify_report_frequency field to manager_notification_preferences.
This allows managers to choose how often they receive trusted employee auto-approve reports.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'f6g7h8i9j0k1'
down_revision: Union[str, None] = 'e5f6g7h8i9j0'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Get connection to check if table/column exists
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    existing_tables = inspector.get_table_names()

    if 'manager_notification_preferences' in existing_tables:
        existing_columns = [col['name'] for col in inspector.get_columns('manager_notification_preferences')]

        if 'auto_notify_report_frequency' not in existing_columns:
            op.add_column('manager_notification_preferences', sa.Column(
                'auto_notify_report_frequency',
                sa.String(20),
                nullable=False,
                server_default='weekly'
            ))


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    existing_tables = inspector.get_table_names()

    if 'manager_notification_preferences' in existing_tables:
        existing_columns = [col['name'] for col in inspector.get_columns('manager_notification_preferences')]

        if 'auto_notify_report_frequency' in existing_columns:
            op.drop_column('manager_notification_preferences', 'auto_notify_report_frequency')
