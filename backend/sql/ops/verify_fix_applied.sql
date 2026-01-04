-- ============================================================================
-- Verificación: ¿Se aplicó el fix correctamente?
-- ============================================================================
-- Este script verifica si el fix se aplicó y si hay datos después del fix
-- ============================================================================

-- 1. Verificar si v_claims_payment_status_cabinet tiene los campos de identidad
SELECT 
    '=== VISTA BASE: Campos de identidad en PAID_MISAPPLIED ===' AS seccion,
    reason_code,
    COUNT(*) AS total_claims,
    COUNT(*) FILTER (WHERE payment_identity_status IS NOT NULL) AS with_identity_status,
    COUNT(*) FILTER (WHERE payment_match_rule IS NOT NULL) AS with_match_rule,
    COUNT(*) FILTER (WHERE payment_match_confidence IS NOT NULL) AS with_match_confidence,
    COUNT(*) FILTER (WHERE payment_identity_status IS NOT NULL 
                     AND payment_match_rule IS NOT NULL 
                     AND payment_match_confidence IS NOT NULL) AS with_all_fields
FROM ops.v_claims_payment_status_cabinet c
WHERE EXISTS (
    SELECT 1 
    FROM ops.mv_yango_cabinet_claims_for_collection m
    WHERE m.driver_id = c.driver_id 
        AND m.milestone_value = c.milestone_value
        AND m.yango_payment_status = 'PAID_MISAPPLIED'
)
GROUP BY reason_code
ORDER BY total_claims DESC;

-- 2. Verificar si mv_claims_payment_status_cabinet tiene los campos (después de refresh)
SELECT 
    '=== MV_CLAIMS: Campos de identidad en PAID_MISAPPLIED ===' AS seccion,
    reason_code,
    COUNT(*) AS total_claims,
    COUNT(*) FILTER (WHERE payment_identity_status IS NOT NULL) AS with_identity_status,
    COUNT(*) FILTER (WHERE payment_match_rule IS NOT NULL) AS with_match_rule,
    COUNT(*) FILTER (WHERE payment_match_confidence IS NOT NULL) AS with_match_confidence,
    COUNT(*) FILTER (WHERE payment_identity_status IS NOT NULL 
                     AND payment_match_rule IS NOT NULL 
                     AND payment_match_confidence IS NOT NULL) AS with_all_fields
FROM ops.mv_claims_payment_status_cabinet c
WHERE EXISTS (
    SELECT 1 
    FROM ops.mv_yango_cabinet_claims_for_collection m
    WHERE m.driver_id = c.driver_id 
        AND m.milestone_value = c.milestone_value
        AND m.yango_payment_status = 'PAID_MISAPPLIED'
)
GROUP BY reason_code
ORDER BY total_claims DESC;

-- 3. Verificar valores en mv_yango_cabinet_claims_for_collection
SELECT 
    '=== MV_YANGO_CABINET: Campos de identidad ===' AS seccion,
    yango_payment_status,
    is_reconcilable_enriched,
    COUNT(*) AS total_claims,
    COUNT(*) FILTER (WHERE identity_status IS NOT NULL) AS with_identity_status,
    COUNT(*) FILTER (WHERE match_rule IS NOT NULL) AS with_match_rule,
    COUNT(*) FILTER (WHERE match_confidence IS NOT NULL) AS with_match_confidence,
    SUM(expected_amount) AS total_amount
FROM ops.mv_yango_cabinet_claims_for_collection
WHERE yango_payment_status = 'PAID_MISAPPLIED'
GROUP BY yango_payment_status, is_reconcilable_enriched
ORDER BY is_reconcilable_enriched DESC;

-- 4. Verificar si hay pagos en el ledger para estos drivers
SELECT 
    '=== PAGOS EN LEDGER para drivers PAID_MISAPPLIED ===' AS seccion,
    COUNT(DISTINCT c.driver_id) AS unique_drivers_in_claims,
    COUNT(DISTINCT p.driver_id_final) AS unique_drivers_in_ledger,
    COUNT(DISTINCT p.payment_key) AS total_payments,
    COUNT(*) FILTER (WHERE p.identity_status IS NOT NULL) AS payments_with_identity,
    COUNT(*) FILTER (WHERE p.match_rule IS NOT NULL) AS payments_with_match_rule,
    COUNT(*) FILTER (WHERE p.match_confidence IS NOT NULL) AS payments_with_match_confidence
FROM ops.mv_yango_cabinet_claims_for_collection c
LEFT JOIN ops.mv_yango_payments_ledger_latest_enriched p
    ON p.driver_id_final = c.driver_id
    AND p.is_paid = true
WHERE c.yango_payment_status = 'PAID_MISAPPLIED'
    AND c.reason_code = 'payment_found_other_milestone';

-- 5. Ejemplos de pagos en otro milestone para estos drivers
SELECT 
    '=== EJEMPLOS: Pagos en otro milestone para drivers PAID_MISAPPLIED ===' AS seccion,
    c.driver_id,
    c.milestone_value AS claim_milestone,
    p.milestone_value AS payment_milestone,
    p.identity_status,
    p.match_rule,
    p.match_confidence,
    p.is_paid
FROM ops.mv_yango_cabinet_claims_for_collection c
JOIN ops.mv_yango_payments_ledger_latest_enriched p
    ON p.driver_id_final = c.driver_id
    AND p.milestone_value != c.milestone_value
    AND p.is_paid = true
WHERE c.yango_payment_status = 'PAID_MISAPPLIED'
    AND c.reason_code = 'payment_found_other_milestone'
ORDER BY c.expected_amount DESC
LIMIT 10;

-- 6. Verificar la definición actual de v_claims_payment_status_cabinet
-- (Para ver si el fix se aplicó)
SELECT 
    '=== DEFINICION: v_claims_payment_status_cabinet ===' AS seccion,
    pg_get_viewdef('ops.v_claims_payment_status_cabinet', true) LIKE '%p_other_milestone.identity_status%' AS has_fix_applied;







