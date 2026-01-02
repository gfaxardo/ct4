-- ============================================================================
-- Verificación de Resultados: is_reconcilable_enriched
-- ============================================================================
-- Ejecutar este script en tu cliente SQL para verificar los resultados del fix
-- ============================================================================

-- 1. RESUMEN: PAID_MISAPPLIED por Reconciliabilidad
SELECT 
    '=== RESUMEN: PAID_MISAPPLIED por Reconciliabilidad ===' AS seccion,
    CASE 
        WHEN is_reconcilable_enriched = true THEN 'RECONCILIABLE'
        ELSE 'NO RECONCILIABLE'
    END AS categoria,
    COUNT(*) AS total_claims,
    SUM(expected_amount) AS total_amount,
    ROUND(100.0 * COUNT(*) / NULLIF((SELECT COUNT(*) FROM ops.mv_yango_cabinet_claims_for_collection WHERE yango_payment_status = 'PAID_MISAPPLIED'), 0), 2) AS pct_rows,
    ROUND(100.0 * SUM(expected_amount) / NULLIF((SELECT SUM(expected_amount) FROM ops.mv_yango_cabinet_claims_for_collection WHERE yango_payment_status = 'PAID_MISAPPLIED'), 0), 2) AS pct_amount
FROM ops.mv_yango_cabinet_claims_for_collection
WHERE yango_payment_status = 'PAID_MISAPPLIED'
GROUP BY is_reconcilable_enriched
ORDER BY is_reconcilable_enriched DESC;

-- 2. VERIFICACION: Suma de Reconciliables + No Reconciliables = Total
SELECT 
    '=== VERIFICACION: Suma = Total ===' AS seccion,
    (SELECT COUNT(*) FROM ops.mv_yango_cabinet_claims_for_collection WHERE yango_payment_status = 'PAID_MISAPPLIED' AND is_reconcilable_enriched = true) AS reconcilable_rows,
    (SELECT COUNT(*) FROM ops.mv_yango_cabinet_claims_for_collection WHERE yango_payment_status = 'PAID_MISAPPLIED' AND is_reconcilable_enriched = false) AS not_reconcilable_rows,
    (SELECT COUNT(*) FROM ops.mv_yango_cabinet_claims_for_collection WHERE yango_payment_status = 'PAID_MISAPPLIED') AS total_rows,
    (SELECT COUNT(*) FROM ops.mv_yango_cabinet_claims_for_collection WHERE yango_payment_status = 'PAID_MISAPPLIED' AND is_reconcilable_enriched = true) +
    (SELECT COUNT(*) FROM ops.mv_yango_cabinet_claims_for_collection WHERE yango_payment_status = 'PAID_MISAPPLIED' AND is_reconcilable_enriched = false) AS suma_rows,
    CASE 
        WHEN (SELECT COUNT(*) FROM ops.mv_yango_cabinet_claims_for_collection WHERE yango_payment_status = 'PAID_MISAPPLIED' AND is_reconcilable_enriched = true) +
             (SELECT COUNT(*) FROM ops.mv_yango_cabinet_claims_for_collection WHERE yango_payment_status = 'PAID_MISAPPLIED' AND is_reconcilable_enriched = false) =
             (SELECT COUNT(*) FROM ops.mv_yango_cabinet_claims_for_collection WHERE yango_payment_status = 'PAID_MISAPPLIED')
        THEN 'OK: Las filas cuadran'
        ELSE 'ERROR: Las filas NO cuadran'
    END AS validacion_rows,
    (SELECT SUM(expected_amount) FROM ops.mv_yango_cabinet_claims_for_collection WHERE yango_payment_status = 'PAID_MISAPPLIED' AND is_reconcilable_enriched = true) AS reconcilable_amount,
    (SELECT SUM(expected_amount) FROM ops.mv_yango_cabinet_claims_for_collection WHERE yango_payment_status = 'PAID_MISAPPLIED' AND is_reconcilable_enriched = false) AS not_reconcilable_amount,
    (SELECT SUM(expected_amount) FROM ops.mv_yango_cabinet_claims_for_collection WHERE yango_payment_status = 'PAID_MISAPPLIED') AS total_amount,
    COALESCE((SELECT SUM(expected_amount) FROM ops.mv_yango_cabinet_claims_for_collection WHERE yango_payment_status = 'PAID_MISAPPLIED' AND is_reconcilable_enriched = true), 0) +
    COALESCE((SELECT SUM(expected_amount) FROM ops.mv_yango_cabinet_claims_for_collection WHERE yango_payment_status = 'PAID_MISAPPLIED' AND is_reconcilable_enriched = false), 0) AS suma_amount,
    CASE 
        WHEN ABS(
            COALESCE((SELECT SUM(expected_amount) FROM ops.mv_yango_cabinet_claims_for_collection WHERE yango_payment_status = 'PAID_MISAPPLIED' AND is_reconcilable_enriched = true), 0) +
            COALESCE((SELECT SUM(expected_amount) FROM ops.mv_yango_cabinet_claims_for_collection WHERE yango_payment_status = 'PAID_MISAPPLIED' AND is_reconcilable_enriched = false), 0) -
            COALESCE((SELECT SUM(expected_amount) FROM ops.mv_yango_cabinet_claims_for_collection WHERE yango_payment_status = 'PAID_MISAPPLIED'), 0)
        ) < 0.01
        THEN 'OK: Los montos cuadran'
        ELSE 'ERROR: Los montos NO cuadran'
    END AS validacion_amount;

-- 3. DISTRIBUCION: identity_status + match_confidence + match_rule
SELECT 
    '=== DISTRIBUCION DETALLADA ===' AS seccion,
    identity_status,
    match_confidence,
    match_rule,
    is_reconcilable_enriched,
    COUNT(*) AS total_claims,
    SUM(expected_amount) AS total_amount
FROM ops.mv_yango_cabinet_claims_for_collection
WHERE yango_payment_status = 'PAID_MISAPPLIED'
GROUP BY identity_status, match_confidence, match_rule, is_reconcilable_enriched
ORDER BY is_reconcilable_enriched DESC, total_claims DESC;

-- 4. EJEMPLOS: Claims Reconciliables (TOP 10)
SELECT 
    '=== EJEMPLOS: RECONCILIABLES (TOP 10) ===' AS seccion,
    driver_id,
    milestone_value,
    expected_amount,
    identity_status,
    match_rule,
    match_confidence,
    is_reconcilable_enriched,
    reason_code
FROM ops.mv_yango_cabinet_claims_for_collection
WHERE yango_payment_status = 'PAID_MISAPPLIED'
    AND is_reconcilable_enriched = true
ORDER BY expected_amount DESC
LIMIT 10;

-- 5. EJEMPLOS: Claims NO Reconciliables (TOP 10)
SELECT 
    '=== EJEMPLOS: NO RECONCILIABLES (TOP 10) ===' AS seccion,
    driver_id,
    milestone_value,
    expected_amount,
    identity_status,
    match_rule,
    match_confidence,
    is_reconcilable_enriched,
    reason_code
FROM ops.mv_yango_cabinet_claims_for_collection
WHERE yango_payment_status = 'PAID_MISAPPLIED'
    AND is_reconcilable_enriched = false
ORDER BY expected_amount DESC
LIMIT 10;

