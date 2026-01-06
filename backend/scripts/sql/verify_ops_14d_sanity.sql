-- ============================================================================
-- Script de Verificación: Ops 14d Sanity Check
-- ============================================================================
-- PROPÓSITO:
-- Validar coherencia entre achieved flags y viajes reales dentro de ventana de 14 días.
-- Garantiza que los achieved flags se sustentan en viajes reales desde summary_daily.
-- ============================================================================

SET statement_timeout = '120s';

-- ============================================================================
-- CHECK A: Drivers con m1_achieved_flag = true pero trips_completed_14d_from_lead < 1
-- ============================================================================
SELECT 
    'CHECK A: M1 achieved pero trips < 1' AS check_name,
    COUNT(*) AS count_inconsistencies,
    CASE 
        WHEN COUNT(*) = 0 THEN '✓ PASS'
        ELSE '✗ FAIL'
    END AS status
FROM ops.v_payments_driver_matrix_cabinet
WHERE origin_tag = 'cabinet'
    AND m1_achieved_flag = true
    AND COALESCE(trips_completed_14d_from_lead, 0) < 1;

-- ============================================================================
-- CHECK B: Drivers con m5_achieved_flag = true pero trips_completed_14d_from_lead < 5
-- ============================================================================
SELECT 
    'CHECK B: M5 achieved pero trips < 5' AS check_name,
    COUNT(*) AS count_inconsistencies,
    CASE 
        WHEN COUNT(*) = 0 THEN '✓ PASS'
        ELSE '✗ FAIL'
    END AS status
FROM ops.v_payments_driver_matrix_cabinet
WHERE origin_tag = 'cabinet'
    AND m5_achieved_flag = true
    AND COALESCE(trips_completed_14d_from_lead, 0) < 5;

-- ============================================================================
-- CHECK C: Drivers con m25_achieved_flag = true pero trips_completed_14d_from_lead < 25
-- ============================================================================
SELECT 
    'CHECK C: M25 achieved pero trips < 25' AS check_name,
    COUNT(*) AS count_inconsistencies,
    CASE 
        WHEN COUNT(*) = 0 THEN '✓ PASS'
        ELSE '✗ FAIL'
    END AS status
FROM ops.v_payments_driver_matrix_cabinet
WHERE origin_tag = 'cabinet'
    AND m25_achieved_flag = true
    AND COALESCE(trips_completed_14d_from_lead, 0) < 25;

-- ============================================================================
-- CHECK D: Drivers con connection_within_14d_flag = true pero connection_date fuera de ventana
-- ============================================================================
SELECT 
    'CHECK D: Connection flag true pero fecha fuera de ventana' AS check_name,
    COUNT(*) AS count_inconsistencies,
    CASE 
        WHEN COUNT(*) = 0 THEN '✓ PASS'
        ELSE '✗ FAIL'
    END AS status
FROM ops.v_payments_driver_matrix_cabinet
WHERE origin_tag = 'cabinet'
    AND connection_within_14d_flag = true
    AND (
        connection_date_within_14d IS NULL
        OR connection_date_within_14d < lead_date
        OR connection_date_within_14d >= lead_date + INTERVAL '14 days'
    );

-- ============================================================================
-- RESUMEN: Distribución de achieved vs trips
-- ============================================================================
SELECT 
    'RESUMEN: Achieved vs trips en ventana' AS check_name,
    COUNT(*) FILTER (WHERE m1_achieved_flag = true) AS m1_achieved_count,
    COUNT(*) FILTER (WHERE m1_achieved_flag = true AND trips_completed_14d_from_lead >= 1) AS m1_achieved_with_trips_ok,
    COUNT(*) FILTER (WHERE m5_achieved_flag = true) AS m5_achieved_count,
    COUNT(*) FILTER (WHERE m5_achieved_flag = true AND trips_completed_14d_from_lead >= 5) AS m5_achieved_with_trips_ok,
    COUNT(*) FILTER (WHERE m25_achieved_flag = true) AS m25_achieved_count,
    COUNT(*) FILTER (WHERE m25_achieved_flag = true AND trips_completed_14d_from_lead >= 25) AS m25_achieved_with_trips_ok
FROM ops.v_payments_driver_matrix_cabinet
WHERE origin_tag = 'cabinet';

