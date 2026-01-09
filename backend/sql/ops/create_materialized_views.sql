-- ============================================================================
-- Script: Creación de Vistas Materializadas para Optimización de Rendimiento
-- ============================================================================
-- OBJETIVO:
-- Materializar las vistas más costosas del sistema de pagos Yango para
-- eliminar timeouts y mejorar significativamente el rendimiento de consultas.
-- ============================================================================
-- ORDEN DE CREACIÓN:
-- 1. Vistas base (sin dependencias)
-- 2. Vistas intermedias
-- 3. Vistas de claims
-- 4. Índices optimizados
-- ============================================================================

-- ============================================================================
-- PASO 1: Crear vistas materializadas base (sin dependencias)
-- ============================================================================

-- 1.1: mv_driver_name_index
-- Base para matching por nombre, normalización costosa
DROP MATERIALIZED VIEW IF EXISTS ops.mv_driver_name_index CASCADE;

CREATE MATERIALIZED VIEW ops.mv_driver_name_index AS
SELECT 
    driver_id,
    person_key,
    full_name_raw,
    full_name_normalized
FROM ops.v_driver_name_index;

COMMENT ON MATERIALIZED VIEW ops.mv_driver_name_index IS 
'Vista materializada de índice de nombres de drivers normalizados. Base para matching por nombre. Refrescar diariamente o cuando cambian drivers.';

-- 1.2: mv_yango_payments_ledger_latest
-- DISTINCT ON sobre tabla grande, consultado frecuentemente
DROP MATERIALIZED VIEW IF EXISTS ops.mv_yango_payments_ledger_latest CASCADE;

CREATE MATERIALIZED VIEW ops.mv_yango_payments_ledger_latest AS
SELECT 
    id,
    latest_snapshot_at,
    source_table,
    source_pk,
    pay_date,
    pay_time,
    raw_driver_name,
    driver_name_normalized,
    milestone_type,
    milestone_value,
    is_paid,
    paid_flag_source,
    driver_id,
    person_key,
    match_rule,
    match_confidence,
    payment_key,
    state_hash,
    created_at
FROM ops.v_yango_payments_ledger_latest;

COMMENT ON MATERIALIZED VIEW ops.mv_yango_payments_ledger_latest IS 
'Vista materializada del último estado de pagos Yango del ledger. Usa DISTINCT ON sobre tabla grande. Refrescar cada hora o cuando hay nuevos pagos.';

-- 1.3: mv_yango_payments_raw_current
-- Muy costosa: normalización, expansión UNION ALL, matching
DROP MATERIALIZED VIEW IF EXISTS ops.mv_yango_payments_raw_current CASCADE;

CREATE MATERIALIZED VIEW ops.mv_yango_payments_raw_current AS
SELECT 
    source_pk,
    pay_date,
    pay_time,
    scout_id,
    raw_driver_name,
    driver_name_normalized,
    milestone_type,
    milestone_value,
    is_paid,
    paid_flag_source,
    driver_id,
    person_key,
    match_rule,
    match_confidence,
    payment_key,
    state_hash
FROM ops.v_yango_payments_raw_current;

COMMENT ON MATERIALIZED VIEW ops.mv_yango_payments_raw_current IS 
'Vista materializada de pagos Yango raw normalizados. Muy costosa: normalización de nombres, expansión UNION ALL, matching. Refrescar cada hora o cuando hay nuevos pagos en public.module_ct_cabinet_payments.';

-- ============================================================================
-- PASO 2: Crear vistas materializadas intermedias
-- ============================================================================

-- 2.1: mv_yango_payments_ledger_latest_enriched
-- JOIN entre ledger_latest y raw_current, consultada múltiples veces
DROP MATERIALIZED VIEW IF EXISTS ops.mv_yango_payments_ledger_latest_enriched CASCADE;

CREATE MATERIALIZED VIEW ops.mv_yango_payments_ledger_latest_enriched AS
SELECT 
    id,
    latest_snapshot_at,
    source_table,
    source_pk,
    pay_date,
    pay_time,
    raw_driver_name,
    driver_name_normalized,
    milestone_type,
    milestone_value,
    is_paid,
    paid_flag_source,
    driver_id_original,
    person_key_original,
    driver_id_enriched,
    driver_id_final,
    person_key_final,
    identity_status,
    match_rule,
    match_confidence,
    identity_enriched,
    payment_key,
    state_hash,
    created_at
