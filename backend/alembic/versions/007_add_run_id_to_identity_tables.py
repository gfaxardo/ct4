"""add_run_id_to_identity_tables

Revision ID: 007_add_run_id_to_identity_tables
Revises: 006_fix_jobtype_enum
Create Date: 2025-12-21 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '007_add_run_id'
down_revision = '006_fix_jobtype_enum'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        'identity_links',
        sa.Column('run_id', sa.Integer(), nullable=True),
        schema='canon'
    )
    
    op.add_column(
        'identity_unmatched',
        sa.Column('run_id', sa.Integer(), nullable=True),
        schema='canon'
    )
    
    op.create_foreign_key(
        'fk_identity_links_run_id',
        'identity_links',
        'ingestion_runs',
        ['run_id'],
        ['id'],
        source_schema='canon',
        referent_schema='ops'
    )
    
    op.create_foreign_key(
        'fk_identity_unmatched_run_id',
        'identity_unmatched',
        'ingestion_runs',
        ['run_id'],
        ['id'],
        source_schema='canon',
        referent_schema='ops'
    )
    
    op.create_index(
        'idx_identity_links_run_id',
        'identity_links',
        ['run_id'],
        schema='canon'
    )
    
    op.create_index(
        'idx_identity_unmatched_run_id',
        'identity_unmatched',
        ['run_id'],
        schema='canon'
    )


def downgrade() -> None:
    op.drop_index('idx_identity_unmatched_run_id', table_name='identity_unmatched', schema='canon')
    op.drop_index('idx_identity_links_run_id', table_name='identity_links', schema='canon')
    op.drop_constraint('fk_identity_unmatched_run_id', 'identity_unmatched', schema='canon', type_='foreignkey')
    op.drop_constraint('fk_identity_links_run_id', 'identity_links', schema='canon', type_='foreignkey')
    op.drop_column('identity_unmatched', 'run_id', schema='canon')
    op.drop_column('identity_links', 'run_id', schema='canon')

