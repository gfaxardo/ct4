-- ============================================================================
-- Sistema de Ledger para Liquidaciones Scout
-- ============================================================================
-- Tabla de registro de pagos y vistas para gestionar items pagados/abiertos
-- ============================================================================

-- ============================================================================
-- 1) Tabla: ops.scout_liquidation_ledger
-- ============================================================================
CREATE TABLE IF NOT EXISTS ops.scout_liquidation_ledger (
    id BIGSERIAL PRIMARY KEY,
    payment_item_key TEXT NOT NULL UNIQUE,
    scout_id INTEGER,
    person_key UUID,
    driver_id TEXT,
    lead_origin TEXT,
    milestone_type TEXT,
    milestone_value INTEGER,
    rule_id INTEGER,
    payable_date DATE,
    achieved_date DATE,
    amount NUMERIC(12, 2),
    currency TEXT,
    paid_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    paid_by TEXT,
    payment_ref TEXT,
    notes TEXT,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);

-- Índices para búsquedas frecuentes
CREATE INDEX IF NOT EXISTS idx_scout_liquidation_ledger_scout_id 
    ON ops.scout_liquidation_ledger(scout_id);

CREATE INDEX IF NOT EXISTS idx_scout_liquidation_ledger_payable_date 
    ON ops.scout_liquidation_ledger(payable_date);

CREATE INDEX IF NOT EXISTS idx_scout_liquidation_ledger_payment_item_key 
    ON ops.scout_liquidation_ledger(payment_item_key);

CREATE INDEX IF NOT EXISTS idx_scout_liquidation_ledger_person_key 
    ON ops.scout_liquidation_ledger(person_key);

COMMENT ON TABLE ops.scout_liquidation_ledger IS 
'Ledger de liquidaciones scout. Registra qué items han sido pagados, cuándo, por quién y referencia de pago.';

COMMENT ON COLUMN ops.scout_liquidation_ledger.payment_item_key IS 
'Clave única del item de pago (MD5 hash de campos identificadores). Usado para evitar duplicados.';

COMMENT ON COLUMN ops.scout_liquidation_ledger.paid_at IS 
'Fecha y hora en que se marcó el item como pagado. Default: NOW().';

COMMENT ON COLUMN ops.scout_liquidation_ledger.paid_by IS 
'Usuario o sistema que marcó el item como pagado.';

COMMENT ON COLUMN ops.scout_liquidation_ledger.payment_ref IS 
'Referencia externa del pago (ej: número de transferencia, voucher, etc.).';

-- ============================================================================
-- 2) Vista: ops.v_scout_payable_items_base
-- ============================================================================
CREATE OR REPLACE VIEW ops.v_scout_payable_items_base AS
SELECT 
    rule_id,
    scout_id,
    person_key,
    driver_id,
    lead_origin,
    milestone_type,
    milestone_value,
    payable_date,
    achieved_date,
    amount,
    currency,
    -- Construir payment_item_key usando MD5
    MD5(CONCAT_WS('|',
        'yego_scouts',
        COALESCE(scout_id::text, ''),
        COALESCE(person_key::text, ''),
        COALESCE(lead_origin, ''),
        COALESCE(rule_id::text, ''),
        COALESCE(milestone_type, ''),
        COALESCE(milestone_value::text, ''),
        COALESCE(payable_date::text, ''),
        COALESCE(amount::text, ''),
        COALESCE(currency, '')
    )) AS payment_item_key
FROM ops.v_scout_payments_report_ui
WHERE is_payable = true
  AND amount > 0;

COMMENT ON VIEW ops.v_scout_payable_items_base IS 
'Base de items elegibles para pago scout. Incluye payment_item_key calculado para identificación única.';

-- ============================================================================
-- 3) Vista: ops.v_scout_liquidation_open_items (ENRIQUECIDA con atribución)
-- ============================================================================
CREATE OR REPLACE VIEW ops.v_scout_liquidation_open_items AS
SELECT 
    base.payment_item_key,
    base.rule_id,
    base.scout_id,
    base.person_key,
    base.driver_id,
    base.lead_origin,
    base.milestone_type,
    base.milestone_value,
    base.payable_date,
    base.achieved_date,
    base.amount,
    base.currency,
    -- Columnas de atribución
    attr.acquisition_scout_id,
    attr.acquisition_scout_name,
    attr.attribution_confidence,
    attr.attribution_rule
FROM ops.v_scout_payable_items_base base
LEFT JOIN ops.scout_liquidation_ledger ledger
    ON ledger.payment_item_key = base.payment_item_key
LEFT JOIN ops.v_attribution_canonical attr
    ON attr.person_key = base.person_key
WHERE ledger.payment_item_key IS NULL
ORDER BY base.payable_date DESC, base.scout_id, base.person_key;

COMMENT ON VIEW ops.v_scout_liquidation_open_items IS 
'Items scout elegibles para pago que aún no han sido marcados como pagados en el ledger. Enriquecida con columnas de atribución desde ops.v_attribution_canonical.';

-- ============================================================================
-- 4) Vista: ops.v_scout_liquidation_paid_items
-- ============================================================================
CREATE OR REPLACE VIEW ops.v_scout_liquidation_paid_items AS
SELECT 
    base.payment_item_key,
    base.rule_id,
    base.scout_id,
    base.person_key,
    base.driver_id,
    base.lead_origin,
    base.milestone_type,
    base.milestone_value,
    base.payable_date,
    base.achieved_date,
    base.amount,
    base.currency,
    ledger.paid_at,
    ledger.paid_by,
    ledger.payment_ref,
    ledger.notes,
    ledger.created_at AS ledger_created_at
FROM ops.v_scout_payable_items_base base
INNER JOIN ops.scout_liquidation_ledger ledger
    ON ledger.payment_item_key = base.payment_item_key
ORDER BY ledger.paid_at DESC, base.scout_id, base.person_key;

COMMENT ON VIEW ops.v_scout_liquidation_paid_items IS 
'Items scout que ya han sido marcados como pagados en el ledger. Incluye información de pago (paid_at, paid_by, payment_ref).';

-- ============================================================================
-- 5) Template: Marcar pagado por lote
-- ============================================================================
-- Template SQL comentado para marcar items como pagados por lote
-- 
-- Ejemplo de uso:
-- BEGIN;
-- 
-- INSERT INTO ops.scout_liquidation_ledger (
--     payment_item_key,
--     scout_id,
--     person_key,
--     driver_id,
--     lead_origin,
--     milestone_type,
--     milestone_value,
--     rule_id,
--     payable_date,
--     achieved_date,
--     amount,
--     currency,
--     paid_by,
--     payment_ref,
--     notes
-- )
-- SELECT 
--     payment_item_key,
--     scout_id,
--     person_key,
--     driver_id,
--     lead_origin,
--     milestone_type,
--     milestone_value,
--     rule_id,
--     payable_date,
--     achieved_date,
--     amount,
--     currency,
--     'usuario_liquidacion' AS paid_by,
--     'REF-2025-12-25-001' AS payment_ref,
--     'Liquidación semanal scout' AS notes
-- FROM ops.v_scout_liquidation_open_items
-- WHERE scout_id = 12345
--   AND payable_date <= DATE '2025-12-31'
-- ON CONFLICT (payment_item_key) DO NOTHING;
-- 
-- COMMIT;
-- 
-- Nota: Reemplazar valores literales (scout_id, fecha) antes de ejecutar.