FROM ops.v_yango_payments_ledger_latest_enriched;

COMMENT ON MATERIALIZED VIEW ops.mv_yango_payments_ledger_latest_enriched IS 
'Vista materializada del ledger Yango con identidad enriquecida. JOIN entre ledger_latest y raw_current. Consultada múltiples veces por JOINs LATERAL. Refrescar cada hora o cuando hay nuevos pagos.';

-- ============================================================================
-- PASO 3: Crear vistas materializadas de claims
-- ============================================================================

-- 3.1: mv_yango_receivable_payable_detail
-- Base de claims, se consulta frecuentemente
DROP MATERIALIZED VIEW IF EXISTS ops.mv_yango_receivable_payable_detail CASCADE;

CREATE MATERIALIZED VIEW ops.mv_yango_receivable_payable_detail AS
SELECT 
    pay_week_start_monday,
    pay_iso_year_week,
    payable_date,
    achieved_date,
    lead_date,
    lead_origin,
    payer,
    milestone_type,
    milestone_value,
    window_days,
    trips_in_window,
    person_key,
    driver_id,
    amount,
    currency,
    created_at_export
FROM ops.v_yango_receivable_payable_detail;

COMMENT ON MATERIALIZED VIEW ops.mv_yango_receivable_payable_detail IS 
'Vista materializada de receivables Yango elegibles para liquidación. Base de v_claims_payment_status_cabinet. Refrescar cada hora o cuando hay nuevos claims.';

-- 3.2: mv_claims_payment_status_cabinet
-- Vista intermedia crítica con 3 LEFT JOIN LATERAL costosos
DROP MATERIALIZED VIEW IF EXISTS ops.mv_claims_payment_status_cabinet CASCADE;

CREATE MATERIALIZED VIEW ops.mv_claims_payment_status_cabinet AS
SELECT 
    driver_id,
    person_key,
    milestone_value,
    lead_date,
    due_date,
    expected_amount,
    days_overdue,
    bucket_overdue,
    paid_flag,
    paid_date,
    payment_key,
    payment_identity_status,
    payment_match_rule,
    payment_match_confidence,
    payment_status,
    payment_reason,
    reason_code,
    action_priority
FROM ops.v_claims_payment_status_cabinet;

COMMENT ON MATERIALIZED VIEW ops.mv_claims_payment_status_cabinet IS 
'Vista materializada de claims payment status cabinet. Vista intermedia crítica con 3 LEFT JOIN LATERAL costosos. Refrescar cada hora o cuando hay nuevos claims.';

-- ============================================================================
-- PASO 4: Crear índices optimizados para cada vista materializada
-- ============================================================================

-- Índices para mv_driver_name_index
CREATE INDEX IF NOT EXISTS idx_mv_driver_name_index_driver_id 
    ON ops.mv_driver_name_index(driver_id);
CREATE INDEX IF NOT EXISTS idx_mv_driver_name_index_full_name_normalized 
    ON ops.mv_driver_name_index(full_name_normalized);
CREATE INDEX IF NOT EXISTS idx_mv_driver_name_index_person_key 
    ON ops.mv_driver_name_index(person_key) WHERE person_key IS NOT NULL;

-- Índices para mv_yango_payments_ledger_latest
CREATE UNIQUE INDEX IF NOT EXISTS idx_mv_ledger_latest_payment_key 
    ON ops.mv_yango_payments_ledger_latest(payment_key);
CREATE INDEX IF NOT EXISTS idx_mv_ledger_latest_driver_milestone_paid 
    ON ops.mv_yango_payments_ledger_latest(driver_id, milestone_value, is_paid) 
    WHERE is_paid = true AND driver_id IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_mv_ledger_latest_person_milestone_paid 
    ON ops.mv_yango_payments_ledger_latest(person_key, milestone_value, is_paid) 
    WHERE is_paid = true AND person_key IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_mv_ledger_latest_pay_date 
    ON ops.mv_yango_payments_ledger_latest(pay_date DESC);

