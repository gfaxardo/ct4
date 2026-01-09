-- ============================================================================
-- QUERY OPERATIVA: Claims para Cobrar a Yango
-- ============================================================================
-- PROPÓSITO:
-- SELECT claro que liste SOLO lo exigible a Yango hoy (equivalente a "EXIGIMOS").
-- Ordenado, exportable a Excel, sin depender de columnas inexistentes.
--
-- VALIDACIÓN:
-- - Debe coincidir con ops.v_yango_cabinet_claims_exec_summary section='EXIGIMOS'
-- - Suma de expected_amount debe ser igual a la suma en exec_summary
-- ============================================================================

-- ============================================================================
-- QUERY 3.1: SELECT directo desde v_yango_cabinet_claims_exigimos
-- ============================================================================
-- Esta vista ya filtra UNPAID y driver_id IS NOT NULL
-- ============================================================================

SELECT 
    '=== QUERY 3.1: Claims para Cobrar (Directo desde v_yango_cabinet_claims_exigimos) ===' AS seccion;

SELECT 
    -- Identificación del claim
    claim_key,
    driver_id,
    driver_name,
    person_key,
    milestone_value,
    
    -- Monto exigible
    expected_amount,
    
    -- Fechas
    lead_date,
    yango_due_date,
    days_overdue_yango,
    overdue_bucket_yango,
    
    -- Estado y diagnóstico
    yango_payment_status,
    reason_code,
    identity_status,
    match_rule,
    match_confidence,
    is_reconcilable_enriched,
    
    -- Campos adicionales
    payment_key,
    pay_date,
    suggested_driver_id
    
FROM ops.v_yango_cabinet_claims_exigimos
ORDER BY 
    days_overdue_yango DESC,
    expected_amount DESC,
    driver_id,
    milestone_value;

-- ============================================================================
-- QUERY 3.2: Versión exportable a Excel
-- ============================================================================
-- Columnas optimizadas para exportación, con nombres amigables
-- ============================================================================

SELECT 
    '=== QUERY 3.2: Claims para Cobrar (Exportable a Excel) ===' AS seccion;

SELECT 
    -- Identificación
    driver_id AS "Driver ID",
    driver_name AS "Nombre Conductor",
    milestone_value AS "Milestone",
    
    -- Monto
    expected_amount AS "Monto Exigible (S/)",
    
    -- Fechas
    lead_date AS "Fecha Lead",
    yango_due_date AS "Fecha Vencimiento",
    days_overdue_yango AS "Días Vencidos",
    overdue_bucket_yango AS "Bucket Vencimiento",
    
    -- Estado
    yango_payment_status AS "Estado Pago",
    reason_code AS "Razón",
    identity_status AS "Estado Identidad",
    match_rule AS "Regla Matching",
    match_confidence AS "Confianza Matching",
    is_reconcilable_enriched AS "Reconciliable",
    
    -- Campos adicionales para contexto
    payment_key AS "Payment Key",
    pay_date AS "Fecha Pago Encontrado",
    suggested_driver_id AS "Driver ID Sugerido",
    person_key AS "Person Key"
    
FROM ops.v_yango_cabinet_claims_exigimos
ORDER BY 
    days_overdue_yango DESC,
    expected_amount DESC,
    driver_id,
    milestone_value;

-- ============================================================================
-- QUERY 3.3: Totales agregados por milestone
-- ============================================================================
-- Equivalente a "EXIGIMOS" del exec_summary
-- ============================================================================

SELECT 
    '=== QUERY 3.3: Totales Agregados por Milestone (EXIGIMOS) ===' AS seccion;

SELECT 
    milestone_value AS "Milestone",
    COUNT(*) AS "Cantidad Claims",
    SUM(expected_amount) AS "Total Exigible (S/)",
    COUNT(DISTINCT driver_id) AS "Conductores Únicos",
    COUNT(*) FILTER (WHERE is_reconcilable_enriched = true) AS "Reconciliables",
    COUNT(*) FILTER (WHERE is_reconcilable_enriched = false) AS "No Reconciliables",
    COUNT(*) FILTER (WHERE days_overdue_yango > 0) AS "Vencidos",
    COUNT(*) FILTER (WHERE days_overdue_yango = 0) AS "No Vencidos",
    MAX(days_overdue_yango) AS "Máx Días Vencidos",
    AVG(days_overdue_yango) AS "Promedio Días Vencidos"
