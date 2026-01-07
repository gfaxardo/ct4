-- ============================================================================
-- Vista: Último Estado de Pagos Yango del Ledger
-- ============================================================================
-- Obtiene el último estado por payment_key desde el ledger histórico.
-- 
-- Usa DISTINCT ON para obtener solo el registro más reciente (por snapshot_at)
-- para cada payment_key.
-- ============================================================================

CREATE OR REPLACE VIEW ops.v_yango_payments_ledger_latest AS
SELECT DISTINCT ON (payment_key)
    id,
    snapshot_at AS latest_snapshot_at,
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
FROM ops.yango_payment_status_ledger
ORDER BY payment_key, snapshot_at DESC;

COMMENT ON VIEW ops.v_yango_payments_ledger_latest IS 
'Vista que obtiene el último estado por payment_key desde el ledger histórico. Usa DISTINCT ON para seleccionar solo el registro más reciente (por snapshot_at) para cada payment_key.';

COMMENT ON COLUMN ops.v_yango_payments_ledger_latest.latest_snapshot_at IS 
'Timestamp del snapshot más reciente para este payment_key. Indica cuándo se registró por última vez este estado.';



























