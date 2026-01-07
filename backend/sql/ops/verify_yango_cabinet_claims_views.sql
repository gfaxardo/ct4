-- ============================================================================
-- Validación: Vistas de Reclamo Formal a Yango
-- ============================================================================
-- Queries para validar las vistas de EXIGIMOS, REPORTAMOS y RESUMEN
-- ============================================================================

-- ============================================================================
-- 1. Validación: Conteos y duplicados en EXIGIMOS
-- ============================================================================
SELECT 
    'Validacion EXIGIMOS: Conteos' AS validacion,
    COUNT(*) AS total_rows,
    COUNT(DISTINCT claim_key) AS distinct_claim_keys,
    COUNT(DISTINCT (driver_id, milestone_value, lead_date)) AS distinct_composite_keys,
    CASE 
        WHEN COUNT(*) = COUNT(DISTINCT claim_key) THEN 'OK: Sin duplicados por claim_key'
        ELSE 'ERROR: ' || (COUNT(*) - COUNT(DISTINCT claim_key)) || ' duplicados por claim_key'
    END AS resultado_claim_key,
    CASE 
        WHEN COUNT(*) = COUNT(DISTINCT (driver_id, milestone_value, lead_date)) THEN 'OK: Sin duplicados por composite key'
        ELSE 'ERROR: ' || (COUNT(*) - COUNT(DISTINCT (driver_id, milestone_value, lead_date))) || ' duplicados por composite key'
    END AS resultado_composite
FROM ops.v_yango_cabinet_claims_exigimos;

-- ============================================================================
-- 2. Validación: Conteos y duplicados en REPORTAMOS
-- ============================================================================
SELECT 
    'Validacion REPORTAMOS: Conteos' AS validacion,
    COUNT(*) AS total_rows,
    COUNT(DISTINCT payment_key) AS distinct_payment_keys,
    COUNT(*) FILTER (WHERE payment_key IS NULL) AS rows_null_payment_key,
    CASE 
        WHEN COUNT(*) = COUNT(DISTINCT payment_key) THEN 'OK: Sin duplicados por payment_key'
        ELSE 'ERROR: ' || (COUNT(*) - COUNT(DISTINCT payment_key)) || ' duplicados por payment_key'
    END AS resultado
FROM ops.v_yango_cabinet_payments_reportamos;

-- ============================================================================
-- 3. Validación: EXIGIMOS solo tiene UNPAID
-- ============================================================================
SELECT 
    'Validacion EXIGIMOS: Solo UNPAID' AS validacion,
    yango_payment_status,
    COUNT(*) AS count_rows,
    SUM(expected_amount) AS total_amount
FROM ops.v_yango_cabinet_claims_exigimos
GROUP BY yango_payment_status;

-- ============================================================================
-- 4. Validación: EXIGIMOS tiene driver_id NOT NULL
-- ============================================================================
SELECT 
    'Validacion EXIGIMOS: driver_id NOT NULL' AS validacion,
    COUNT(*) AS total_rows,
    COUNT(driver_id) AS rows_with_driver_id,
    COUNT(*) FILTER (WHERE driver_id IS NULL) AS rows_null_driver_id,
    CASE 
        WHEN COUNT(*) FILTER (WHERE driver_id IS NULL) = 0 THEN 'OK: Todos tienen driver_id'
        ELSE 'ERROR: ' || COUNT(*) FILTER (WHERE driver_id IS NULL) || ' sin driver_id'
    END AS resultado
FROM ops.v_yango_cabinet_claims_exigimos;

-- ============================================================================
-- 5. Validación: REPORTAMOS solo tiene is_paid = true
-- ============================================================================
SELECT 
    'Validacion REPORTAMOS: Distribucion por no_mapping_reason' AS validacion,
    no_mapping_reason,
    COUNT(*) AS count_rows,
    SUM(paid_amount) AS total_amount
FROM ops.v_yango_cabinet_payments_reportamos
GROUP BY no_mapping_reason
ORDER BY count_rows DESC;

-- ============================================================================
-- 6. Validación: RESUMEN - Totales deben calzar
-- ============================================================================
SELECT 
    'Validacion RESUMEN: Totales' AS validacion,
    section,
    category,
    count_claims,
    amount
FROM ops.v_yango_cabinet_claims_exec_summary
WHERE category = 'TOTAL'
ORDER BY section;

-- ============================================================================
-- 7. Comparación: EXIGIMOS vs MV original
-- ============================================================================
SELECT 
    'Comparacion EXIGIMOS vs MV' AS validacion,
    (SELECT COUNT(*) FROM ops.v_yango_cabinet_claims_exigimos) AS vista_exigimos_count,
    (SELECT COUNT(*) FROM ops.mv_yango_cabinet_claims_for_collection 
     WHERE yango_payment_status = 'UNPAID' AND driver_id IS NOT NULL) AS mv_unpaid_count,
    CASE 
        WHEN (SELECT COUNT(*) FROM ops.v_yango_cabinet_claims_exigimos) = 
             (SELECT COUNT(*) FROM ops.mv_yango_cabinet_claims_for_collection 
              WHERE yango_payment_status = 'UNPAID' AND driver_id IS NOT NULL)
        THEN 'OK: Conteos calzan'
        ELSE 'ERROR: Diferencia de ' || 
             ABS((SELECT COUNT(*) FROM ops.v_yango_cabinet_claims_exigimos) - 
                 (SELECT COUNT(*) FROM ops.mv_yango_cabinet_claims_for_collection 
                  WHERE yango_payment_status = 'UNPAID' AND driver_id IS NOT NULL))
    END AS resultado;

-- ============================================================================
-- 8. Distribución: EXIGIMOS por milestone
-- ============================================================================
SELECT 
    'Distribucion EXIGIMOS por milestone' AS validacion,
    milestone_value,
    COUNT(*) AS count_claims,
    SUM(expected_amount) AS total_amount,
    ROUND(AVG(expected_amount), 2) AS avg_amount
FROM ops.v_yango_cabinet_claims_exigimos
GROUP BY milestone_value
ORDER BY milestone_value;

-- ============================================================================
-- 9. Distribución: REPORTAMOS por milestone
-- ============================================================================
SELECT 
    'Distribucion REPORTAMOS por milestone' AS validacion,
    milestone_value,
    COUNT(*) AS count_payments,
    SUM(paid_amount) AS total_amount,
    ROUND(AVG(paid_amount), 2) AS avg_amount
FROM ops.v_yango_cabinet_payments_reportamos
GROUP BY milestone_value
ORDER BY milestone_value;













