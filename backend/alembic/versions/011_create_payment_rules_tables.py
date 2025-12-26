"""create_payment_rules_tables

Revision ID: 011_payment_rules
Revises: 010_lead_attribution
Create Date: 2025-01-16 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '011_payment_rules'
down_revision = '010_lead_attribution'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Asegurar que el schema ops existe (ya debería existir, pero por si acaso)
    op.execute('CREATE SCHEMA IF NOT EXISTS ops')
    
    # Crear función para actualizar updated_at (si no existe)
    op.execute("""
        CREATE OR REPLACE FUNCTION ops.update_updated_at_column()
        RETURNS TRIGGER AS $$
        BEGIN
            NEW.updated_at = NOW();
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql;
    """)
    
    # Tabla: ops.partner_payment_rules
    # Verificar si la tabla ya existe antes de crearla
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    tables = inspector.get_table_names(schema='ops')
    
    if 'partner_payment_rules' not in tables:
        op.create_table(
            'partner_payment_rules',
            sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
            sa.Column('origin_tag', sa.String(50), nullable=False),
            sa.Column('window_days', sa.Integer(), nullable=False),
            sa.Column('milestone_trips', sa.Integer(), nullable=False),
            sa.Column('amount', sa.Numeric(12, 2), nullable=False),
            sa.Column('currency', sa.String(3), nullable=False, server_default='PEN'),
            sa.Column('valid_from', sa.Date(), nullable=False),
            sa.Column('valid_to', sa.Date(), nullable=True),
            sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
            sa.Column('notes', sa.Text(), nullable=True),
            sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
            sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
            sa.PrimaryKeyConstraint('id'),
            sa.CheckConstraint("origin_tag IN ('cabinet', 'fleet_migration')", name='chk_partner_origin_tag'),
            sa.CheckConstraint('window_days > 0', name='chk_partner_window_days'),
            sa.CheckConstraint('milestone_trips > 0', name='chk_partner_milestone_trips'),
            sa.CheckConstraint("currency IN ('PEN', 'COP', 'USD')", name='chk_partner_currency'),
            sa.CheckConstraint('valid_to IS NULL OR valid_to >= valid_from', name='chk_partner_valid_dates'),
            sa.CheckConstraint('amount >= 0', name='chk_partner_amount'),
            sa.UniqueConstraint('origin_tag', 'window_days', 'milestone_trips', 'valid_from', name='uq_partner_payment_rule'),
            schema='ops'
        )
    
    # Tabla: ops.scout_payment_rules
    # Verificar si la tabla ya existe antes de crearla
    if 'scout_payment_rules' not in tables:
        op.create_table(
            'scout_payment_rules',
            sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
            sa.Column('origin_tag', sa.String(50), nullable=False),
            sa.Column('window_days', sa.Integer(), nullable=False),
            sa.Column('milestone_trips', sa.Integer(), nullable=False),
            sa.Column('amount', sa.Numeric(12, 2), nullable=False),
            sa.Column('currency', sa.String(3), nullable=False, server_default='PEN'),
            sa.Column('valid_from', sa.Date(), nullable=False),
            sa.Column('valid_to', sa.Date(), nullable=True),
            sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
            sa.Column('notes', sa.Text(), nullable=True),
            sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
            sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
            sa.PrimaryKeyConstraint('id'),
            sa.CheckConstraint("origin_tag IN ('cabinet', 'fleet_migration')", name='chk_scout_origin_tag'),
            sa.CheckConstraint('window_days > 0', name='chk_scout_window_days'),
            sa.CheckConstraint('milestone_trips > 0', name='chk_scout_milestone_trips'),
            sa.CheckConstraint("currency IN ('PEN', 'COP', 'USD')", name='chk_scout_currency'),
            sa.CheckConstraint('valid_to IS NULL OR valid_to >= valid_from', name='chk_scout_valid_dates'),
            sa.CheckConstraint('amount >= 0', name='chk_scout_amount'),
            sa.UniqueConstraint('origin_tag', 'window_days', 'milestone_trips', 'valid_from', name='uq_scout_payment_rule'),
            schema='ops'
        )
    
    # Actualizar la lista de tablas después de crear las nuevas
    tables = inspector.get_table_names(schema='ops')
    
    # Índices para partner_payment_rules
    if 'partner_payment_rules' in tables:
        indexes = [idx['name'] for idx in inspector.get_indexes('partner_payment_rules', schema='ops')]
        
        if 'idx_partner_payment_rules_origin_tag' not in indexes:
            op.create_index(
                'idx_partner_payment_rules_origin_tag',
                'partner_payment_rules',
                ['origin_tag'],
                schema='ops'
            )
        
        if 'idx_partner_payment_rules_active' not in indexes:
            op.create_index(
                'idx_partner_payment_rules_active',
                'partner_payment_rules',
                ['is_active'],
                schema='ops',
                postgresql_where=sa.text('is_active = true')
            )
        
        if 'idx_partner_payment_rules_validity' not in indexes:
            op.create_index(
                'idx_partner_payment_rules_validity',
                'partner_payment_rules',
                ['valid_from', 'valid_to'],
                schema='ops',
                postgresql_where=sa.text('is_active = true')
            )
        
        if 'idx_partner_payment_rules_lookup' not in indexes:
            op.create_index(
                'idx_partner_payment_rules_lookup',
                'partner_payment_rules',
                ['origin_tag', 'window_days', 'milestone_trips', 'is_active', 'valid_from', 'valid_to'],
                schema='ops'
            )
    
    # Índices para scout_payment_rules
    if 'scout_payment_rules' in tables:
        indexes = [idx['name'] for idx in inspector.get_indexes('scout_payment_rules', schema='ops')]
        
        if 'idx_scout_payment_rules_origin_tag' not in indexes:
            op.create_index(
                'idx_scout_payment_rules_origin_tag',
                'scout_payment_rules',
                ['origin_tag'],
                schema='ops'
            )
        
        if 'idx_scout_payment_rules_active' not in indexes:
            op.create_index(
                'idx_scout_payment_rules_active',
                'scout_payment_rules',
                ['is_active'],
                schema='ops',
                postgresql_where=sa.text('is_active = true')
            )
        
        if 'idx_scout_payment_rules_validity' not in indexes:
            op.create_index(
                'idx_scout_payment_rules_validity',
                'scout_payment_rules',
                ['valid_from', 'valid_to'],
                schema='ops',
                postgresql_where=sa.text('is_active = true')
            )
        
        if 'idx_scout_payment_rules_lookup' not in indexes:
            op.create_index(
                'idx_scout_payment_rules_lookup',
                'scout_payment_rules',
                ['origin_tag', 'window_days', 'milestone_trips', 'is_active', 'valid_from', 'valid_to'],
                schema='ops'
            )
    
    # Triggers para actualizar updated_at
    op.execute("""
        DROP TRIGGER IF EXISTS trg_partner_payment_rules_updated_at ON ops.partner_payment_rules;
        CREATE TRIGGER trg_partner_payment_rules_updated_at
            BEFORE UPDATE ON ops.partner_payment_rules
            FOR EACH ROW
            EXECUTE FUNCTION ops.update_updated_at_column();
    """)
    
    op.execute("""
        DROP TRIGGER IF EXISTS trg_scout_payment_rules_updated_at ON ops.scout_payment_rules;
        CREATE TRIGGER trg_scout_payment_rules_updated_at
            BEFORE UPDATE ON ops.scout_payment_rules
            FOR EACH ROW
            EXECUTE FUNCTION ops.update_updated_at_column();
    """)
    
    # Comentarios en tablas y columnas
    op.execute("""
        COMMENT ON TABLE ops.partner_payment_rules IS 
        'Reglas de pago para partners (ej: Yango→Yego). Define montos y condiciones de pago basadas en origin_tag, ventana de tiempo, y milestone de viajes.';
        
        COMMENT ON COLUMN ops.partner_payment_rules.origin_tag IS 
        'Origen del lead: cabinet o fleet_migration';
        
        COMMENT ON COLUMN ops.partner_payment_rules.window_days IS 
        'Ventana de días desde lead_date para evaluar la regla (ej: 7, 14, 30)';
        
        COMMENT ON COLUMN ops.partner_payment_rules.milestone_trips IS 
        'Número de viajes completados requerido para activar el pago (ej: 1, 5, 25, 50)';
        
        COMMENT ON COLUMN ops.partner_payment_rules.amount IS 
        'Monto a pagar cuando se cumple la condición';
        
        COMMENT ON COLUMN ops.partner_payment_rules.currency IS 
        'Moneda del pago: PEN, COP, o USD';
        
        COMMENT ON COLUMN ops.partner_payment_rules.valid_from IS 
        'Fecha desde la cual la regla es válida (inclusivo)';
        
        COMMENT ON COLUMN ops.partner_payment_rules.valid_to IS 
        'Fecha hasta la cual la regla es válida (inclusivo). NULL significa vigencia abierta';
        
        COMMENT ON COLUMN ops.partner_payment_rules.is_active IS 
        'Indica si la regla está activa. Reglas inactivas no se aplican aunque estén en vigencia';
        
        COMMENT ON TABLE ops.scout_payment_rules IS 
        'Reglas de pago para scouts (Yego→Scouts). Define montos y condiciones de pago basadas en origin_tag, ventana de tiempo, y milestone de viajes.';
        
        COMMENT ON COLUMN ops.scout_payment_rules.origin_tag IS 
        'Origen del lead: cabinet o fleet_migration';
        
        COMMENT ON COLUMN ops.scout_payment_rules.window_days IS 
        'Ventana de días desde lead_date para evaluar la regla (ej: 7, 14, 30)';
        
        COMMENT ON COLUMN ops.scout_payment_rules.milestone_trips IS 
        'Número de viajes completados requerido para activar el pago (ej: 1, 5, 25, 50)';
        
        COMMENT ON COLUMN ops.scout_payment_rules.amount IS 
        'Monto a pagar cuando se cumple la condición';
        
        COMMENT ON COLUMN ops.scout_payment_rules.currency IS 
        'Moneda del pago: PEN, COP, o USD';
        
        COMMENT ON COLUMN ops.scout_payment_rules.valid_from IS 
        'Fecha desde la cual la regla es válida (inclusivo)';
        
        COMMENT ON COLUMN ops.scout_payment_rules.valid_to IS 
        'Fecha hasta la cual la regla es válida (inclusivo). NULL significa vigencia abierta';
        
        COMMENT ON COLUMN ops.scout_payment_rules.is_active IS 
        'Indica si la regla está activa. Reglas inactivas no se aplican aunque estén en vigencia';
    """)


def downgrade() -> None:
    # Eliminar triggers
    op.execute('DROP TRIGGER IF EXISTS trg_scout_payment_rules_updated_at ON ops.scout_payment_rules')
    op.execute('DROP TRIGGER IF EXISTS trg_partner_payment_rules_updated_at ON ops.partner_payment_rules')
    
    # Eliminar índices de scout_payment_rules
    op.drop_index('idx_scout_payment_rules_lookup', table_name='scout_payment_rules', schema='ops')
    op.drop_index('idx_scout_payment_rules_validity', table_name='scout_payment_rules', schema='ops')
    op.drop_index('idx_scout_payment_rules_active', table_name='scout_payment_rules', schema='ops')
    op.drop_index('idx_scout_payment_rules_origin_tag', table_name='scout_payment_rules', schema='ops')
    
    # Eliminar índices de partner_payment_rules
    op.drop_index('idx_partner_payment_rules_lookup', table_name='partner_payment_rules', schema='ops')
    op.drop_index('idx_partner_payment_rules_validity', table_name='partner_payment_rules', schema='ops')
    op.drop_index('idx_partner_payment_rules_active', table_name='partner_payment_rules', schema='ops')
    op.drop_index('idx_partner_payment_rules_origin_tag', table_name='partner_payment_rules', schema='ops')
    
    # Eliminar tablas
    op.drop_table('scout_payment_rules', schema='ops')
    op.drop_table('partner_payment_rules', schema='ops')
    
    # Eliminar función (solo si no se usa en otro lado)
    # Nota: No la eliminamos porque puede ser usada por otras tablas