FROM ops.v_yango_cabinet_claims_exigimos
GROUP BY milestone_value
ORDER BY milestone_value;

-- Total general
SELECT 
    'TOTAL' AS "Milestone",
    COUNT(*) AS "Cantidad Claims",
    SUM(expected_amount) AS "Total Exigible (S/)",
    COUNT(DISTINCT driver_id) AS "Conductores Únicos",
    COUNT(*) FILTER (WHERE is_reconcilable_enriched = true) AS "Reconciliables",
    COUNT(*) FILTER (WHERE is_reconcilable_enriched = false) AS "No Reconciliables",
    COUNT(*) FILTER (WHERE days_overdue_yango > 0) AS "Vencidos",
    COUNT(*) FILTER (WHERE days_overdue_yango = 0) AS "No Vencidos",
    MAX(days_overdue_yango) AS "Máx Días Vencidos",
    AVG(days_overdue_yango) AS "Promedio Días Vencidos"
FROM ops.v_yango_cabinet_claims_exigimos;

-- ============================================================================
-- QUERY 3.4: Validación contra exec_summary
-- ============================================================================
-- Verificar que los totales coinciden con ops.v_yango_cabinet_claims_exec_summary
-- ============================================================================

SELECT 
    '=== QUERY 3.4: Validación contra Exec Summary ===' AS seccion;

-- Totales desde v_yango_cabinet_claims_exigimos
WITH exigimos_totals AS (
    SELECT 
        milestone_value::text AS category,
        COUNT(*) AS count_claims,
        SUM(expected_amount) AS amount
    FROM ops.v_yango_cabinet_claims_exigimos
    GROUP BY milestone_value
    
    UNION ALL
    
    SELECT 
        'TOTAL' AS category,
        COUNT(*) AS count_claims,
        SUM(expected_amount) AS amount
    FROM ops.v_yango_cabinet_claims_exigimos
),
exec_summary_totals AS (
    SELECT 
        category,
        count_claims,
        amount
    FROM ops.v_yango_cabinet_claims_exec_summary
    WHERE section = 'EXIGIMOS'
)
SELECT 
    COALESCE(e.category, s.category) AS "Categoría",
    COALESCE(e.count_claims, 0) AS "Count desde Exigimos",
    COALESCE(s.count_claims, 0) AS "Count desde Exec Summary",
    COALESCE(e.count_claims, 0) - COALESCE(s.count_claims, 0) AS "Diferencia Count",
    COALESCE(e.amount, 0) AS "Amount desde Exigimos",
    COALESCE(s.amount, 0) AS "Amount desde Exec Summary",
    COALESCE(e.amount, 0) - COALESCE(s.amount, 0) AS "Diferencia Amount",
    CASE 
        WHEN COALESCE(e.count_claims, 0) = COALESCE(s.count_claims, 0) 
            AND COALESCE(e.amount, 0) = COALESCE(s.amount, 0) 
        THEN 'OK'
        ELSE 'ERROR: No coinciden'
    END AS "Validación"
FROM exigimos_totals e
FULL OUTER JOIN exec_summary_totals s
    ON e.category = s.category
ORDER BY 
    CASE 
        WHEN COALESCE(e.category, s.category) = 'TOTAL' THEN 999
        ELSE CAST(COALESCE(e.category, s.category) AS INTEGER)
    END;

-- ============================================================================
-- QUERY 3.5: Desglose por bucket de vencimiento
-- ============================================================================
-- Agrupar claims por bucket de días vencidos para priorización
-- ============================================================================

SELECT 
    '=== QUERY 3.5: Desglose por Bucket de Vencimiento ===' AS seccion;

SELECT 
    overdue_bucket_yango AS "Bucket Vencimiento",
    COUNT(*) AS "Cantidad Claims",
    SUM(expected_amount) AS "Total Exigible (S/)",
    COUNT(DISTINCT driver_id) AS "Conductores Únicos",
    MIN(days_overdue_yango) AS "Mín Días",
    MAX(days_overdue_yango) AS "Máx Días",
    AVG(days_overdue_yango) AS "Promedio Días"
FROM ops.v_yango_cabinet_claims_exigimos
GROUP BY overdue_bucket_yango
ORDER BY 
    CASE overdue_bucket_yango
        WHEN '4_30_plus' THEN 1
        WHEN '3_15_30' THEN 2
        WHEN '2_8_14' THEN 3
        WHEN '1_1_7' THEN 4
        WHEN '0_not_due' THEN 5
        ELSE 6
    END;

