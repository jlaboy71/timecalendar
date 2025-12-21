"""add_policy_change_tracking

Revision ID: b2c3d4e5f6g7
Revises: a1b2c3d4e5f6
Create Date: 2025-12-14 14:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b2c3d4e5f6g7'
down_revision: Union[str, None] = 'a1b2c3d4e5f6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Get connection to check if tables/indexes exist
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    existing_tables = inspector.get_table_names()

    # Create handbook_uploads table first (referenced by policy_change_logs)
    if 'handbook_uploads' not in existing_tables:
        op.create_table(
            'handbook_uploads',
            sa.Column('id', sa.Integer(), primary_key=True),
            sa.Column('version', sa.String(20), nullable=False, unique=True),
            sa.Column('filename', sa.String(255), nullable=False),
            sa.Column('file_path', sa.String(500), nullable=False),
            sa.Column('file_hash', sa.String(64), nullable=False),
            sa.Column('file_size', sa.Integer(), nullable=False),
            sa.Column('extracted_policies', sa.JSON(), nullable=True),
            sa.Column('ai_analysis', sa.JSON(), nullable=True),
            sa.Column('ai_summary', sa.Text(), nullable=True),
            sa.Column('status', sa.String(20), nullable=False, server_default='pending'),
            sa.Column('error_message', sa.Text(), nullable=True),
            sa.Column('uploaded_by', sa.Integer(), sa.ForeignKey('users.id'), nullable=False),
            sa.Column('uploaded_at', sa.DateTime(), server_default=sa.func.now()),
            sa.Column('published_at', sa.DateTime(), nullable=True),
            sa.Column('published_by', sa.Integer(), sa.ForeignKey('users.id'), nullable=True),
            sa.Column('is_revert_of', sa.Integer(), sa.ForeignKey('handbook_uploads.id'), nullable=True),
            sa.Column('detected_duplicate_of', sa.String(20), nullable=True)
        )

        # Create indexes for newly created table
        op.create_index('ix_handbook_uploads_file_hash', 'handbook_uploads', ['file_hash'])
        op.create_index('ix_handbook_uploads_status', 'handbook_uploads', ['status'])
        op.create_index('ix_handbook_uploads_version', 'handbook_uploads', ['version'])
    else:
        # Check for missing indexes on existing table
        handbook_indexes = [idx['name'] for idx in inspector.get_indexes('handbook_uploads')]
        if 'ix_handbook_uploads_file_hash' not in handbook_indexes:
            op.create_index('ix_handbook_uploads_file_hash', 'handbook_uploads', ['file_hash'])
        if 'ix_handbook_uploads_status' not in handbook_indexes:
            op.create_index('ix_handbook_uploads_status', 'handbook_uploads', ['status'])
        if 'ix_handbook_uploads_version' not in handbook_indexes:
            op.create_index('ix_handbook_uploads_version', 'handbook_uploads', ['version'])

    # Create policy_change_logs table
    if 'policy_change_logs' not in existing_tables:
        op.create_table(
            'policy_change_logs',
            sa.Column('id', sa.Integer(), primary_key=True),
            sa.Column('handbook_version', sa.String(20), nullable=False),
            sa.Column('policy_type', sa.String(50), nullable=False),
            sa.Column('location_state', sa.String(2), nullable=True),
            sa.Column('location_city', sa.String(50), nullable=True),
            sa.Column('old_value', sa.String(100), nullable=False),
            sa.Column('new_value', sa.String(100), nullable=False),
            sa.Column('old_value_display', sa.String(100), nullable=False),
            sa.Column('new_value_display', sa.String(100), nullable=False),
            sa.Column('effective_date', sa.Date(), nullable=False),
            sa.Column('reason', sa.Text(), nullable=True),
            sa.Column('ai_summary', sa.Text(), nullable=True),
            sa.Column('changed_by', sa.Integer(), sa.ForeignKey('users.id'), nullable=False),
            sa.Column('created_at', sa.DateTime(), server_default=sa.func.now()),
            sa.Column('expires_at', sa.DateTime(), nullable=False),
            sa.Column('is_revert', sa.Boolean(), nullable=False, server_default='0'),
            sa.Column('reverted_to_version', sa.String(20), nullable=True),
            sa.Column('handbook_upload_id', sa.Integer(), sa.ForeignKey('handbook_uploads.id'), nullable=True)
        )

        # Create indexes for newly created table
        op.create_index('ix_policy_change_logs_policy_type', 'policy_change_logs', ['policy_type'])
        op.create_index('ix_policy_change_logs_location_state', 'policy_change_logs', ['location_state'])
        op.create_index('ix_policy_change_logs_expires_at', 'policy_change_logs', ['expires_at'])
        op.create_index('ix_policy_change_logs_handbook_version', 'policy_change_logs', ['handbook_version'])
    else:
        # Check for missing indexes on existing table
        policy_indexes = [idx['name'] for idx in inspector.get_indexes('policy_change_logs')]
        if 'ix_policy_change_logs_policy_type' not in policy_indexes:
            op.create_index('ix_policy_change_logs_policy_type', 'policy_change_logs', ['policy_type'])
        if 'ix_policy_change_logs_location_state' not in policy_indexes:
            op.create_index('ix_policy_change_logs_location_state', 'policy_change_logs', ['location_state'])
        if 'ix_policy_change_logs_expires_at' not in policy_indexes:
            op.create_index('ix_policy_change_logs_expires_at', 'policy_change_logs', ['expires_at'])
        if 'ix_policy_change_logs_handbook_version' not in policy_indexes:
            op.create_index('ix_policy_change_logs_handbook_version', 'policy_change_logs', ['handbook_version'])


def downgrade() -> None:
    # Get connection to check if tables exist
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    existing_tables = inspector.get_table_names()

    # Drop policy_change_logs table and indexes
    if 'policy_change_logs' in existing_tables:
        policy_indexes = [idx['name'] for idx in inspector.get_indexes('policy_change_logs')]
        if 'ix_policy_change_logs_handbook_version' in policy_indexes:
            op.drop_index('ix_policy_change_logs_handbook_version', 'policy_change_logs')
        if 'ix_policy_change_logs_expires_at' in policy_indexes:
            op.drop_index('ix_policy_change_logs_expires_at', 'policy_change_logs')
        if 'ix_policy_change_logs_location_state' in policy_indexes:
            op.drop_index('ix_policy_change_logs_location_state', 'policy_change_logs')
        if 'ix_policy_change_logs_policy_type' in policy_indexes:
            op.drop_index('ix_policy_change_logs_policy_type', 'policy_change_logs')
        op.drop_table('policy_change_logs')

    # Drop handbook_uploads table and indexes
    if 'handbook_uploads' in existing_tables:
        handbook_indexes = [idx['name'] for idx in inspector.get_indexes('handbook_uploads')]
        if 'ix_handbook_uploads_version' in handbook_indexes:
            op.drop_index('ix_handbook_uploads_version', 'handbook_uploads')
        if 'ix_handbook_uploads_status' in handbook_indexes:
            op.drop_index('ix_handbook_uploads_status', 'handbook_uploads')
        if 'ix_handbook_uploads_file_hash' in handbook_indexes:
            op.drop_index('ix_handbook_uploads_file_hash', 'handbook_uploads')
        op.drop_table('handbook_uploads')
