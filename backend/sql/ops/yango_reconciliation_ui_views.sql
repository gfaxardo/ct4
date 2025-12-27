-- ============================================================================
-- Vistas UI para Reconciliación Yango
-- ============================================================================
-- Crea las vistas UI-friendly para el frontend /pagos
-- Basadas en ops.v_yango_reconciliation_detail
-- ============================================================================

-- ============================================================================
-- 1. VISTA: Resumen Agregado UI (Summary)
-- ============================================================================
-- Agrupa por semana y milestone_value (sin reconciliation_status)
-- Proporciona métricas: expected_total, paid_total, diff_total, anomalies_total
-- ============================================================================

-- Drop la vista existente para poder cambiar columnas
DROP VIEW IF EXISTS ops.v_yango_reconciliation_summary_ui CASCADE;

CREATE VIEW ops.v_yango_reconciliation_summary_ui AS
SELECT
    pay_week_start_monday,
    milestone_value,
    -- amount_expected_sum: suma de expected_amount donde expected_amount IS NOT NULL
    COALESCE(SUM(expected_amount) FILTER (WHERE expected_amount IS NOT NULL), 0) AS amount_expected_sum,
    -- amount_paid_sum: suma de expected_amount donde reconciliation_status='paid'
    COALESCE(SUM(expected_amount) FILTER (WHERE reconciliation_status = 'paid'), 0) AS amount_paid_sum,
    -- amount_diff: diferencia entre expected y paid
    COALESCE(SUM(expected_amount) FILTER (WHERE expected_amount IS NOT NULL), 0)
        - COALESCE(SUM(expected_amount) FILTER (WHERE reconciliation_status = 'paid'), 0) AS amount_diff,
    -- anomalies_total: items con reconciliation_status='pending' (EXPECTED_NOT_PAID)
    COALESCE(COUNT(*) FILTER (WHERE reconciliation_status = 'pending'), 0) AS anomalies_total,
    -- count_expected: items con expected_amount IS NOT NULL
    COALESCE(COUNT(*) FILTER (WHERE expected_amount IS NOT NULL), 0) AS count_expected,
    -- count_paid: items con reconciliation_status='paid'
    COALESCE(COUNT(*) FILTER (WHERE reconciliation_status = 'paid'), 0) AS count_paid,
    -- count_pending: items con reconciliation_status='pending'
    COALESCE(COUNT(*) FILTER (WHERE reconciliation_status = 'pending'), 0) AS count_pending,
    -- count_drivers: drivers únicos donde driver_id IS NOT NULL
    COALESCE(COUNT(DISTINCT CASE WHEN driver_id IS NOT NULL THEN driver_id END), 0) AS count_drivers
FROM ops.v_yango_reconciliation_detail
WHERE pay_week_start_monday IS NOT NULL
GROUP BY pay_week_start_monday, milestone_value
ORDER BY pay_week_start_monday DESC, milestone_value;

COMMENT ON VIEW ops.v_yango_reconciliation_summary_ui IS 
'Vista agregada semanal UI-friendly de reconciliación Yango. Agrupa por semana (pay_week_start_monday) y milestone_value. Proporciona métricas limpias para UI: amount_expected_sum, amount_paid_sum, amount_diff, anomalies_total, count_expected, count_paid, count_pending, count_drivers.';

COMMENT ON COLUMN ops.v_yango_reconciliation_summary_ui.amount_expected_sum IS 
'Suma de montos expected (solo donde expected_amount IS NOT NULL).';

COMMENT ON COLUMN ops.v_yango_reconciliation_summary_ui.amount_paid_sum IS 
'Suma de expected_amount donde reconciliation_status=''paid'' (montos que fueron pagados).';

COMMENT ON COLUMN ops.v_yango_reconciliation_summary_ui.amount_diff IS 
'Diferencia entre expected y paid: amount_expected_sum - amount_paid_sum. Positivo indica pendiente, negativo indica sobrepago.';

COMMENT ON COLUMN ops.v_yango_reconciliation_summary_ui.anomalies_total IS 
'Conteo de items con reconciliation_status=''pending'' (EXPECTED_NOT_PAID).';

COMMENT ON COLUMN ops.v_yango_reconciliation_summary_ui.count_drivers IS 
'Conteo de drivers únicos: usa driver_id si existe, sino usa paid_raw_driver_name.';

-- ============================================================================
-- 2. VISTA: Items Detallados UI
-- ============================================================================
-- Devuelve filas detalle de ops.v_yango_reconciliation_detail
-- con campo anomaly_reason agregado para la UI
-- ============================================================================

