"""add_identity_to_cabinet_payments

Revision ID: 012_add_identity_cabinet_payments
Revises: 011_create_payment_rules_tables
Create Date: 2025-01-20 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '012_identity_cabinet'
down_revision = '011_payment_rules'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """
    Agrega columnas driver_id y person_key a public.module_ct_cabinet_payments.
    
    Estas columnas deben ser pobladas en el punto de inserción/ingesta upstream.
    El matching por nombre solo se usará como fallback informativo si estas columnas están NULL.
    """
    # Agregar columna driver_id (puede ser NULL si no está disponible en upstream)
    op.add_column(
        'module_ct_cabinet_payments',
        sa.Column('driver_id', sa.String(), nullable=True),
        schema='public'
    )
    
    # Agregar columna person_key (puede ser NULL si no está disponible en upstream)
    op.add_column(
        'module_ct_cabinet_payments',
        sa.Column('person_key', postgresql.UUID(as_uuid=True), nullable=True),
        schema='public'
    )
    
    # Crear índices para mejorar performance de queries
    op.create_index(
        'idx_cabinet_payments_driver_id',
        'module_ct_cabinet_payments',
        ['driver_id'],
        schema='public',
        postgresql_where=sa.text('driver_id IS NOT NULL')
    )
    
    op.create_index(
        'idx_cabinet_payments_person_key',
        'module_ct_cabinet_payments',
        ['person_key'],
        schema='public',
        postgresql_where=sa.text('person_key IS NOT NULL')
    )
    
    # Agregar comentarios
    op.execute("""
        COMMENT ON COLUMN public.module_ct_cabinet_payments.driver_id IS 
        'Driver ID del conductor. Debe ser poblado en el punto de inserción/ingesta upstream. NULL si no está disponible.';
        
        COMMENT ON COLUMN public.module_ct_cabinet_payments.person_key IS 
        'Person Key del conductor (UUID). Debe ser poblado en el punto de inserción/ingesta upstream. NULL si no está disponible.';
    """)


def downgrade() -> None:
    """
    Elimina las columnas driver_id y person_key de public.module_ct_cabinet_payments.
    """
    op.drop_index('idx_cabinet_payments_person_key', table_name='module_ct_cabinet_payments', schema='public')
    op.drop_index('idx_cabinet_payments_driver_id', table_name='module_ct_cabinet_payments', schema='public')
    op.drop_column('module_ct_cabinet_payments', 'person_key', schema='public')
    op.drop_column('module_ct_cabinet_payments', 'driver_id', schema='public')






