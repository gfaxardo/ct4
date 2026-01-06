-- ============================================================================
-- Auditoría: Verificación del Fix de is_reconcilable_enriched
-- ============================================================================
-- Objetivo: Verificar que después del fix hay reconciliables (>0) y que los montos cuadran
-- ============================================================================

-- 1. Resumen general de PAID_MISAPPLIED por reconciliabilidad
SELECT 
    '=== RESUMEN: PAID_MISAPPLIED por Reconciliabilidad ===' AS seccion,
    yango_payment_status,
    is_reconcilable_enriched,
    COUNT(*) AS total_claims,
    SUM(expected_amount) AS total_amount,
    ROUND(100.0 * COUNT(*) / NULLIF((SELECT COUNT(*) FROM ops.mv_yango_cabinet_claims_for_collection WHERE yango_payment_status = 'PAID_MISAPPLIED'), 0), 2) AS pct_rows,
    ROUND(100.0 * SUM(expected_amount) / NULLIF((SELECT SUM(expected_amount) FROM ops.mv_yango_cabinet_claims_for_collection WHERE yango_payment_status = 'PAID_MISAPPLIED'), 0), 2) AS pct_amount
FROM ops.mv_yango_cabinet_claims_for_collection
WHERE yango_payment_status = 'PAID_MISAPPLIED'
GROUP BY yango_payment_status, is_reconcilable_enriched
ORDER BY is_reconcilable_enriched DESC;

-- 2. Verificación: misapplied_reconcilable + misapplied_not_reconcilable = misapplied_total
SELECT 
    '=== VERIFICACION: Suma de Reconciliables + No Reconciliables = Total ===' AS seccion,
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
    (SELECT SUM(expected_amount) FROM ops.mv_yango_cabinet_claims_for_collection WHERE yango_payment_status = 'PAID_MISAPPLIED' AND is_reconcilable_enriched = true) +
    (SELECT SUM(expected_amount) FROM ops.mv_yango_cabinet_claims_for_collection WHERE yango_payment_status = 'PAID_MISAPPLIED' AND is_reconcilable_enriched = false) AS suma_amount,
    CASE 
        WHEN COALESCE((SELECT SUM(expected_amount) FROM ops.mv_yango_cabinet_claims_for_collection WHERE yango_payment_status = 'PAID_MISAPPLIED' AND is_reconcilable_enriched = true), 0) +
             COALESCE((SELECT SUM(expected_amount) FROM ops.mv_yango_cabinet_claims_for_collection WHERE yango_payment_status = 'PAID_MISAPPLIED' AND is_reconcilable_enriched = false), 0) =
             COALESCE((SELECT SUM(expected_amount) FROM ops.mv_yango_cabinet_claims_for_collection WHERE yango_payment_status = 'PAID_MISAPPLIED'), 0)
        THEN 'OK: Los montos cuadran'
        ELSE 'ERROR: Los montos NO cuadran'
    END AS validacion_amount;

-- 3. Desglose detallado por identity_status, match_confidence, match_rule
SELECT 
    '=== DESGLOSE DETALLADO: PAID_MISAPPLIED ===' AS seccion,
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

-- 4. Ejemplos de claims reconciliables (LIMIT 10)
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
FROM ops.mv_yango_cabinet_claims_for_collection
WHERE yango_payment_status = 'PAID_MISAPPLIED'
    AND is_reconcilable_enriched = true
ORDER BY expected_amount DESC
LIMIT 10;

-- 5. Ejemplos de claims NO reconciliables (LIMIT 10)
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
FROM ops.mv_yango_cabinet_claims_for_collection
WHERE yango_payment_status = 'PAID_MISAPPLIED'
    AND is_reconcilable_enriched = false
ORDER BY expected_amount DESC
LIMIT 10;











