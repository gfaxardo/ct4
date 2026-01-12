-- ============================================================================
-- Script de Validación: Cobranza Yango - Performance y Sanity Checks
-- ============================================================================
-- PROPÓSITO:
-- Validar que la MV enriched funciona correctamente y que los índices
-- están optimizando las queries. Ejecutar después de crear/refrescar la MV.
-- ============================================================================

-- ============================================================================
-- 1) SANITY CHECKS: Conteos básicos
-- ============================================================================

SELECT 
    '=== SANITY CHECKS ===' AS section;

-- Total drivers
SELECT 
    'Total Drivers' AS metric,
    COUNT(*) AS value
FROM ops.mv_yango_cabinet_cobranza_enriched_14d;

-- Drivers con scout
SELECT 
    'Drivers con Scout' AS metric,
    COUNT(*) AS value
FROM ops.mv_yango_cabinet_cobranza_enriched_14d
WHERE scout_id IS NOT NULL;

-- Drivers sin scout
SELECT 
    'Drivers sin Scout' AS metric,
    COUNT(*) AS value
FROM ops.mv_yango_cabinet_cobranza_enriched_14d
WHERE scout_id IS NULL;

-- Porcentaje con scout
SELECT 
    'Porcentaje con Scout' AS metric,
    ROUND(
        (COUNT(CASE WHEN scout_id IS NOT NULL THEN 1 END)::NUMERIC / 
         NULLIF(COUNT(*), 0)) * 100, 
        2
    ) AS value
FROM ops.mv_yango_cabinet_cobranza_enriched_14d;

-- ============================================================================
-- 2) GAP ANALYSIS: Drivers con milestone pero sin scout
-- ============================================================================

SELECT 
    '=== GAP ANALYSIS ===' AS section;

-- Drivers con milestone alcanzado pero sin scout
SELECT 
    'Drivers con Milestone pero Sin Scout' AS metric,
    COUNT(*) AS value
FROM ops.mv_yango_cabinet_cobranza_enriched_14d
WHERE (reached_m1_14d = true OR reached_m5_14d = true OR reached_m25_14d = true)
    AND scout_id IS NULL;

-- Top 50 drivers sin scout con milestone
SELECT 
    '=== TOP 50 SIN SCOUT CON MILESTONE ===' AS section;

SELECT 
    driver_id,
    person_key,
    lead_date,
    reached_m1_14d,
    reached_m5_14d,
    reached_m25_14d,
    amount_due_yango,
    expected_total_yango
FROM ops.mv_yango_cabinet_cobranza_enriched_14d
WHERE (reached_m1_14d = true OR reached_m5_14d = true OR reached_m25_14d = true)
    AND scout_id IS NULL
ORDER BY amount_due_yango DESC NULLS LAST, lead_date DESC NULLS LAST
LIMIT 50;

-- ============================================================================
-- 3) DISTRIBUCIÓN POR SCOUT SOURCE Y QUALITY
-- ============================================================================

SELECT 
    '=== DISTRIBUCIÓN POR SCOUT SOURCE ===' AS section;

SELECT 
    scout_source_table,
    COUNT(*) AS count,
    ROUND(COUNT(*)::NUMERIC / NULLIF((SELECT COUNT(*) FROM ops.mv_yango_cabinet_cobranza_enriched_14d WHERE scout_id IS NOT NULL), 0) * 100, 2) AS pct
FROM ops.mv_yango_cabinet_cobranza_enriched_14d
WHERE scout_id IS NOT NULL
GROUP BY scout_source_table
ORDER BY count DESC;

SELECT 
    '=== DISTRIBUCIÓN POR SCOUT QUALITY BUCKET ===' AS section;

SELECT 
    scout_quality_bucket,
    COUNT(*) AS count,
    ROUND(COUNT(*)::NUMERIC / NULLIF((SELECT COUNT(*) FROM ops.mv_yango_cabinet_cobranza_enriched_14d WHERE scout_id IS NOT NULL), 0) * 100, 2) AS pct
FROM ops.mv_yango_cabinet_cobranza_enriched_14d
WHERE scout_id IS NOT NULL
GROUP BY scout_quality_bucket
ORDER BY count DESC;

-- ============================================================================
-- 4) PERFORMANCE: EXPLAIN ANALYZE
-- ============================================================================

SELECT 
    '=== PERFORMANCE: EXPLAIN ANALYZE ===' AS section;

-- Query típica con filtros (only_with_debt + milestone M25 + limit 100)
EXPLAIN (ANALYZE, BUFFERS, VERBOSE)
SELECT 
    driver_id,
    driver_name,
    lead_date,
    amount_due_yango,
    scout_id,
    scout_name,
    scout_quality_bucket
FROM ops.mv_yango_cabinet_cobranza_enriched_14d
WHERE amount_due_yango > 0
    AND reached_m25_14d = true
ORDER BY lead_date DESC NULLS LAST, driver_id
LIMIT 100;

-- Query con filtro week_start
EXPLAIN (ANALYZE, BUFFERS, VERBOSE)
SELECT 
    driver_id,
    driver_name,
    lead_date,
    week_start,
    amount_due_yango,
    scout_id,
    scout_name
FROM ops.mv_yango_cabinet_cobranza_enriched_14d
WHERE amount_due_yango > 0
    AND week_start = (SELECT MAX(week_start) FROM ops.mv_yango_cabinet_cobranza_enriched_14d WHERE week_start IS NOT NULL)
ORDER BY lead_date DESC NULLS LAST, driver_id
LIMIT 100;

-- ============================================================================
-- 5) VERIFICACIÓN DE ÍNDICES
-- ============================================================================

SELECT 
    '=== ÍNDICES CREADOS ===' AS section;

SELECT 
    schemaname,
    tablename,
    indexname,
    indexdef
FROM pg_indexes
WHERE schemaname = 'ops'
    AND tablename = 'mv_yango_cabinet_cobranza_enriched_14d'
ORDER BY indexname;

-- ============================================================================
-- 6) VERIFICACIÓN DE CONSISTENCIA: MV vs Vista Base
-- ============================================================================

SELECT 
    '=== CONSISTENCIA: MV vs Vista Base ===' AS section;

-- Comparar conteos (deberían ser similares, MV puede tener más filas si incluye enriquecimiento)
SELECT 
    'MV Enriched' AS source,
    COUNT(*) AS total_drivers,
    COUNT(CASE WHEN amount_due_yango > 0 THEN 1 END) AS with_debt,
    COUNT(CASE WHEN scout_id IS NOT NULL THEN 1 END) AS with_scout
FROM ops.mv_yango_cabinet_cobranza_enriched_14d
UNION ALL
SELECT 
    'Vista Base' AS source,
    COUNT(*) AS total_drivers,
    COUNT(CASE WHEN amount_due_yango > 0 THEN 1 END) AS with_debt,
    0 AS with_scout  -- Vista base no tiene scout
FROM ops.v_cabinet_financial_14d;
