-- ============================================================================
-- Validación y Resumen: Auditoría de Claims No Reconciliables
-- ============================================================================
-- Ejecutar estos queries después de crear la vista para validar y obtener resúmenes
-- ============================================================================

-- ============================================================================
-- A) VALIDACIÓN: Conteos deben calzar exactamente
-- ============================================================================
SELECT 
    'Validación: Conteo de claims' AS validacion,
    (SELECT COUNT(*) FROM ops.v_yango_cabinet_audit_non_reconcilable) AS vista_audit_count,
    (SELECT COUNT(*) FROM ops.mv_yango_cabinet_claims_for_collection WHERE is_reconcilable_enriched = false) AS mv_count,
    CASE 
        WHEN (SELECT COUNT(*) FROM ops.v_yango_cabinet_audit_non_reconcilable) = 
             (SELECT COUNT(*) FROM ops.mv_yango_cabinet_claims_for_collection WHERE is_reconcilable_enriched = false)
        THEN 'OK: Conteos calzan'
        ELSE 'ERROR: Conteos NO calzan - diferencia: ' || 
             ABS((SELECT COUNT(*) FROM ops.v_yango_cabinet_audit_non_reconcilable) - 
                 (SELECT COUNT(*) FROM ops.mv_yango_cabinet_claims_for_collection WHERE is_reconcilable_enriched = false))
    END AS resultado;

-- ============================================================================
-- B) VALIDACIÓN: audit_reason_code no debe ser NULL
-- ============================================================================
SELECT 
    'Validación: audit_reason_code no NULL' AS validacion,
    COUNT(*) AS total_rows,
    COUNT(audit_reason_code) AS rows_with_reason_code,
    COUNT(*) FILTER (WHERE audit_reason_code IS NULL) AS rows_null_reason_code,
    CASE 
        WHEN COUNT(*) FILTER (WHERE audit_reason_code IS NULL) = 0
        THEN 'OK: Todos tienen audit_reason_code'
        ELSE 'ERROR: ' || COUNT(*) FILTER (WHERE audit_reason_code IS NULL) || ' sin audit_reason_code'
    END AS resultado
FROM ops.v_yango_cabinet_audit_non_reconcilable;

-- ============================================================================
-- C) RESUMEN: Por audit_reason_code ordenado por monto DESC
-- ============================================================================
SELECT 
    audit_reason_code,
    COUNT(*) AS claims_count,
    SUM(expected_amount) AS total_amount,
    ROUND(AVG(expected_amount), 2) AS avg_amount,
    MIN(expected_amount) AS min_amount,
    MAX(expected_amount) AS max_amount
FROM ops.v_yango_cabinet_audit_non_reconcilable
GROUP BY audit_reason_code
ORDER BY total_amount DESC NULLS LAST;

-- ============================================================================
-- D) DISTRIBUCIÓN DETALLADA: audit_reason_code vs identity_status
-- ============================================================================
SELECT 
    audit_reason_code,
    identity_status,
    COUNT(*) AS claims_count,
    SUM(expected_amount) AS total_amount,
    ROUND(100.0 * COUNT(*) / SUM(COUNT(*)) OVER (PARTITION BY audit_reason_code), 2) AS pct_within_reason
FROM ops.v_yango_cabinet_audit_non_reconcilable
GROUP BY audit_reason_code, identity_status
ORDER BY audit_reason_code, claims_count DESC;

-- ============================================================================
-- E) DISTRIBUCIÓN: audit_reason_code vs match_confidence
-- ============================================================================
SELECT 
    audit_reason_code,
    match_confidence,
    COUNT(*) AS claims_count,
    SUM(expected_amount) AS total_amount
FROM ops.v_yango_cabinet_audit_non_reconcilable
GROUP BY audit_reason_code, match_confidence
ORDER BY audit_reason_code, claims_count DESC;

-- ============================================================================
-- F) TOP 20 EJEMPLOS POR REASON_CODE (para inspección rápida)
-- ============================================================================
WITH ranked_examples AS (
    SELECT 
        audit_reason_code,
        audit_row_key,
        driver_id,
        driver_name,
        milestone_value,
        expected_amount,
        identity_status,
        match_rule,
        match_confidence,
        yango_payment_status,
        days_overdue_yango,
        ROW_NUMBER() OVER (PARTITION BY audit_reason_code ORDER BY expected_amount DESC) AS rn
    FROM ops.v_yango_cabinet_audit_non_reconcilable
)
SELECT 
    audit_reason_code,
    audit_row_key,
    driver_id,
    driver_name,
    milestone_value,
    expected_amount,
    identity_status,
    match_rule,
    match_confidence,
    yango_payment_status,
    days_overdue_yango
FROM ranked_examples
WHERE rn <= 20
ORDER BY audit_reason_code, expected_amount DESC;






