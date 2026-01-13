-- ============================================================================
-- Script de Validación: Reconciliación Rollup vs Claim-Level
-- ============================================================================
-- PROPÓSITO:
-- Verificar que SUM(driver_rollup) == SUM(claim_level) para garantizar
-- que no hay double-count ni pérdida por filtros.
-- ============================================================================

-- Reconciliación 1: Totales generales
SELECT 
    'Totales Generales' AS validacion,
    (SELECT SUM(expected_total_yango) FROM ops.v_claims_cabinet_driver_rollup) AS rollup_total,
    (SELECT SUM(expected_amount) FROM ops.v_yango_cabinet_claims_for_collection) AS claim_level_total,
    (SELECT SUM(expected_total_yango) FROM ops.v_claims_cabinet_driver_rollup) - 
    (SELECT SUM(expected_amount) FROM ops.v_yango_cabinet_claims_for_collection) AS difference,
    CASE 
        WHEN (SELECT SUM(expected_total_yango) FROM ops.v_claims_cabinet_driver_rollup) = 
             (SELECT SUM(expected_amount) FROM ops.v_yango_cabinet_claims_for_collection)
        THEN 'OK'
        ELSE 'ERROR'
    END AS status;

-- Reconciliación 2: Por status (PAID/UNPAID/PAID_MISAPPLIED)
SELECT 
    'Por Status' AS validacion,
    yango_payment_status,
    (SELECT SUM(expected_total_yango) FROM ops.v_claims_cabinet_driver_rollup) AS rollup_total,
    SUM(expected_amount) AS claim_level_total,
    (SELECT SUM(expected_total_yango) FROM ops.v_claims_cabinet_driver_rollup) - SUM(expected_amount) AS difference
FROM ops.v_yango_cabinet_claims_for_collection
GROUP BY yango_payment_status
ORDER BY yango_payment_status;

-- Reconciliación 3: Por milestone
SELECT 
    'Por Milestone' AS validacion,
    milestone_value,
    (SELECT SUM(expected_total_yango) FROM ops.v_claims_cabinet_driver_rollup) AS rollup_total,
    SUM(expected_amount) AS claim_level_total,
    (SELECT SUM(expected_total_yango) FROM ops.v_claims_cabinet_driver_rollup) - SUM(expected_amount) AS difference
FROM ops.v_yango_cabinet_claims_for_collection
GROUP BY milestone_value
ORDER BY milestone_value;

-- Reconciliación 4: Totales por status desde rollup (verificar que suma correcta)
SELECT 
    'Rollup Status Breakdown' AS validacion,
    SUM(paid_total_yango) AS rollup_paid_total,
    SUM(unpaid_total_yango) AS rollup_unpaid_total,
    SUM(misapplied_total_yango) AS rollup_misapplied_total,
    SUM(expected_total_yango) AS rollup_expected_total,
    SUM(paid_total_yango) + SUM(unpaid_total_yango) + SUM(misapplied_total_yango) AS rollup_sum_status,
    CASE 
        WHEN SUM(paid_total_yango) + SUM(unpaid_total_yango) + SUM(misapplied_total_yango) = SUM(expected_total_yango)
        THEN 'OK'
        ELSE 'ERROR'
    END AS status_sum_check
FROM ops.v_claims_cabinet_driver_rollup;

-- Reconciliación 5: Claim-level status breakdown (comparar con rollup)
SELECT 
    'Claim-Level Status Breakdown' AS validacion,
    SUM(CASE WHEN yango_payment_status = 'PAID' THEN expected_amount ELSE 0 END) AS claim_paid_total,
    SUM(CASE WHEN yango_payment_status = 'UNPAID' THEN expected_amount ELSE 0 END) AS claim_unpaid_total,
    SUM(CASE WHEN yango_payment_status = 'PAID_MISAPPLIED' THEN expected_amount ELSE 0 END) AS claim_misapplied_total,
    SUM(expected_amount) AS claim_expected_total
FROM ops.v_yango_cabinet_claims_for_collection;

-- Reconciliación 6: Counts
SELECT 
    'Counts' AS validacion,
    (SELECT COUNT(*) FROM ops.v_claims_cabinet_driver_rollup) AS rollup_driver_count,
    (SELECT COUNT(*) FROM ops.v_yango_cabinet_claims_for_collection) AS claim_level_count,
    (SELECT SUM(claims_total) FROM ops.v_claims_cabinet_driver_rollup) AS rollup_total_claims,
    (SELECT COUNT(*) FROM ops.v_yango_cabinet_claims_for_collection) AS claim_level_total_claims,
    CASE 
        WHEN (SELECT SUM(claims_total) FROM ops.v_claims_cabinet_driver_rollup) = 
             (SELECT COUNT(*) FROM ops.v_yango_cabinet_claims_for_collection)
        THEN 'OK'
        ELSE 'ERROR'
    END AS count_check;







