"""create_canon_schema

Revision ID: 001_create_canon_schema
Revises: 
Create Date: 2024-01-01 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '001_create_canon_schema'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute('CREATE SCHEMA IF NOT EXISTS canon')
    op.execute('CREATE SCHEMA IF NOT EXISTS ops')

    op.create_table(
        'identity_registry',
        sa.Column('person_key', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('confidence_level', sa.Enum('HIGH', 'MEDIUM', 'LOW', name='confidencelevel'), nullable=False),
        sa.Column('primary_phone', sa.String(), nullable=True),
        sa.Column('primary_document', sa.String(), nullable=True),
        sa.Column('primary_license', sa.String(), nullable=True),
        sa.Column('primary_full_name', sa.String(), nullable=True),
        sa.Column('flags', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        schema='canon'
    )

    op.create_table(
        'identity_links',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('person_key', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('source_table', sa.String(), nullable=False),
        sa.Column('source_pk', sa.String(), nullable=False),
        sa.Column('snapshot_date', sa.DateTime(timezone=True), nullable=False),
        sa.Column('match_rule', sa.String(), nullable=False),
        sa.Column('match_score', sa.Integer(), nullable=False),
        sa.Column('confidence_level', sa.Enum('HIGH', 'MEDIUM', 'LOW', name='confidencelevel'), nullable=False),
        sa.Column('evidence', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('linked_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['person_key'], ['canon.identity_registry.person_key'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('source_table', 'source_pk', name='uq_identity_links_source'),
        schema='canon'
    )

    op.create_table(
        'identity_unmatched',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('source_table', sa.String(), nullable=False),
        sa.Column('source_pk', sa.String(), nullable=False),
        sa.Column('snapshot_date', sa.DateTime(timezone=True), nullable=False),
        sa.Column('reason_code', sa.String(), nullable=False),
        sa.Column('details', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('candidates_preview', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('status', sa.Enum('OPEN', 'RESOLVED', 'IGNORED', name='unmatchedstatus'), server_default='OPEN', nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('resolved_at', sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('source_table', 'source_pk', name='uq_identity_unmatched_source'),
        schema='canon'
    )

    op.create_table(
        'ingestion_runs',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('started_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('status', sa.Enum('RUNNING', 'COMPLETED', 'FAILED', name='runstatus'), server_default='RUNNING', nullable=False),
        sa.Column('stats', sa.JSON(), nullable=True),
        sa.Column('error_message', sa.String(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        schema='ops'
    )


def downgrade() -> None:
    op.drop_table('ingestion_runs', schema='ops')
    op.drop_table('identity_unmatched', schema='canon')
    op.drop_table('identity_links', schema='canon')
    op.drop_table('identity_registry', schema='canon')
    op.execute('DROP SCHEMA IF EXISTS ops')
    op.execute('DROP SCHEMA IF EXISTS canon')
    op.execute('DROP TYPE IF EXISTS runstatus')
    op.execute('DROP TYPE IF EXISTS unmatchedstatus')
    op.execute('DROP TYPE IF EXISTS confidencelevel')





