-- Índices para mv_yango_payments_raw_current
CREATE UNIQUE INDEX IF NOT EXISTS idx_mv_raw_current_payment_key 
    ON ops.mv_yango_payments_raw_current(payment_key);
CREATE INDEX IF NOT EXISTS idx_mv_raw_current_driver_milestone 
    ON ops.mv_yango_payments_raw_current(driver_id, milestone_value) 
    WHERE driver_id IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_mv_raw_current_person_milestone 
    ON ops.mv_yango_payments_raw_current(person_key, milestone_value) 
    WHERE person_key IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_mv_raw_current_pay_date 
    ON ops.mv_yango_payments_raw_current(pay_date DESC);

-- Índices para mv_yango_payments_ledger_latest_enriched
CREATE UNIQUE INDEX IF NOT EXISTS idx_mv_enriched_payment_key 
    ON ops.mv_yango_payments_ledger_latest_enriched(payment_key);
CREATE INDEX IF NOT EXISTS idx_mv_enriched_driver_milestone_paid 
    ON ops.mv_yango_payments_ledger_latest_enriched(driver_id_final, milestone_value, is_paid) 
    WHERE is_paid = true AND driver_id_final IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_mv_enriched_person_milestone_paid 
    ON ops.mv_yango_payments_ledger_latest_enriched(person_key_final, milestone_value, is_paid) 
    WHERE is_paid = true AND person_key_final IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_mv_enriched_pay_date 
    ON ops.mv_yango_payments_ledger_latest_enriched(pay_date DESC);
CREATE INDEX IF NOT EXISTS idx_mv_enriched_driver_milestone_exact 
    ON ops.mv_yango_payments_ledger_latest_enriched(driver_id_final, milestone_value, pay_date DESC, payment_key DESC) 
    WHERE is_paid = true AND driver_id_final IS NOT NULL;

-- Índices para mv_yango_receivable_payable_detail
CREATE INDEX IF NOT EXISTS idx_mv_receivable_driver_milestone 
    ON ops.mv_yango_receivable_payable_detail(driver_id, milestone_value) 
    WHERE driver_id IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_mv_receivable_lead_origin_milestone 
    ON ops.mv_yango_receivable_payable_detail(lead_origin, milestone_value);
CREATE INDEX IF NOT EXISTS idx_mv_receivable_lead_date 
    ON ops.mv_yango_receivable_payable_detail(lead_date DESC);
CREATE INDEX IF NOT EXISTS idx_mv_receivable_person_key 
    ON ops.mv_yango_receivable_payable_detail(person_key) 
    WHERE person_key IS NOT NULL;

-- Índices para mv_claims_payment_status_cabinet
CREATE UNIQUE INDEX IF NOT EXISTS idx_mv_claims_driver_milestone 
    ON ops.mv_claims_payment_status_cabinet(driver_id, milestone_value) 
    WHERE driver_id IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_mv_claims_reason_code 
    ON ops.mv_claims_payment_status_cabinet(reason_code);
CREATE INDEX IF NOT EXISTS idx_mv_claims_paid_flag 
    ON ops.mv_claims_payment_status_cabinet(paid_flag);
CREATE INDEX IF NOT EXISTS idx_mv_claims_lead_date 
    ON ops.mv_claims_payment_status_cabinet(lead_date DESC);
CREATE INDEX IF NOT EXISTS idx_mv_claims_payment_key 
    ON ops.mv_claims_payment_status_cabinet(payment_key) 
    WHERE payment_key IS NOT NULL;

-- ============================================================================
-- RESUMEN
-- ============================================================================
-- Vistas materializadas creadas:
-- 1. ops.mv_driver_name_index
-- 2. ops.mv_yango_payments_ledger_latest
-- 3. ops.mv_yango_payments_raw_current
-- 4. ops.mv_yango_payments_ledger_latest_enriched
-- 5. ops.mv_yango_receivable_payable_detail
-- 6. ops.mv_claims_payment_status_cabinet
--
-- Próximos pasos:
-- 1. Ejecutar script de actualización de vistas dependientes
-- 2. Refrescar vistas materializadas: REFRESH MATERIALIZED VIEW CONCURRENTLY
-- 3. Validar que los resultados coinciden con vistas originales
-- ============================================================================















