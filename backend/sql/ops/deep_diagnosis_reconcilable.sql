-- ============================================================================
-- Diagnóstico Profundo: Por qué no hay reconciliables
-- ============================================================================
-- Este script hace un diagnóstico completo para entender por qué
-- is_reconcilable_enriched sigue siendo false o NULL
-- ============================================================================

-- 1. Verificar valores reales en mv_yango_cabinet_claims_for_collection
SELECT 
    '=== VALORES REALES en mv_yango_cabinet_claims_for_collection ===' AS seccion,
    yango_payment_status,
    identity_status,
    match_rule,
    match_confidence,
    is_reconcilable_enriched,
    COUNT(*) AS total_claims,
    SUM(expected_amount) AS total_amount
FROM ops.mv_yango_cabinet_claims_for_collection
WHERE yango_payment_status = 'PAID_MISAPPLIED'
GROUP BY yango_payment_status, identity_status, match_rule, match_confidence, is_reconcilable_enriched
ORDER BY total_claims DESC;

-- 2. Verificar valores en mv_claims_payment_status_cabinet (vista base materializada)
SELECT 
    '=== VALORES en mv_claims_payment_status_cabinet ===' AS seccion,
    reason_code,
    payment_identity_status,
    payment_match_rule,
    payment_match_confidence,
    COUNT(*) AS total_claims,
    SUM(expected_amount) AS total_amount
FROM ops.mv_claims_payment_status_cabinet
WHERE reason_code = 'payment_found_other_milestone'
GROUP BY reason_code, payment_identity_status, payment_match_rule, payment_match_confidence
ORDER BY total_claims DESC;

-- 3. Verificar si los pagos en el ledger tienen valores de identidad
SELECT 
    '=== PAGOS EN LEDGER: ¿Tienen valores de identidad? ===' AS seccion,
    identity_status,
    match_rule,
    match_confidence,
    COUNT(*) AS total_payments,
    COUNT(DISTINCT driver_id_final) AS unique_drivers
FROM ops.mv_yango_payments_ledger_latest_enriched
WHERE is_paid = true
    AND driver_id_final IS NOT NULL
GROUP BY identity_status, match_rule, match_confidence
ORDER BY total_payments DESC;

-- 4. Verificar pagos específicos para drivers PAID_MISAPPLIED
SELECT 
    '=== PAGOS ESPECIFICOS para drivers PAID_MISAPPLIED ===' AS seccion,
    c.driver_id,
    c.milestone_value AS claim_milestone,
    c.reason_code,
    p.milestone_value AS payment_milestone,
    p.identity_status,
    p.match_rule,
    p.match_confidence,
    p.is_paid,
    p.driver_id_final
FROM ops.mv_claims_payment_status_cabinet c
LEFT JOIN ops.mv_yango_payments_ledger_latest_enriched p
    ON p.driver_id_final = c.driver_id
    AND p.milestone_value != c.milestone_value
    AND p.is_paid = true
WHERE c.reason_code = 'payment_found_other_milestone'
ORDER BY c.expected_amount DESC
LIMIT 20;

-- 5. Verificar el cálculo de is_reconcilable_enriched paso a paso
SELECT 
    '=== CALCULO PASO A PASO de is_reconcilable_enriched ===' AS seccion,
    c.driver_id,
    c.milestone_value,
    c.payment_identity_status,
    c.payment_match_rule,
    c.payment_match_confidence,
    -- Paso 1: ¿identity_status es confirmed o enriched?
    CASE 
        WHEN c.payment_identity_status IN ('confirmed', 'enriched') THEN 'SI: confirmed/enriched'
        ELSE 'NO: ' || COALESCE(c.payment_identity_status::text, 'NULL')
    END AS paso1_identity_status,
    -- Paso 2: ¿match_confidence es high?
    CASE 
        WHEN c.payment_match_confidence = 'high' THEN 'SI: high'
        ELSE 'NO: ' || COALESCE(c.payment_match_confidence::text, 'NULL')
    END AS paso2_high,
    -- Paso 3: ¿match_confidence es medium con rule válida?
    CASE 
        WHEN c.payment_match_confidence = 'medium' 
            AND c.payment_match_rule IN ('name_unique', 'source_upstream')
        THEN 'SI: medium + rule válida'
        WHEN c.payment_match_confidence = 'medium' THEN 'NO: medium pero rule=' || COALESCE(c.payment_match_rule::text, 'NULL')
        ELSE 'NO aplica'
    END AS paso3_medium,
    -- Resultado esperado
    CASE
        WHEN c.payment_identity_status NOT IN ('confirmed', 'enriched') THEN false
        WHEN c.payment_match_confidence = 'high' THEN true
        WHEN c.payment_match_confidence = 'medium' 
            AND c.payment_match_rule IN ('name_unique', 'source_upstream') 
        THEN true
        WHEN c.payment_match_confidence::text ~ '^[0-9]+\.?[0-9]*$' 
            AND (c.payment_match_confidence::numeric >= 0.85)
        THEN true
        ELSE false
    END AS resultado_esperado,
    -- Resultado actual en mv_yango_cabinet_claims_for_collection
    m.is_reconcilable_enriched AS resultado_actual
FROM ops.mv_claims_payment_status_cabinet c
LEFT JOIN ops.mv_yango_cabinet_claims_for_collection m
    ON m.driver_id = c.driver_id
    AND m.milestone_value = c.milestone_value
WHERE c.reason_code = 'payment_found_other_milestone'
ORDER BY c.expected_amount DESC
LIMIT 20;

-- 6. Comparar: ¿Los valores se están pasando correctamente de mv_claims a mv_yango_cabinet?
SELECT 
    '=== COMPARACION: mv_claims vs mv_yango_cabinet ===' AS seccion,
    c.driver_id,
    c.milestone_value,
    c.payment_identity_status AS mv_claims_identity_status,
    m.identity_status AS mv_yango_identity_status,
    c.payment_match_rule AS mv_claims_match_rule,
    m.match_rule AS mv_yango_match_rule,
    c.payment_match_confidence AS mv_claims_match_confidence,
    m.match_confidence AS mv_yango_match_confidence,
    CASE 
        WHEN c.payment_identity_status = m.identity_status 
            AND c.payment_match_rule = m.match_rule
            AND c.payment_match_confidence = m.match_confidence
        THEN 'OK: Coinciden'
        ELSE 'ERROR: NO coinciden'
    END AS validacion
FROM ops.mv_claims_payment_status_cabinet c
JOIN ops.mv_yango_cabinet_claims_for_collection m
    ON m.driver_id = c.driver_id
    AND m.milestone_value = c.milestone_value
WHERE c.reason_code = 'payment_found_other_milestone'
LIMIT 20;













