-- ============================================================================
-- Tabla Ledger de Estado de Pagos Yango
-- ============================================================================
-- Ledger histórico idempotente para snapshots de pagos Yango desde
-- public.module_ct_cabinet_payments.
--
-- Permite historizar cambios de estado de pagos manteniendo idempotencia
-- mediante unique constraint en (payment_key, state_hash).
-- ============================================================================

CREATE TABLE IF NOT EXISTS ops.yango_payment_status_ledger (
    id BIGSERIAL PRIMARY KEY,
    snapshot_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    source_table TEXT NOT NULL DEFAULT 'module_ct_cabinet_payments',
    source_pk TEXT NOT NULL,
    pay_date DATE,
    pay_time TIME,
    raw_driver_name TEXT NOT NULL,
    driver_name_normalized TEXT NOT NULL,
    milestone_type TEXT NOT NULL DEFAULT 'trips',
    milestone_value INTEGER NOT NULL CHECK (milestone_value IN (1, 5, 25)),
    is_paid BOOLEAN NOT NULL,
    paid_flag_source TEXT NOT NULL CHECK (paid_flag_source IN ('trip_1', 'trip_5', 'trip_25')),
    driver_id TEXT,
    person_key UUID,
    match_rule TEXT NOT NULL DEFAULT 'none' CHECK (match_rule IN ('none', 'driver_name_unique', 'driver_id_direct')),
    match_confidence TEXT NOT NULL DEFAULT 'unknown' CHECK (match_confidence IN ('high', 'medium', 'unknown')),
    payment_key TEXT NOT NULL,
    state_hash TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Constraint único para idempotencia: solo inserta si cambia el estado
CREATE UNIQUE INDEX IF NOT EXISTS idx_yango_payment_ledger_payment_state 
    ON ops.yango_payment_status_ledger (payment_key, state_hash);

-- Índices para consultas frecuentes
CREATE INDEX IF NOT EXISTS idx_yango_payment_ledger_snapshot_at 
    ON ops.yango_payment_status_ledger (snapshot_at DESC);

CREATE INDEX IF NOT EXISTS idx_yango_payment_ledger_milestone_paid 
    ON ops.yango_payment_status_ledger (milestone_value, is_paid);

CREATE INDEX IF NOT EXISTS idx_yango_payment_ledger_driver_id 
    ON ops.yango_payment_status_ledger (driver_id) 
    WHERE driver_id IS NOT NULL;

CREATE INDEX IF NOT EXISTS idx_yango_payment_ledger_person_key 
    ON ops.yango_payment_status_ledger (person_key) 
    WHERE person_key IS NOT NULL;

CREATE INDEX IF NOT EXISTS idx_yango_payment_ledger_pay_date 
    ON ops.yango_payment_status_ledger (pay_date) 
    WHERE pay_date IS NOT NULL;

CREATE INDEX IF NOT EXISTS idx_yango_payment_ledger_payment_key 
    ON ops.yango_payment_status_ledger (payment_key);

-- Comentarios
COMMENT ON TABLE ops.yango_payment_status_ledger IS 
'Ledger histórico idempotente de snapshots de pagos Yango. Registra cada cambio de estado de pago desde public.module_ct_cabinet_payments. El constraint único (payment_key, state_hash) garantiza idempotencia: solo se inserta un nuevo registro cuando cambia el estado del pago.';

COMMENT ON COLUMN ops.yango_payment_status_ledger.snapshot_at IS 
'Timestamp del snapshot/ingest. Cada corrida de ingest genera un nuevo snapshot_at para todos los registros insertados en esa corrida.';

COMMENT ON COLUMN ops.yango_payment_status_ledger.source_pk IS 
'ID del registro fuente en public.module_ct_cabinet_payments (columna id).';

COMMENT ON COLUMN ops.yango_payment_status_ledger.payment_key IS 
'Hash estable para deduplicación: md5(source_pk || milestone_value || driver_name_normalized). Identifica de forma única un pago específico.';

COMMENT ON COLUMN ops.yango_payment_status_ledger.state_hash IS 
'Hash del estado actual: md5(is_paid::text). Permite detectar cambios de estado para el mismo payment_key.';

COMMENT ON COLUMN ops.yango_payment_status_ledger.match_rule IS 
'Regla de matching usada: none (sin match), driver_name_unique (match único por nombre), driver_id_direct (match directo por driver_id).';

COMMENT ON COLUMN ops.yango_payment_status_ledger.match_confidence IS 
'Nivel de confianza del match: high (driver_id directo), medium (nombre único), unknown (sin match o múltiples matches).';








