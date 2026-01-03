-- Tablas de Configuración para Reglas de Pago (Paso 7)
-- Define reglas de pago para Partners (Yango→Yego) y Scouts (Yego→Scouts)
-- con soporte para vigencia temporal y múltiples condiciones

-- Asegurar que el schema ops existe
CREATE SCHEMA IF NOT EXISTS ops;

-- ============================================================================
-- TABLA: ops.partner_payment_rules
-- Define reglas de pago para partners (ej: Yango→Yego)
-- ============================================================================
CREATE TABLE IF NOT EXISTS ops.partner_payment_rules (
    id SERIAL PRIMARY KEY,
    origin_tag VARCHAR(50) NOT NULL,
    window_days INTEGER NOT NULL,
    milestone_trips INTEGER NOT NULL,
    amount NUMERIC(12, 2) NOT NULL,
    currency VARCHAR(3) NOT NULL DEFAULT 'PEN',
    valid_from DATE NOT NULL,
    valid_to DATE NULL,
    is_active BOOLEAN NOT NULL DEFAULT true,
    notes TEXT NULL,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    
    -- Constraints
    CONSTRAINT chk_partner_origin_tag CHECK (origin_tag IN ('cabinet', 'fleet_migration')),
    CONSTRAINT chk_partner_window_days CHECK (window_days > 0),
    CONSTRAINT chk_partner_milestone_trips CHECK (milestone_trips > 0),
    CONSTRAINT chk_partner_currency CHECK (currency IN ('PEN', 'COP', 'USD')),
    CONSTRAINT chk_partner_valid_dates CHECK (valid_to IS NULL OR valid_to >= valid_from),
    CONSTRAINT chk_partner_amount CHECK (amount >= 0),
    
    -- Unique parcial para evitar duplicados exactos (solo para reglas activas)
    CONSTRAINT uq_partner_payment_rule UNIQUE (origin_tag, window_days, milestone_trips, valid_from)
);

-- ============================================================================
-- TABLA: ops.scout_payment_rules
-- Define reglas de pago para scouts (Yego→Scouts)
-- ============================================================================
CREATE TABLE IF NOT EXISTS ops.scout_payment_rules (
    id SERIAL PRIMARY KEY,
    origin_tag VARCHAR(50) NOT NULL,
    window_days INTEGER NOT NULL,
    milestone_trips INTEGER NOT NULL,
    amount NUMERIC(12, 2) NOT NULL,
    currency VARCHAR(3) NOT NULL DEFAULT 'PEN',
    valid_from DATE NOT NULL,
    valid_to DATE NULL,
    is_active BOOLEAN NOT NULL DEFAULT true,
    notes TEXT NULL,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    
    -- Constraints
    CONSTRAINT chk_scout_origin_tag CHECK (origin_tag IN ('cabinet', 'fleet_migration')),
    CONSTRAINT chk_scout_window_days CHECK (window_days > 0),
    CONSTRAINT chk_scout_milestone_trips CHECK (milestone_trips > 0),
    CONSTRAINT chk_scout_currency CHECK (currency IN ('PEN', 'COP', 'USD')),
    CONSTRAINT chk_scout_valid_dates CHECK (valid_to IS NULL OR valid_to >= valid_from),
    CONSTRAINT chk_scout_amount CHECK (amount >= 0),
    
    -- Unique parcial para evitar duplicados exactos (solo para reglas activas)
    CONSTRAINT uq_scout_payment_rule UNIQUE (origin_tag, window_days, milestone_trips, valid_from)
);

-- ============================================================================
-- ÍNDICES
-- ============================================================================

-- Índices para búsquedas frecuentes por origen y vigencia
CREATE INDEX IF NOT EXISTS idx_partner_payment_rules_origin_tag 
    ON ops.partner_payment_rules(origin_tag);

CREATE INDEX IF NOT EXISTS idx_partner_payment_rules_active 
    ON ops.partner_payment_rules(is_active) 
    WHERE is_active = true;

CREATE INDEX IF NOT EXISTS idx_partner_payment_rules_validity 
    ON ops.partner_payment_rules(valid_from, valid_to) 
    WHERE is_active = true;

CREATE INDEX IF NOT EXISTS idx_partner_payment_rules_lookup 
    ON ops.partner_payment_rules(origin_tag, window_days, milestone_trips, is_active, valid_from, valid_to);

CREATE INDEX IF NOT EXISTS idx_scout_payment_rules_origin_tag 
    ON ops.scout_payment_rules(origin_tag);

CREATE INDEX IF NOT EXISTS idx_scout_payment_rules_active 
    ON ops.scout_payment_rules(is_active) 
    WHERE is_active = true;

CREATE INDEX IF NOT EXISTS idx_scout_payment_rules_validity 
    ON ops.scout_payment_rules(valid_from, valid_to) 
    WHERE is_active = true;

CREATE INDEX IF NOT EXISTS idx_scout_payment_rules_lookup 
    ON ops.scout_payment_rules(origin_tag, window_days, milestone_trips, is_active, valid_from, valid_to);

-- ============================================================================
-- FUNCIÓN: Actualizar updated_at automáticamente
-- ============================================================================
CREATE OR REPLACE FUNCTION ops.update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Triggers para actualizar updated_at
DROP TRIGGER IF EXISTS trg_partner_payment_rules_updated_at ON ops.partner_payment_rules;
CREATE TRIGGER trg_partner_payment_rules_updated_at
    BEFORE UPDATE ON ops.partner_payment_rules
    FOR EACH ROW
    EXECUTE FUNCTION ops.update_updated_at_column();

DROP TRIGGER IF EXISTS trg_scout_payment_rules_updated_at ON ops.scout_payment_rules;
CREATE TRIGGER trg_scout_payment_rules_updated_at
    BEFORE UPDATE ON ops.scout_payment_rules
    FOR EACH ROW
    EXECUTE FUNCTION ops.update_updated_at_column();

-- ============================================================================
-- COMENTARIOS EN TABLAS Y COLUMNAS
-- ============================================================================
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

-- ============================================================================
-- VALIDACIÓN
-- ============================================================================

-- Queries de validación (ejecutar manualmente después de crear las tablas):
-- 
-- 1. Listar todas las tablas en el schema ops:
--    \dt ops.*
-- 
-- 2. Contar reglas de partners:
--    SELECT COUNT(*) FROM ops.partner_payment_rules;
-- 
-- 3. Contar reglas de scouts:
--    SELECT COUNT(*) FROM ops.scout_payment_rules;





