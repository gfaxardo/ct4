-- ============================================================================
-- Script de Verificación: Fix UI M1 Claims
-- ============================================================================
-- PROPÓSITO:
-- Verificar que después del fix en v_payments_driver_matrix_cabinet,
-- los flags achieved y claims estén alineados correctamente.
-- ============================================================================

SET statement_timeout = '120s';

-- ============================================================================
-- VERIFICACIÓN 1: Alineación achieved flags vs claims
-- ============================================================================
SELECT 
    'VERIF 1: Alineación achieved vs claims' AS check_name,
    COUNT(*) FILTER (WHERE m1_achieved_flag = true) AS m1_achieved_count,
    COUNT(*) FILTER (WHERE m1_yango_payment_status IS NOT NULL) AS m1_with_claim_count,
    COUNT(*) FILTER (WHERE m1_achieved_flag = true AND m1_yango_payment_status IS NULL) AS m1_achieved_without_claim,
    CASE 
        WHEN COUNT(*) FILTER (WHERE m1_achieved_flag = true AND m1_yango_payment_status IS NULL) = 0 THEN '✓ PASS'
        ELSE '✗ FAIL'
    END AS status
FROM ops.v_payments_driver_matrix_cabinet
WHERE origin_tag = 'cabinet';

-- ============================================================================
-- VERIFICACIÓN 2: Comparar achieved desde ambas fuentes
-- ============================================================================
WITH achieved_from_payment_calc AS (
    SELECT DISTINCT driver_id
    FROM ops.v_cabinet_milestones_achieved_from_payment_calc
    WHERE milestone_value = 1 AND achieved_flag = true
),
driver_matrix_m1 AS (
    SELECT DISTINCT driver_id
    FROM ops.v_payments_driver_matrix_cabinet
    WHERE origin_tag = 'cabinet' AND m1_achieved_flag = true
)
SELECT 
    'VERIF 2: Alineación payment_calc vs driver_matrix' AS check_name,
    COUNT(DISTINCT p.driver_id) AS in_payment_calc,
    COUNT(DISTINCT d.driver_id) AS in_driver_matrix,
    COUNT(DISTINCT p.driver_id) - COUNT(DISTINCT d.driver_id) AS difference,
    CASE 
        WHEN COUNT(DISTINCT p.driver_id) = COUNT(DISTINCT d.driver_id) THEN '✓ PASS'
        ELSE '✗ FAIL'
    END AS status
FROM achieved_from_payment_calc p
FULL OUTER JOIN driver_matrix_m1 d ON d.driver_id = p.driver_id;

-- ============================================================================
-- VERIFICACIÓN 3: Resumen por milestone
-- ============================================================================
SELECT 
    'VERIF 3: Resumen achieved vs claims por milestone' AS check_name,
    'M1' AS milestone,
    COUNT(*) FILTER (WHERE m1_achieved_flag = true) AS achieved_count,
    COUNT(*) FILTER (WHERE m1_yango_payment_status IS NOT NULL) AS claim_count,
    COUNT(*) FILTER (WHERE m1_achieved_flag = true AND m1_yango_payment_status IS NULL) AS gap_count
FROM ops.v_payments_driver_matrix_cabinet
WHERE origin_tag = 'cabinet'

UNION ALL

SELECT 
    'VERIF 3: Resumen achieved vs claims por milestone' AS check_name,
    'M5' AS milestone,
    COUNT(*) FILTER (WHERE m5_achieved_flag = true) AS achieved_count,
    COUNT(*) FILTER (WHERE m5_yango_payment_status IS NOT NULL) AS claim_count,
    COUNT(*) FILTER (WHERE m5_achieved_flag = true AND m5_yango_payment_status IS NULL) AS gap_count
FROM ops.v_payments_driver_matrix_cabinet
WHERE origin_tag = 'cabinet'

UNION ALL

SELECT 
    'VERIF 3: Resumen achieved vs claims por milestone' AS check_name,
    'M25' AS milestone,
    COUNT(*) FILTER (WHERE m25_achieved_flag = true) AS achieved_count,
    COUNT(*) FILTER (WHERE m25_yango_payment_status IS NOT NULL) AS claim_count,
    COUNT(*) FILTER (WHERE m25_achieved_flag = true AND m25_yango_payment_status IS NULL) AS gap_count
FROM ops.v_payments_driver_matrix_cabinet
WHERE origin_tag = 'cabinet';

