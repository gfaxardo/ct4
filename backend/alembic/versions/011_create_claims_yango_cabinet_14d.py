"""create_claims_yango_cabinet_14d

Revision ID: 011_claims_cabinet_14d
Revises: 010_lead_attribution
Create Date: 2026-01-XX 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '018_claims_cabinet_14d'
down_revision = '017_merge_heads'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Crear ENUM para status de claim
    claim_status_enum = postgresql.ENUM(
        'expected', 'generated', 'paid', 'rejected', 'expired',
        name='claimstatus',
        create_type=False
    )
    claim_status_enum.create(op.get_bind(), checkfirst=True)
    
    # Crear tabla canónica de claims
    op.create_table(
        'claims_yango_cabinet_14d',
        sa.Column('claim_id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('person_key', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('driver_id', sa.String(), nullable=True),
        sa.Column('lead_source_pk', sa.String(), nullable=False),
        sa.Column('lead_date', sa.Date(), nullable=False),
        sa.Column('milestone', sa.Integer(), nullable=False),
        sa.Column('amount_expected', sa.Numeric(12, 2), nullable=False),
        sa.Column('status', claim_status_enum, nullable=False, server_default='expected'),
        sa.Column('expected_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('generated_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('paid_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('reason', sa.String(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), onupdate=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['person_key'], ['canon.identity_registry.person_key']),
        sa.PrimaryKeyConstraint('claim_id'),
        schema='canon'
    )
    
    # Índices para performance
    op.create_index(
        'idx_claims_cabinet_person_lead_milestone',
        'claims_yango_cabinet_14d',
        ['person_key', 'lead_date', 'milestone'],
        unique=True,
        schema='canon'
    )
    
    op.create_index(
        'idx_claims_cabinet_driver_milestone',
        'claims_yango_cabinet_14d',
        ['driver_id', 'milestone'],
        schema='canon'
    )
    
    op.create_index(
        'idx_claims_cabinet_lead_source',
        'claims_yango_cabinet_14d',
        ['lead_source_pk', 'milestone'],
        schema='canon'
    )
    
    op.create_index(
        'idx_claims_cabinet_status',
        'claims_yango_cabinet_14d',
        ['status'],
        schema='canon'
    )
    
    op.create_index(
        'idx_claims_cabinet_lead_date',
        'claims_yango_cabinet_14d',
        ['lead_date'],
        schema='canon'
    )


def downgrade() -> None:
    op.drop_index('idx_claims_cabinet_lead_date', table_name='claims_yango_cabinet_14d', schema='canon')
    op.drop_index('idx_claims_cabinet_status', table_name='claims_yango_cabinet_14d', schema='canon')
    op.drop_index('idx_claims_cabinet_lead_source', table_name='claims_yango_cabinet_14d', schema='canon')
    op.drop_index('idx_claims_cabinet_driver_milestone', table_name='claims_yango_cabinet_14d', schema='canon')
    op.drop_index('idx_claims_cabinet_person_lead_milestone', table_name='claims_yango_cabinet_14d', schema='canon')
    op.drop_table('claims_yango_cabinet_14d', schema='canon')
    op.execute("DROP TYPE IF EXISTS claimstatus")
