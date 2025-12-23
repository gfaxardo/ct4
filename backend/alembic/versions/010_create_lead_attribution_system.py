"""create_lead_attribution_system

Revision ID: 010_lead_attribution
Revises: 009_alerts
Create Date: 2025-01-15 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '010_lead_attribution'
down_revision = '009_alerts'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute('CREATE SCHEMA IF NOT EXISTS observational')
    
    attribution_confidence_enum = postgresql.ENUM('high', 'medium', 'low', name='attributionconfidence', create_type=False)
    attribution_confidence_enum.create(op.get_bind(), checkfirst=True)
    
    decision_status_enum = postgresql.ENUM('assigned', 'unassigned', 'conflict', name='decisionstatus', create_type=False)
    decision_status_enum.create(op.get_bind(), checkfirst=True)
    
    op.create_table(
        'lead_events',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('source_table', sa.String(), nullable=False),
        sa.Column('source_pk', sa.String(), nullable=False),
        sa.Column('event_date', sa.Date(), nullable=False),
        sa.Column('person_key', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('scout_id', sa.Integer(), nullable=True),
        sa.Column('payload_json', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['person_key'], ['canon.identity_registry.person_key'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('source_table', 'source_pk', name='uq_lead_events_source'),
        schema='observational'
    )
    
    op.create_index(
        'idx_lead_events_person_key',
        'lead_events',
        ['person_key'],
        schema='observational'
    )
    
    op.create_index(
        'idx_lead_events_event_date',
        'lead_events',
        ['event_date'],
        schema='observational'
    )
    
    op.create_index(
        'idx_lead_events_scout_id',
        'lead_events',
        ['scout_id'],
        schema='observational'
    )
    
    op.create_index(
        'idx_lead_events_source_table_pk',
        'lead_events',
        ['source_table', 'source_pk'],
        schema='observational'
    )
    
    op.create_table(
        'lead_ledger',
        sa.Column('person_key', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('attributed_source', sa.String(), nullable=True),
        sa.Column('attributed_scout_id', sa.Integer(), nullable=True),
        sa.Column('attribution_rule', sa.String(), nullable=True),
        sa.Column('attribution_score', sa.Numeric(5, 2), nullable=False),
        sa.Column('confidence_level', attribution_confidence_enum, nullable=False),
        sa.Column('evidence_json', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('decision_status', decision_status_enum, nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['person_key'], ['canon.identity_registry.person_key'], ),
        sa.PrimaryKeyConstraint('person_key'),
        schema='observational'
    )
    
    op.create_index(
        'idx_lead_ledger_decision_status',
        'lead_ledger',
        ['decision_status'],
        schema='observational'
    )
    
    op.create_index(
        'idx_lead_ledger_scout_id',
        'lead_ledger',
        ['attributed_scout_id'],
        schema='observational'
    )


def downgrade() -> None:
    op.drop_index('idx_lead_ledger_scout_id', table_name='lead_ledger', schema='observational')
    op.drop_index('idx_lead_ledger_decision_status', table_name='lead_ledger', schema='observational')
    op.drop_table('lead_ledger', schema='observational')
    op.drop_index('idx_lead_events_source_table_pk', table_name='lead_events', schema='observational')
    op.drop_index('idx_lead_events_scout_id', table_name='lead_events', schema='observational')
    op.drop_index('idx_lead_events_event_date', table_name='lead_events', schema='observational')
    op.drop_index('idx_lead_events_person_key', table_name='lead_events', schema='observational')
    op.drop_table('lead_events', schema='observational')
    op.execute('DROP TYPE IF EXISTS decisionstatus')
    op.execute('DROP TYPE IF EXISTS attributionconfidence')
    op.execute('DROP SCHEMA IF EXISTS observational')

