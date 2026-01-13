"""create_cabinet_kpi_red_recovery_queue

Revision ID: 016_cabinet_kpi_red_recovery_queue
Revises: 015_cabinet_lead_recovery_audit
Create Date: 2025-01-22 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '016_kpi_red_recovery_queue'
down_revision = '015_cabinet_lead_recovery_audit'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Crear tabla cabinet_kpi_red_recovery_queue (idempotente)
    op.create_table(
        'cabinet_kpi_red_recovery_queue',
        sa.Column('lead_source_pk', sa.String(), nullable=False, primary_key=True),
        sa.Column('status', sa.String(), nullable=False, server_default='pending'),
        sa.Column('attempt_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('last_attempt_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('matched_person_key', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('fail_reason', sa.String(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        schema='ops'
    )
    
    # Índices para mejorar queries
    op.create_index(
        'idx_cabinet_kpi_red_recovery_queue_status_attempt',
        'cabinet_kpi_red_recovery_queue',
        ['status', 'last_attempt_at'],
        schema='ops'
    )
    
    op.create_index(
        'idx_cabinet_kpi_red_recovery_queue_person_key',
        'cabinet_kpi_red_recovery_queue',
        ['matched_person_key'],
        schema='ops',
        postgresql_where=sa.text('matched_person_key IS NOT NULL')
    )
    
    # Constraint: status debe ser pending, matched, o failed
    op.execute("""
        ALTER TABLE ops.cabinet_kpi_red_recovery_queue
        ADD CONSTRAINT chk_cabinet_kpi_red_recovery_queue_status
        CHECK (status IN ('pending', 'matched', 'failed'))
    """)


def downgrade() -> None:
    op.drop_constraint('chk_cabinet_kpi_red_recovery_queue_status', 'cabinet_kpi_red_recovery_queue', schema='ops', type_='check')
    op.drop_index('idx_cabinet_kpi_red_recovery_queue_person_key', table_name='cabinet_kpi_red_recovery_queue', schema='ops')
    op.drop_index('idx_cabinet_kpi_red_recovery_queue_status_attempt', table_name='cabinet_kpi_red_recovery_queue', schema='ops')
    op.drop_table('cabinet_kpi_red_recovery_queue', schema='ops')
