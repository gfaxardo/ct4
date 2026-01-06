-- ============================================================================
-- Script de Verificación: Consistencia Claims vs Operativo
-- ============================================================================
-- PROPÓSITO:
-- Validar coherencia entre claims generados y viajes reales dentro de ventana.
-- Garantiza que los claims se sustentan en viajes reales desde summary_daily.
-- ============================================================================

SET statement_timeout = '120s';

-- ============================================================================
-- CHECK A: Claim M1 existente pero trips_completed_14d_from_lead = 0
-- ============================================================================
SELECT 
    'CHECK A: Claim M1 pero trips = 0' AS check_name,
    COUNT(*) AS count_inconsistencies,
    CASE 
        WHEN COUNT(*) = 0 THEN '✓ PASS'
        ELSE '✗ FAIL'
    END AS status
FROM ops.v_payments_driver_matrix_cabinet
WHERE origin_tag = 'cabinet'
    AND m1_yango_payment_status IS NOT NULL  -- Existe claim M1
    AND COALESCE(trips_completed_14d_from_lead, 0) = 0;

-- ============================================================================
-- CHECK B: Claim M5 existente pero trips_completed_14d_from_lead < 5
-- ============================================================================
SELECT 
    'CHECK B: Claim M5 pero trips < 5' AS check_name,
    COUNT(*) AS count_inconsistencies,
    CASE 
        WHEN COUNT(*) = 0 THEN '✓ PASS'
        ELSE '✗ FAIL'
    END AS status
FROM ops.v_payments_driver_matrix_cabinet
WHERE origin_tag = 'cabinet'
    AND m5_yango_payment_status IS NOT NULL  -- Existe claim M5
    AND COALESCE(trips_completed_14d_from_lead, 0) < 5;

-- ============================================================================
-- CHECK C: Claim M25 existente pero trips_completed_14d_from_lead < 25
-- ============================================================================
SELECT 
    'CHECK C: Claim M25 pero trips < 25' AS check_name,
    COUNT(*) AS count_inconsistencies,
    CASE 
        WHEN COUNT(*) = 0 THEN '✓ PASS'
        ELSE '✗ FAIL'
    END AS status
FROM ops.v_payments_driver_matrix_cabinet
WHERE origin_tag = 'cabinet'
    AND m25_yango_payment_status IS NOT NULL  -- Existe claim M25
    AND COALESCE(trips_completed_14d_from_lead, 0) < 25;

-- ============================================================================
-- RESUMEN: Distribución de claims vs trips
-- ============================================================================
SELECT 
    'RESUMEN: Claims vs trips en ventana' AS check_name,
    COUNT(*) FILTER (WHERE m1_yango_payment_status IS NOT NULL) AS m1_claims_count,
    COUNT(*) FILTER (WHERE m1_yango_payment_status IS NOT NULL AND trips_completed_14d_from_lead >= 1) AS m1_claims_with_trips_ok,
    COUNT(*) FILTER (WHERE m5_yango_payment_status IS NOT NULL) AS m5_claims_count,
    COUNT(*) FILTER (WHERE m5_yango_payment_status IS NOT NULL AND trips_completed_14d_from_lead >= 5) AS m5_claims_with_trips_ok,
    COUNT(*) FILTER (WHERE m25_yango_payment_status IS NOT NULL) AS m25_claims_count,
    COUNT(*) FILTER (WHERE m25_yango_payment_status IS NOT NULL AND trips_completed_14d_from_lead >= 25) AS m25_claims_with_trips_ok
FROM ops.v_payments_driver_matrix_cabinet
WHERE origin_tag = 'cabinet';

