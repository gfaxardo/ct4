"""create_cabinet_lead_recovery_audit

Revision ID: 015_cabinet_lead_recovery_audit
Revises: 014_driver_orphan_quarantine
Create Date: 2025-01-22 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '015_cabinet_lead_recovery_audit'
down_revision = '014_identity_gap_recovery'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Crear tabla cabinet_lead_recovery_audit (append-only o upsert auditado)
    op.create_table(
        'cabinet_lead_recovery_audit',
        sa.Column('lead_id', sa.String(), nullable=False, primary_key=True),
        sa.Column('first_recovered_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('last_recovered_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('recovered_person_key', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('recovered_by', sa.String(), nullable=False, server_default='system'),
        sa.Column('recovery_method', sa.String(), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        schema='ops'
    )
    
    # Índices para mejorar queries
    op.create_index(
        'idx_cabinet_lead_recovery_audit_first_recovered_at',
        'cabinet_lead_recovery_audit',
        ['first_recovered_at'],
        schema='ops'
    )
    
    op.create_index(
        'idx_cabinet_lead_recovery_audit_person_key',
        'cabinet_lead_recovery_audit',
        ['recovered_person_key'],
        schema='ops'
    )


def downgrade() -> None:
    op.drop_index('idx_cabinet_lead_recovery_audit_person_key', table_name='cabinet_lead_recovery_audit', schema='ops')
    op.drop_index('idx_cabinet_lead_recovery_audit_first_recovered_at', table_name='cabinet_lead_recovery_audit', schema='ops')
    op.drop_table('cabinet_lead_recovery_audit', schema='ops')
