-- ============================================================================
-- Diagnóstico: Valores reales en PAID_MISAPPLIED
-- ============================================================================
-- Objetivo: Ver los valores reales de identity_status, match_confidence, match_rule
-- para entender por qué is_reconcilable_enriched está calculado incorrectamente
-- ============================================================================

-- 1. Distribución de identity_status en PAID_MISAPPLIED
SELECT 
    '=== DISTRIBUCION: identity_status en PAID_MISAPPLIED ===' AS seccion,
    identity_status,
    COUNT(*) AS total_claims,
    SUM(expected_amount) AS total_amount,
    ROUND(100.0 * COUNT(*) / NULLIF((SELECT COUNT(*) FROM ops.mv_yango_cabinet_claims_for_collection WHERE yango_payment_status = 'PAID_MISAPPLIED'), 0), 2) AS pct_rows
FROM ops.mv_yango_cabinet_claims_for_collection
WHERE yango_payment_status = 'PAID_MISAPPLIED'
GROUP BY identity_status
ORDER BY total_claims DESC;

-- 2. Distribución de match_confidence en PAID_MISAPPLIED
SELECT 
    '=== DISTRIBUCION: match_confidence en PAID_MISAPPLIED ===' AS seccion,
    match_confidence,
    COUNT(*) AS total_claims,
    SUM(expected_amount) AS total_amount
FROM ops.mv_yango_cabinet_claims_for_collection
WHERE yango_payment_status = 'PAID_MISAPPLIED'
GROUP BY match_confidence
ORDER BY total_claims DESC;

-- 3. Distribución de match_rule en PAID_MISAPPLIED
SELECT 
    '=== DISTRIBUCION: match_rule en PAID_MISAPPLIED ===' AS seccion,
    match_rule,
    COUNT(*) AS total_claims,
    SUM(expected_amount) AS total_amount
FROM ops.mv_yango_cabinet_claims_for_collection
WHERE yango_payment_status = 'PAID_MISAPPLIED'
GROUP BY match_rule
ORDER BY total_claims DESC;

-- 4. Combinación identity_status + match_confidence + match_rule
SELECT 
    '=== COMBINACION: identity_status + match_confidence + match_rule ===' AS seccion,
    identity_status,
    match_confidence,
    match_rule,
    COUNT(*) AS total_claims,
    SUM(expected_amount) AS total_amount
FROM ops.mv_yango_cabinet_claims_for_collection
WHERE yango_payment_status = 'PAID_MISAPPLIED'
GROUP BY identity_status, match_confidence, match_rule
ORDER BY total_claims DESC;

-- 5. Verificar tipo de dato de match_confidence (muestra algunos valores)
SELECT 
    '=== MUESTRA: Valores reales de match_confidence ===' AS seccion,
    match_confidence,
    pg_typeof(match_confidence) AS data_type,
    COUNT(*) AS count
FROM ops.mv_yango_cabinet_claims_for_collection
WHERE yango_payment_status = 'PAID_MISAPPLIED'
GROUP BY match_confidence, pg_typeof(match_confidence)
ORDER BY count DESC
LIMIT 10;

-- 6. Valores actuales de is_reconcilable_enriched
SELECT 
    '=== ESTADO ACTUAL: is_reconcilable_enriched ===' AS seccion,
    is_reconcilable_enriched,
    COUNT(*) AS total_claims,
    SUM(expected_amount) AS total_amount
FROM ops.mv_yango_cabinet_claims_for_collection
WHERE yango_payment_status = 'PAID_MISAPPLIED'
GROUP BY is_reconcilable_enriched;

-- 7. Ejemplos de filas PAID_MISAPPLIED con diferentes combinaciones
SELECT 
    '=== EJEMPLOS: Filas PAID_MISAPPLIED ===' AS seccion,
    driver_id,
    milestone_value,
    expected_amount,
    identity_status,
    match_confidence,
    match_rule,
    is_reconcilable_enriched,
    reason_code
FROM ops.mv_yango_cabinet_claims_for_collection
WHERE yango_payment_status = 'PAID_MISAPPLIED'
ORDER BY expected_amount DESC
LIMIT 20;

-- 8. Verificar valores en la vista base (v_claims_payment_status_cabinet)
SELECT 
    '=== VISTA BASE: payment_identity_status, payment_match_confidence, payment_match_rule ===' AS seccion,
    payment_identity_status,
    payment_match_confidence,
    payment_match_rule,
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
GROUP BY payment_identity_status, payment_match_confidence, payment_match_rule
ORDER BY total_claims DESC;














