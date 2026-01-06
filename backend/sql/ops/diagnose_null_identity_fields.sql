-- ============================================================================
-- Diagnóstico: Por qué identity_status, match_rule, match_confidence son NULL
-- ============================================================================
-- Objetivo: Entender por qué estos campos son NULL en PAID_MISAPPLIED
-- ============================================================================

-- 1. Verificar valores en la vista base (v_claims_payment_status_cabinet)
SELECT 
    '=== VISTA BASE: payment_identity_status, payment_match_rule, payment_match_confidence ===' AS seccion,
    payment_identity_status,
    payment_match_rule,
    payment_match_confidence,
    reason_code,
    COUNT(*) AS total_claims,
    SUM(expected_amount) AS total_amount
FROM ops.v_claims_payment_status_cabinet c
WHERE EXISTS (
    SELECT 1 
    FROM ops.mv_yango_cabinet_claims_for_collection m
    WHERE m.driver_id = c.driver_id 
        AND m.milestone_value = c.milestone_value
        AND m.yango_payment_status = 'PAID_MISAPPLIED'
)
GROUP BY payment_identity_status, payment_match_rule, payment_match_confidence, reason_code
ORDER BY total_claims DESC;

-- 2. Verificar si hay pagos en el ledger enriched para estos claims
SELECT 
    '=== PAGOS EN LEDGER ENRICHED para claims PAID_MISAPPLIED ===' AS seccion,
    COUNT(DISTINCT p.payment_key) AS total_payments,
    COUNT(DISTINCT p.driver_id_final) AS unique_drivers,
    COUNT(*) FILTER (WHERE p.identity_status IS NOT NULL) AS with_identity_status,
    COUNT(*) FILTER (WHERE p.match_rule IS NOT NULL) AS with_match_rule,
    COUNT(*) FILTER (WHERE p.match_confidence IS NOT NULL) AS with_match_confidence
FROM ops.mv_yango_cabinet_claims_for_collection c
JOIN ops.mv_yango_payments_ledger_latest_enriched p
    ON p.driver_id_final = c.driver_id
    AND p.milestone_value != c.milestone_value
    AND p.is_paid = true
WHERE c.yango_payment_status = 'PAID_MISAPPLIED'
    AND c.reason_code = 'payment_found_other_milestone';

-- 3. Verificar valores en mv_claims_payment_status_cabinet (vista materializada base)
SELECT 
    '=== MV_CLAIMS: payment_identity_status, payment_match_rule, payment_match_confidence ===' AS seccion,
    payment_identity_status,
    payment_match_rule,
    payment_match_confidence,
    reason_code,
    COUNT(*) AS total_claims,
    SUM(expected_amount) AS total_amount
FROM ops.mv_claims_payment_status_cabinet
WHERE EXISTS (
    SELECT 1 
    FROM ops.mv_yango_cabinet_claims_for_collection m
    WHERE m.driver_id = ops.mv_claims_payment_status_cabinet.driver_id 
        AND m.milestone_value = ops.mv_claims_payment_status_cabinet.milestone_value
        AND m.yango_payment_status = 'PAID_MISAPPLIED'
)
GROUP BY payment_identity_status, payment_match_rule, payment_match_confidence, reason_code
ORDER BY total_claims DESC;

-- 4. Comparar: ¿De dónde vienen los valores NULL?
SELECT 
    '=== COMPARACION: Vista base vs Materializada ===' AS seccion,
    'v_claims_payment_status_cabinet' AS fuente,
    COUNT(*) AS total_claims,
    COUNT(*) FILTER (WHERE payment_identity_status IS NULL) AS null_identity_status,
    COUNT(*) FILTER (WHERE payment_match_rule IS NULL) AS null_match_rule,
    COUNT(*) FILTER (WHERE payment_match_confidence IS NULL) AS null_match_confidence
FROM ops.v_claims_payment_status_cabinet c
WHERE EXISTS (
    SELECT 1 
    FROM ops.mv_yango_cabinet_claims_for_collection m
    WHERE m.driver_id = c.driver_id 
        AND m.milestone_value = c.milestone_value
        AND m.yango_payment_status = 'PAID_MISAPPLIED'
)
UNION ALL
SELECT 
    'mv_claims_payment_status_cabinet' AS fuente,
    COUNT(*) AS total_claims,
    COUNT(*) FILTER (WHERE payment_identity_status IS NULL) AS null_identity_status,
    COUNT(*) FILTER (WHERE payment_match_rule IS NULL) AS null_match_rule,
    COUNT(*) FILTER (WHERE payment_match_confidence IS NULL) AS null_match_confidence
FROM ops.mv_claims_payment_status_cabinet
WHERE EXISTS (
    SELECT 1 
    FROM ops.mv_yango_cabinet_claims_for_collection m
    WHERE m.driver_id = ops.mv_claims_payment_status_cabinet.driver_id 
        AND m.milestone_value = ops.mv_claims_payment_status_cabinet.milestone_value
        AND m.yango_payment_status = 'PAID_MISAPPLIED'
);

-- 5. Verificar si el problema está en cómo se obtienen los valores del pago
-- Para PAID_MISAPPLIED, el pago está en otro milestone, así que necesitamos buscarlo
SELECT 
    '=== PAGOS EN OTRO MILESTONE para claims PAID_MISAPPLIED ===' AS seccion,
    c.driver_id,
    c.milestone_value AS claim_milestone,
    c.reason_code,
    p.milestone_value AS payment_milestone,
    p.identity_status,
    p.match_rule,
    p.match_confidence,
    p.is_paid
FROM ops.mv_claims_payment_status_cabinet c
JOIN ops.mv_yango_payments_ledger_latest_enriched p
    ON p.driver_id_final = c.driver_id
    AND p.milestone_value != c.milestone_value
    AND p.is_paid = true
WHERE EXISTS (
    SELECT 1 
    FROM ops.mv_yango_cabinet_claims_for_collection m
    WHERE m.driver_id = c.driver_id 
        AND m.milestone_value = c.milestone_value
        AND m.yango_payment_status = 'PAID_MISAPPLIED'
        AND m.reason_code = 'payment_found_other_milestone'
)
LIMIT 20;












