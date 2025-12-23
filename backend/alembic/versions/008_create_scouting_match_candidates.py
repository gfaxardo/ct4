"""create_scouting_match_candidates

Revision ID: 008_create_scouting_match_candidates
Revises: 007_add_run_id_to_identity_tables
Create Date: 2025-12-21 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '008_scouting_obs'
down_revision = '007_add_run_id'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute('CREATE SCHEMA IF NOT EXISTS observational')
    
    matched_source_enum = postgresql.ENUM('drivers', 'cabinet', 'none', name='matched_source_enum', create_type=False)
    matched_source_enum.create(op.get_bind(), checkfirst=True)
    
    confidence_level_obs_enum = postgresql.ENUM('low', 'medium', 'high', name='confidence_level_obs_enum', create_type=False)
    confidence_level_obs_enum.create(op.get_bind(), checkfirst=True)
    
    op.create_table(
        'scouting_match_candidates',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('week_label', sa.String(), nullable=False),
        sa.Column('scouting_row_id', sa.String(), nullable=False),
        sa.Column('scouting_date', sa.Date(), nullable=False),
        sa.Column('person_key_candidate', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('matched_source', matched_source_enum, nullable=False),
        sa.Column('match_rule', sa.String(), nullable=True),
        sa.Column('score', sa.Numeric(3, 2), nullable=False),
        sa.Column('confidence_level', confidence_level_obs_enum, nullable=False),
        sa.Column('matched_source_pk', sa.String(), nullable=True),
        sa.Column('matched_source_date', sa.Date(), nullable=True),
        sa.Column('time_to_match_days', sa.Integer(), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('run_id', sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(['person_key_candidate'], ['canon.identity_registry.person_key'], ),
        sa.ForeignKeyConstraint(['run_id'], ['ops.ingestion_runs.id'], ),
        sa.PrimaryKeyConstraint('id'),
        schema='observational'
    )
    
    op.create_index(
        'idx_scouting_match_week_label',
        'scouting_match_candidates',
        ['week_label'],
        schema='observational'
    )
    
    op.create_index(
        'idx_scouting_match_scouting_row_id',
        'scouting_match_candidates',
        ['scouting_row_id'],
        schema='observational'
    )
    
    op.create_index(
        'idx_scouting_match_person_key',
        'scouting_match_candidates',
        ['person_key_candidate'],
        schema='observational',
        postgresql_where=sa.text('person_key_candidate IS NOT NULL')
    )
    
    op.create_index(
        'idx_scouting_match_scouting_date',
        'scouting_match_candidates',
        ['scouting_date'],
        schema='observational'
    )


def downgrade() -> None:
    op.drop_index('idx_scouting_match_scouting_date', table_name='scouting_match_candidates', schema='observational')
    op.drop_index('idx_scouting_match_person_key', table_name='scouting_match_candidates', schema='observational')
    op.drop_index('idx_scouting_match_scouting_row_id', table_name='scouting_match_candidates', schema='observational')
    op.drop_index('idx_scouting_match_week_label', table_name='scouting_match_candidates', schema='observational')
    op.drop_table('scouting_match_candidates', schema='observational')
    
    op.execute('DROP TYPE IF EXISTS confidence_level_obs_enum')
    op.execute('DROP TYPE IF EXISTS matched_source_enum')
    op.execute('DROP SCHEMA IF EXISTS observational')

