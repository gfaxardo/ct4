"""add_ingestion_run_fields

Revision ID: 004_add_ingestion_run_fields
Revises: 003_update_drivers_index_upsert
Create Date: 2024-01-04 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '004_add_ingestion_run_fields'
down_revision = '003_update_drivers_index_upsert'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("CREATE TYPE jobtype AS ENUM ('identity_run', 'drivers_index_refresh')")
    
    op.add_column('ingestion_runs', sa.Column('job_type', postgresql.ENUM('identity_run', 'drivers_index_refresh', name='jobtype'), nullable=True, server_default='identity_run'), schema='ops')
    op.add_column('ingestion_runs', sa.Column('scope_date_from', sa.Date(), nullable=True), schema='ops')
    op.add_column('ingestion_runs', sa.Column('scope_date_to', sa.Date(), nullable=True), schema='ops')
    op.add_column('ingestion_runs', sa.Column('incremental', sa.Boolean(), nullable=True, server_default='true'), schema='ops')


def downgrade() -> None:
    op.drop_column('ingestion_runs', 'incremental', schema='ops')
    op.drop_column('ingestion_runs', 'scope_date_to', schema='ops')
    op.drop_column('ingestion_runs', 'scope_date_from', schema='ops')
    op.drop_column('ingestion_runs', 'job_type', schema='ops')
    op.execute('DROP TYPE IF EXISTS jobtype')



