-- ============================================================================
-- QUERY 3.6: Desglose por reconciliabilidad
-- ============================================================================
-- Separar claims reconciliables (con identidad confirmada) de no reconciliables
-- ============================================================================

SELECT 
    '=== QUERY 3.6: Desglose por Reconciliabilidad ===' AS seccion;

SELECT 
    is_reconcilable_enriched AS "Reconciliable",
    identity_status AS "Estado Identidad",
    match_confidence AS "Confianza Matching",
    COUNT(*) AS "Cantidad Claims",
    SUM(expected_amount) AS "Total Exigible (S/)",
    COUNT(DISTINCT driver_id) AS "Conductores Únicos"
FROM ops.v_yango_cabinet_claims_exigimos
GROUP BY is_reconcilable_enriched, identity_status, match_confidence
ORDER BY 
    is_reconcilable_enriched DESC,
    CASE match_confidence
        WHEN 'high' THEN 1
        WHEN 'medium' THEN 2
        WHEN 'low' THEN 3
        ELSE 4
    END;

-- ============================================================================
-- QUERY 3.7: Top 20 claims por monto (priorización)
-- ============================================================================
-- Los claims con mayor monto exigible para priorizar cobranza
-- ============================================================================

SELECT 
    '=== QUERY 3.7: Top 20 Claims por Monto (Priorización) ===' AS seccion;

SELECT 
    driver_id AS "Driver ID",
    driver_name AS "Nombre Conductor",
    milestone_value AS "Milestone",
    expected_amount AS "Monto Exigible (S/)",
    days_overdue_yango AS "Días Vencidos",
    overdue_bucket_yango AS "Bucket Vencimiento",
    is_reconcilable_enriched AS "Reconciliable",
    identity_status AS "Estado Identidad",
    match_confidence AS "Confianza Matching"
FROM ops.v_yango_cabinet_claims_exigimos
ORDER BY expected_amount DESC, days_overdue_yango DESC
LIMIT 20;

-- ============================================================================
-- QUERY 3.8: Resumen ejecutivo para reporte
-- ============================================================================
-- Resumen consolidado para presentación ejecutiva
-- ============================================================================

SELECT 
    '=== QUERY 3.8: Resumen Ejecutivo ===' AS seccion;

SELECT 
    'EXIGIMOS A YANGO' AS "Sección",
    COUNT(*) AS "Total Claims",
    SUM(expected_amount) AS "Total Exigible (S/)",
    COUNT(DISTINCT driver_id) AS "Conductores Únicos",
    COUNT(*) FILTER (WHERE milestone_value = 1) AS "Claims Milestone 1",
    SUM(expected_amount) FILTER (WHERE milestone_value = 1) AS "Monto Milestone 1 (S/)",
    COUNT(*) FILTER (WHERE milestone_value = 5) AS "Claims Milestone 5",
    SUM(expected_amount) FILTER (WHERE milestone_value = 5) AS "Monto Milestone 5 (S/)",
    COUNT(*) FILTER (WHERE milestone_value = 25) AS "Claims Milestone 25",
    SUM(expected_amount) FILTER (WHERE milestone_value = 25) AS "Monto Milestone 25 (S/)",
    COUNT(*) FILTER (WHERE days_overdue_yango > 0) AS "Claims Vencidos",
    SUM(expected_amount) FILTER (WHERE days_overdue_yango > 0) AS "Monto Vencido (S/)",
    COUNT(*) FILTER (WHERE is_reconcilable_enriched = true) AS "Claims Reconciliables",
    SUM(expected_amount) FILTER (WHERE is_reconcilable_enriched = true) AS "Monto Reconciliable (S/)"
FROM ops.v_yango_cabinet_claims_exigimos;

-- ============================================================================
-- NOTAS DE USO
-- ============================================================================
-- 1. QUERY 3.2 es la recomendada para exportar a Excel
-- 2. QUERY 3.3 proporciona totales agregados por milestone
-- 3. QUERY 3.4 valida que los datos coinciden con exec_summary
-- 4. QUERY 3.5 ayuda a priorizar por días vencidos
-- 5. QUERY 3.6 separa claims reconciliables de no reconciliables
-- 6. QUERY 3.7 lista los top claims por monto para priorización
-- 7. QUERY 3.8 proporciona un resumen ejecutivo consolidado
-- ============================================================================










