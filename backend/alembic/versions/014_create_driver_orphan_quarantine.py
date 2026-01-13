"""create_driver_orphan_quarantine

Revision ID: 014_driver_orphan_quarantine
Revises: 013_identity_origin
Create Date: 2025-01-22 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '014_driver_orphan_quarantine'
down_revision = '013_identity_origin'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Crear ENUMs para quarantine
    op.execute("""
        DO $$ BEGIN
            IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'orphan_detected_reason') THEN
                CREATE TYPE orphan_detected_reason AS ENUM (
                    'no_lead_no_events',
                    'no_lead_has_events_repair_failed',
                    'legacy_driver_without_origin',
                    'manual_detection'
                );
            END IF;
        END $$;
    """)
    
    op.execute("""
        DO $$ BEGIN
            IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'orphan_status') THEN
                CREATE TYPE orphan_status AS ENUM (
                    'quarantined',
                    'resolved_relinked',
                    'resolved_created_lead',
                    'purged'
                );
            END IF;
        END $$;
    """)
    
    # Crear tabla driver_orphan_quarantine
    op.create_table(
        'driver_orphan_quarantine',
        sa.Column('driver_id', sa.String(), nullable=False, primary_key=True),
        sa.Column('person_key', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('detected_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('detected_reason', postgresql.ENUM('no_lead_no_events', 'no_lead_has_events_repair_failed', 'legacy_driver_without_origin', 'manual_detection', name='orphan_detected_reason', create_type=False), nullable=False),
        sa.Column('creation_rule', sa.String(), nullable=True),
        sa.Column('evidence_json', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('status', postgresql.ENUM('quarantined', 'resolved_relinked', 'resolved_created_lead', 'purged', name='orphan_status', create_type=False), server_default='quarantined', nullable=False),
        sa.Column('resolved_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('resolution_notes', sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(['person_key'], ['canon.identity_registry.person_key'], ondelete='SET NULL'),
        schema='canon'
    )
    
    # Índices para mejorar queries
    op.create_index(
        'idx_driver_orphan_quarantine_status',
        'driver_orphan_quarantine',
        ['status'],
        schema='canon'
    )
    
    op.create_index(
        'idx_driver_orphan_quarantine_detected_reason',
        'driver_orphan_quarantine',
        ['detected_reason'],
        schema='canon'
    )
    
    op.create_index(
        'idx_driver_orphan_quarantine_person_key',
        'driver_orphan_quarantine',
        ['person_key'],
        schema='canon'
    )
    
    op.create_index(
        'idx_driver_orphan_quarantine_detected_at',
        'driver_orphan_quarantine',
        ['detected_at'],
        schema='canon'
    )


def downgrade() -> None:
    op.drop_index('idx_driver_orphan_quarantine_detected_at', table_name='driver_orphan_quarantine', schema='canon')
    op.drop_index('idx_driver_orphan_quarantine_person_key', table_name='driver_orphan_quarantine', schema='canon')
    op.drop_index('idx_driver_orphan_quarantine_detected_reason', table_name='driver_orphan_quarantine', schema='canon')
    op.drop_index('idx_driver_orphan_quarantine_status', table_name='driver_orphan_quarantine', schema='canon')
    op.drop_table('driver_orphan_quarantine', schema='canon')
    op.execute('DROP TYPE IF EXISTS orphan_status')
    op.execute('DROP TYPE IF EXISTS orphan_detected_reason')