CREATE OR REPLACE VIEW ops.v_yango_reconciliation_items_ui AS
SELECT 
    -- Campos de identificación y fechas
    pay_week_start_monday,
    pay_iso_year_week,
    payable_date,
    achieved_date,
    lead_date,
    sort_date,
    -- Campos de origen y milestone
    lead_origin,
    payer,
    milestone_type,
    milestone_value,
    window_days,
    trips_in_window,
    -- Campos de identificación
    person_key,
    driver_id,
    paid_raw_driver_name,
    paid_driver_name_normalized,
    -- Campos de montos
    expected_amount,
    currency,
    -- Campos de pago
    paid_payment_key,
    paid_snapshot_at,
    paid_source_pk,
    paid_date,
    paid_time,
    paid_is_paid,
    paid_match_rule,
    paid_match_confidence,
    match_method,
    -- Estado de reconciliación
    reconciliation_status,
    -- Campo calculado: anomaly_reason
    -- Para pending: 'EXPECTED_NOT_PAID'
    -- Para paid: NULL
    CASE 
        WHEN reconciliation_status = 'pending' THEN 'EXPECTED_NOT_PAID'
        WHEN reconciliation_status = 'paid' THEN NULL
        ELSE NULL
    END AS anomaly_reason,
    -- Campo calculado: paid_amount (igual a expected_amount si está pagado)
    CASE 
        WHEN reconciliation_status = 'paid' AND expected_amount IS NOT NULL 
        THEN expected_amount
        ELSE NULL
    END AS paid_amount,
    -- Campo adicional: created_at_export si existe
    created_at_export
FROM ops.v_yango_reconciliation_detail
WHERE pay_week_start_monday IS NOT NULL
ORDER BY 
    pay_week_start_monday DESC,
    sort_date DESC NULLS LAST,
    milestone_value;

COMMENT ON VIEW ops.v_yango_reconciliation_items_ui IS 
'Vista detalle UI-friendly de items de reconciliación Yango. Proporciona columnas limpias para tabla del frontend incluyendo anomaly_reason calculado: EXPECTED_NOT_PAID para pending, NULL para paid.';

COMMENT ON COLUMN ops.v_yango_reconciliation_items_ui.anomaly_reason IS 
'Motivo de anomalía: ''EXPECTED_NOT_PAID'' para reconciliation_status=''pending'', NULL para ''paid''.';

COMMENT ON COLUMN ops.v_yango_reconciliation_items_ui.paid_amount IS 
'Monto pagado: igual a expected_amount si reconciliation_status=''paid'', NULL en caso contrario.';

-- ============================================================================
-- VALIDACIONES
-- ============================================================================

-- Validación 1: Conteo de filas en summary_ui
SELECT 
    'v_yango_reconciliation_summary_ui' AS view_name,
    COUNT(*) AS total_rows
FROM ops.v_yango_reconciliation_summary_ui;

-- Validación 2: Conteo de filas en items_ui
SELECT 
    'v_yango_reconciliation_items_ui' AS view_name,
    COUNT(*) AS total_rows
FROM ops.v_yango_reconciliation_items_ui;

-- Validación 1: Confirmar que existan filas paid en detail
SELECT 
    reconciliation_status, 
    COUNT(*) AS count_items
FROM ops.v_yango_reconciliation_detail 
GROUP BY reconciliation_status
ORDER BY reconciliation_status;

-- Validación 2: Confirmar que summary_ui tenga paid_total > 0 al menos en alguna semana
SELECT 
    pay_week_start_monday, 
    milestone_value, 
    amount_expected_sum, 
    amount_paid_sum, 
    amount_diff, 
    anomalies_total, 
    count_paid, 
    count_pending
FROM ops.v_yango_reconciliation_summary_ui
ORDER BY pay_week_start_monday DESC, milestone_value
LIMIT 20;

-- Validación 5: Verificar que anomaly_reason se calcula correctamente
SELECT 
    reconciliation_status,
    anomaly_reason,
    COUNT(*) AS count
FROM ops.v_yango_reconciliation_items_ui
GROUP BY reconciliation_status, anomaly_reason
ORDER BY reconciliation_status, anomaly_reason;

-- Validación 6: Totales globales de summary_ui
SELECT
    SUM(amount_expected_sum) AS expected_total,
    SUM(amount_paid_sum) AS paid_total,
    SUM(anomalies_total) AS anomalies_total
FROM ops.v_yango_reconciliation_summary_ui;

