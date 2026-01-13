-- ============================================================================
-- Script de Validación: Verificar que el fix de claims funciona correctamente
-- ============================================================================
-- Este script valida que después del fix, los missing claims bajan significativamente.
-- ============================================================================

-- 1. ANTES DEL FIX: Contar missing claims (ejecutar antes de aplicar el fix)
-- Guardar estos números para comparar después
SELECT 
    '=== ANTES DEL FIX ===' AS seccion,
    COUNT(*) FILTER (WHERE should_have_claim_m1 = true AND has_claim_m1 = false) AS missing_m1_before,
    COUNT(*) FILTER (WHERE should_have_claim_m5 = true AND has_claim_m5 = false) AS missing_m5_before,
    COUNT(*) FILTER (WHERE should_have_claim_m25 = true AND has_claim_m25 = false) AS missing_m25_before
FROM ops.v_cabinet_claims_audit_14d;

-- 2. DESPUÉS DEL FIX: Contar missing claims (ejecutar después de aplicar el fix)
SELECT 
    '=== DESPUÉS DEL FIX ===' AS seccion,
    COUNT(*) FILTER (WHERE should_have_claim_m1 = true AND has_claim_m1 = false) AS missing_m1_after,
    COUNT(*) FILTER (WHERE should_have_claim_m5 = true AND has_claim_m5 = false) AS missing_m5_after,
    COUNT(*) FILTER (WHERE should_have_claim_m25 = true AND has_claim_m25 = false) AS missing_m25_after
FROM ops.v_cabinet_claims_audit_14d;

-- 3. CASO ESPECÍFICO: Driver con trips>=5 en 14d debe tener expected_m1 y expected_m5
SELECT 
    '=== CASO ESPECÍFICO: trips>=5 en 14d ===' AS seccion,
    a.driver_id,
    a.trips_in_14d,
    a.should_have_claim_m1,
    a.has_claim_m1,
    a.should_have_claim_m5,
    a.has_claim_m5,
    c.expected_amount AS m1_expected_amount,
    c2.expected_amount AS m5_expected_amount,
    c.paid_flag AS m1_paid_flag,
    c2.paid_flag AS m5_paid_flag
FROM ops.v_cabinet_claims_audit_14d a
LEFT JOIN ops.v_claims_payment_status_cabinet c
    ON c.driver_id = a.driver_id
    AND c.milestone_value = 1
LEFT JOIN ops.v_claims_payment_status_cabinet c2
    ON c2.driver_id = a.driver_id
    AND c2.milestone_value = 5
WHERE a.trips_in_14d >= 5
    AND (a.should_have_claim_m1 = true OR a.should_have_claim_m5 = true)
LIMIT 10;

-- 4. VERIFICACIÓN: No debe haber dependencia de pago para generar claims
SELECT 
    '=== VERIFICACIÓN: Claims sin pago ===' AS seccion,
    COUNT(*) AS total_claims,
    COUNT(*) FILTER (WHERE paid_flag = false) AS claims_sin_pago,
    COUNT(*) FILTER (WHERE paid_flag = true) AS claims_con_pago
FROM ops.v_claims_payment_status_cabinet;

-- 5. VERIFICACIÓN: No debe haber dependencia de M1 para M5/M25
SELECT 
    '=== VERIFICACIÓN: M5/M25 sin M1 ===' AS seccion,
    COUNT(*) FILTER (WHERE milestone_value = 5) AS total_m5,
    COUNT(*) FILTER (WHERE milestone_value = 5 AND driver_id NOT IN (
        SELECT driver_id FROM ops.v_claims_payment_status_cabinet WHERE milestone_value = 1
    )) AS m5_sin_m1,
    COUNT(*) FILTER (WHERE milestone_value = 25) AS total_m25,
    COUNT(*) FILTER (WHERE milestone_value = 25 AND driver_id NOT IN (
        SELECT driver_id FROM ops.v_claims_payment_status_cabinet WHERE milestone_value = 1
    )) AS m25_sin_m1
FROM ops.v_claims_payment_status_cabinet;
