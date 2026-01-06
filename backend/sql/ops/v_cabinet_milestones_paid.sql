-- ============================================================================
-- Vista: ops.v_cabinet_milestones_paid
-- ============================================================================
-- PROPÓSITO:
-- Vista canónica C4 que expone SOLO milestones PAID (pagos reconocidos por Yango)
-- sin mezclar con información de milestones alcanzados. Separación semántica clara: PAID ≠ ACHIEVED.
--
-- CAPA CANÓNICA: C4 - Pagos (PAID)
-- ============================================================================
-- REGLAS:
-- 1. Fuente: ops.v_yango_payments_ledger_latest_enriched (ledger enriquecido)
-- 2. Sin campos de achieved (no JOIN con v_payment_calculation)
-- 3. Grano: (driver_id_final, milestone_value) - 1 fila por milestone pagado
-- 4. Solo pagos confirmados: is_paid = true
-- 5. Solo milestones 1, 5, 25
-- 6. Deduplicación: DISTINCT ON (driver_id_final, milestone_value) quedarse con pay_date más reciente
-- 7. Solo pagos donde driver_id_final IS NOT NULL (requiere identidad)
-- ============================================================================
-- NOTA IMPORTANTE:
-- Por negocio puede existir paid_m5=true con paid_m1=false (Yango paga M5 y no paga M1,
-- y luego puede enmendar). Esta vista refleja exactamente lo que Yango pagó, sin asumir
-- que los milestones inferiores también fueron pagados.
-- ============================================================================
-- USO:
-- - Consultar pagos reconocidos por Yango
-- - NO usar para consultar milestones logrados (usar v_cabinet_milestones_achieved)
-- - Para reconciliación: usar v_cabinet_milestones_reconciled
-- ============================================================================

CREATE OR REPLACE VIEW ops.v_cabinet_milestones_paid AS
WITH base_paid AS (
    -- Fuente: ops.v_yango_payments_ledger_latest_enriched (ledger enriquecido)
    SELECT 
        l.driver_id_final AS driver_id,
        l.person_key_final AS person_key,
        l.milestone_value,
        l.pay_date,
        l.is_paid,
        l.payment_key,
        l.identity_status,
        l.match_rule,
        l.match_confidence,
        l.driver_id_original,
        l.driver_id_enriched,
        l.person_key_original,
        l.raw_driver_name,
        l.driver_name_normalized,
        l.latest_snapshot_at
    FROM ops.v_yango_payments_ledger_latest_enriched l
    WHERE l.is_paid = true
        AND l.milestone_value IN (1, 5, 25)
        AND l.driver_id_final IS NOT NULL  -- Requiere identidad para poder reconciliar
),
dedup_paid AS (
    -- Deduplicación: 1 fila por (driver_id + milestone_value), quedarse con pay_date más reciente
    SELECT DISTINCT ON (driver_id, milestone_value)
        driver_id,
        person_key,
        milestone_value,
        pay_date,
        is_paid,
        payment_key,
        identity_status,
        match_rule,
        match_confidence,
        driver_id_original,
        driver_id_enriched,
        person_key_original,
        raw_driver_name,
        driver_name_normalized,
        latest_snapshot_at
    FROM base_paid
    ORDER BY driver_id, milestone_value, pay_date DESC
)
SELECT 
    driver_id,
    person_key,
    milestone_value,
    pay_date,
    is_paid,
    payment_key,
    identity_status,
    match_rule,
    match_confidence,
    driver_id_original,
    driver_id_enriched,
    person_key_original,
    raw_driver_name,
    driver_name_normalized,
    latest_snapshot_at
FROM dedup_paid;

-- ============================================================================
-- Comentarios
-- ============================================================================
COMMENT ON VIEW ops.v_cabinet_milestones_paid IS 
'Vista canónica C4 que expone SOLO milestones PAID (pagos reconocidos por Yango) sin mezclar con información de milestones alcanzados. Separación semántica clara: PAID ≠ ACHIEVED. Grano: (driver_id, milestone_value) - 1 fila por milestone pagado. Fuente: ops.v_yango_payments_ledger_latest_enriched.';

COMMENT ON COLUMN ops.v_cabinet_milestones_paid.driver_id IS 
'ID del conductor (driver_id_final desde ledger enriquecido).';

COMMENT ON COLUMN ops.v_cabinet_milestones_paid.person_key IS 
'Person key del conductor (person_key_final desde ledger enriquecido).';

COMMENT ON COLUMN ops.v_cabinet_milestones_paid.milestone_value IS 
'Valor del milestone pagado (1, 5, o 25).';

COMMENT ON COLUMN ops.v_cabinet_milestones_paid.pay_date IS 
'Fecha del pago reconocido por Yango (pay_date más reciente si hay duplicados).';

COMMENT ON COLUMN ops.v_cabinet_milestones_paid.is_paid IS 
'Flag indicando si el pago está marcado como pagado (siempre true en esta vista).';

COMMENT ON COLUMN ops.v_cabinet_milestones_paid.payment_key IS 
'Clave única del pago en el ledger.';

COMMENT ON COLUMN ops.v_cabinet_milestones_paid.identity_status IS 
'Estado de identidad del pago: confirmed (upstream), enriched (matching), ambiguous, no_match.';

COMMENT ON COLUMN ops.v_cabinet_milestones_paid.match_rule IS 
'Regla de matching usada: source_upstream, name_unique, ambiguous, no_match.';

COMMENT ON COLUMN ops.v_cabinet_milestones_paid.match_confidence IS 
'Confianza del matching: high, medium, low.';

COMMENT ON COLUMN ops.v_cabinet_milestones_paid.driver_id_original IS 
'Driver ID desde el ledger original (generalmente NULL si fue ingested antes de matching).';

COMMENT ON COLUMN ops.v_cabinet_milestones_paid.driver_id_enriched IS 
'Driver ID obtenido por matching de nombre (si fue enriquecido).';

COMMENT ON COLUMN ops.v_cabinet_milestones_paid.person_key_original IS 
'Person key desde el ledger original (puede ser NULL).';

COMMENT ON COLUMN ops.v_cabinet_milestones_paid.raw_driver_name IS 
'Nombre del conductor en formato crudo desde el ledger.';

COMMENT ON COLUMN ops.v_cabinet_milestones_paid.driver_name_normalized IS 
'Nombre del conductor normalizado para matching.';

COMMENT ON COLUMN ops.v_cabinet_milestones_paid.latest_snapshot_at IS 
'Timestamp de la última snapshot del ledger para este pago.';





