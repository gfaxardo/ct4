-- ============================================================================
-- Vista: Resumen de Reconciliación Yango (Agregado Semanal)
-- ============================================================================
-- Agregado semanal desde ops.v_yango_reconciliation_detail.
-- 
-- Agrupa por: pay_week_start_monday, milestone_value, reconciliation_status
-- 
-- Campos agregados: counts, sums de montos expected vs paid, count de drivers.
-- ============================================================================

CREATE OR REPLACE VIEW ops.v_yango_reconciliation_summary AS
SELECT 
    pay_week_start_monday,
    milestone_value,
    reconciliation_status,
    COUNT(*) AS count_items,
    COUNT(DISTINCT driver_id) FILTER (WHERE driver_id IS NOT NULL) AS count_drivers_with_driver_id,
    COUNT(DISTINCT person_key) FILTER (WHERE person_key IS NOT NULL) AS count_drivers_with_person_key,
    COUNT(DISTINCT COALESCE(driver_id::text, person_key::text)) AS count_drivers_total,
    SUM(expected_amount) FILTER (WHERE expected_amount IS NOT NULL) AS sum_amount_expected,
    COUNT(*) FILTER (WHERE paid_is_paid = true) AS count_paid,
    COUNT(*) FILTER (WHERE paid_is_paid = false OR paid_is_paid IS NULL) AS count_pending,
    COUNT(*) FILTER (WHERE reconciliation_status = 'anomaly_paid_without_expected') AS count_anomalies,
    MIN(payable_date) FILTER (WHERE payable_date IS NOT NULL) AS min_payable_date,
    MAX(payable_date) FILTER (WHERE payable_date IS NOT NULL) AS max_payable_date,
    MIN(paid_date) FILTER (WHERE paid_date IS NOT NULL) AS min_paid_date,
    MAX(paid_date) FILTER (WHERE paid_date IS NOT NULL) AS max_paid_date
FROM ops.v_yango_reconciliation_detail
WHERE pay_week_start_monday IS NOT NULL
GROUP BY 
    pay_week_start_monday,
    milestone_value,
    reconciliation_status
ORDER BY 
    pay_week_start_monday DESC,
    milestone_value,
    reconciliation_status;

COMMENT ON VIEW ops.v_yango_reconciliation_summary IS 
'Vista agregada semanal de reconciliación Yango. Agrupa por semana (pay_week_start_monday), milestone_value y reconciliation_status. Proporciona counts, sums de montos expected, y estadísticas de matching.';

COMMENT ON COLUMN ops.v_yango_reconciliation_summary.reconciliation_status IS 
'Estado de reconciliación: paid, pending, anomaly_paid_without_expected.';

COMMENT ON COLUMN ops.v_yango_reconciliation_summary.sum_amount_expected IS 
'Suma de montos expected (solo para items con expected_amount). NULL para items anomaly_paid_without_expected.';

COMMENT ON COLUMN ops.v_yango_reconciliation_summary.count_paid IS 
'Número de items con paid_is_paid = true en esta agrupación.';

COMMENT ON COLUMN ops.v_yango_reconciliation_summary.count_pending IS 
'Número de items con paid_is_paid = false o NULL en esta agrupación.';

COMMENT ON COLUMN ops.v_yango_reconciliation_summary.count_anomalies IS 
'Número de items con status = anomaly_paid_without_expected en esta agrupación.';

























