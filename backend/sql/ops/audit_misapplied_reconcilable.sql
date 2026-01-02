-- ============================================================================
-- Query de Auditoría: Verificación de Misapplied Reconciliable
-- ============================================================================
-- PROPÓSITO:
-- Verificar que el desglose de misapplied por identity_status e 
-- is_reconcilable_enriched es correcto y que los montos cuadran.
--
-- USO:
-- Ejecutar después de implementar Opción B (diagnóstico de misapplied)
-- para validar que los segmentos están correctamente calculados.
-- ============================================================================

-- 1. Distribución por identity_status e is_reconcilable_enriched
SELECT 
    '=== DISTRIBUCIÓN POR IDENTITY_STATUS E IS_RECONCILABLE_ENRICHED ===' AS seccion,
    identity_status,
    is_reconcilable_enriched,
    COUNT(*) AS count_rows,
    SUM(expected_amount) AS sum_amount,
    ROUND(100.0 * COUNT(*) / NULLIF((SELECT COUNT(*) FROM ops.v_yango_cabinet_claims_for_collection WHERE yango_payment_status = 'PAID_MISAPPLIED'), 0), 2) AS pct_rows,
    ROUND(100.0 * SUM(expected_amount) / NULLIF((SELECT SUM(expected_amount) FROM ops.v_yango_cabinet_claims_for_collection WHERE yango_payment_status = 'PAID_MISAPPLIED'), 0), 2) AS pct_amount
FROM ops.v_yango_cabinet_claims_for_collection
WHERE yango_payment_status = 'PAID_MISAPPLIED'
GROUP BY identity_status, is_reconcilable_enriched
ORDER BY identity_status, is_reconcilable_enriched DESC;

-- 2. Verificación de que is_reconcilable_enriched se calcula correctamente
SELECT 
    '=== VERIFICACIÓN DE IS_RECONCILABLE_ENRICHED ===' AS seccion,
    COUNT(*) AS total_misapplied,
    COUNT(*) FILTER (WHERE is_reconcilable_enriched = true) AS count_reconcilable,
    COUNT(*) FILTER (WHERE is_reconcilable_enriched = false) AS count_not_reconcilable,
    SUM(expected_amount) FILTER (WHERE is_reconcilable_enriched = true) AS amount_reconcilable,
    SUM(expected_amount) FILTER (WHERE is_reconcilable_enriched = false) AS amount_not_reconcilable,
    -- Verificar regla: identity_status IN ('confirmed','enriched') AND match_confidence >= 0.85
    COUNT(*) FILTER (
        WHERE identity_status IN ('confirmed', 'enriched')
        AND (
            match_confidence = 'high' OR
            (match_confidence = 'medium' AND match_rule = 'name_unique')
        )
        AND is_reconcilable_enriched = true
    ) AS count_should_be_reconcilable,
    COUNT(*) FILTER (
        WHERE NOT (
            identity_status IN ('confirmed', 'enriched')
            AND (
                match_confidence = 'high' OR
                (match_confidence = 'medium' AND match_rule = 'name_unique')
            )
        )
        AND is_reconcilable_enriched = true
    ) AS count_incorrectly_reconcilable,
    COUNT(*) FILTER (
        WHERE identity_status IN ('confirmed', 'enriched')
        AND (
            match_confidence = 'high' OR
            (match_confidence = 'medium' AND match_rule = 'name_unique')
        )
        AND is_reconcilable_enriched = false
    ) AS count_incorrectly_not_reconcilable
FROM ops.v_yango_cabinet_claims_for_collection
WHERE yango_payment_status = 'PAID_MISAPPLIED';

-- 3. Distribución por match_rule y match_confidence
SELECT 
    '=== DISTRIBUCIÓN POR MATCH_RULE Y MATCH_CONFIDENCE ===' AS seccion,
    match_rule,
    match_confidence,
    identity_status,
    COUNT(*) AS count_rows,
    SUM(expected_amount) AS sum_amount,
    COUNT(*) FILTER (WHERE is_reconcilable_enriched = true) AS count_reconcilable,
    SUM(expected_amount) FILTER (WHERE is_reconcilable_enriched = true) AS amount_reconcilable
FROM ops.v_yango_cabinet_claims_for_collection
WHERE yango_payment_status = 'PAID_MISAPPLIED'
GROUP BY match_rule, match_confidence, identity_status
ORDER BY match_rule, match_confidence, identity_status;

-- 4. Verificación de suma total (debe cuadrar con misapplied_amount)
SELECT 
    '=== VERIFICACIÓN DE SUMA TOTAL ===' AS seccion,
    COUNT(*) AS total_misapplied_rows,
    SUM(expected_amount) AS total_misapplied_amount,
    COUNT(*) FILTER (WHERE is_reconcilable_enriched = true) AS reconcilable_rows,
    SUM(expected_amount) FILTER (WHERE is_reconcilable_enriched = true) AS reconcilable_amount,
    COUNT(*) FILTER (WHERE is_reconcilable_enriched = false) AS not_reconcilable_rows,
    SUM(expected_amount) FILTER (WHERE is_reconcilable_enriched = false) AS not_reconcilable_amount,
    -- Verificar que la suma cuadra
    CASE 
        WHEN SUM(expected_amount) = (
            SUM(expected_amount) FILTER (WHERE is_reconcilable_enriched = true) +
            SUM(expected_amount) FILTER (WHERE is_reconcilable_enriched = false)
        ) THEN 'OK: Suma cuadra'
        ELSE 'ERROR: Suma no cuadra'
    END AS verificacion_suma
FROM ops.v_yango_cabinet_claims_for_collection
WHERE yango_payment_status = 'PAID_MISAPPLIED';

-- 5. Ejemplos de claims reconciliables y no reconciliables
SELECT 
    '=== EJEMPLOS: RECONCILIABLES ===' AS seccion,
    driver_id,
    milestone_value,
    expected_amount,
    identity_status,
    match_rule,
    match_confidence,
    is_reconcilable_enriched,
    reason_code
FROM ops.v_yango_cabinet_claims_for_collection
WHERE yango_payment_status = 'PAID_MISAPPLIED'
    AND is_reconcilable_enriched = true
ORDER BY expected_amount DESC
LIMIT 10;

SELECT 
    '=== EJEMPLOS: NO RECONCILIABLES ===' AS seccion,
    driver_id,
    milestone_value,
    expected_amount,
    identity_status,
    match_rule,
    match_confidence,
    is_reconcilable_enriched,
    reason_code
FROM ops.v_yango_cabinet_claims_for_collection
WHERE yango_payment_status = 'PAID_MISAPPLIED'
    AND is_reconcilable_enriched = false
ORDER BY expected_amount DESC
LIMIT 10;

