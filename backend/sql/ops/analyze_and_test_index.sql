-- ============================================================================
-- Script: Analizar y probar índice parcial
-- ============================================================================
-- Este script:
-- 1. Verifica que el índice existe
-- 2. Obtiene estadísticas de la tabla
-- 3. Ejecuta ANALYZE para actualizar estadísticas
-- 4. Compara planes de ejecución con/sin Seq Scan
-- ============================================================================

-- 1. Verificar índices existentes
SELECT 
    '=== INDICES EN mv_yango_cabinet_claims_for_collection ===' AS seccion,
    indexname,
    indexdef
FROM pg_indexes
WHERE schemaname = 'ops'
    AND tablename = 'mv_yango_cabinet_claims_for_collection'
ORDER BY indexname;

-- 2. Estadísticas de la tabla
SELECT 
    '=== ESTADISTICAS DE LA TABLA ===' AS seccion,
    COUNT(*) AS total_rows,
    COUNT(*) FILTER (WHERE yango_payment_status = 'PAID_MISAPPLIED') AS misapplied_count,
    COUNT(*) FILTER (WHERE is_reconcilable_enriched = true) AS reconcilable_count,
    COUNT(*) FILTER (WHERE yango_payment_status = 'PAID_MISAPPLIED' AND is_reconcilable_enriched = true) AS misapplied_reconcilable_count,
    COUNT(*) FILTER (WHERE yango_payment_status = 'PAID_MISAPPLIED' AND is_reconcilable_enriched = false) AS misapplied_not_reconcilable_count
FROM ops.mv_yango_cabinet_claims_for_collection;

-- 3. Actualizar estadísticas (importante para que el optimizador use el índice)
ANALYZE ops.mv_yango_cabinet_claims_for_collection;

-- 4. EXPLAIN ANALYZE con comportamiento normal
SELECT '=== PLAN DE EJECUCION (NORMAL) ===' AS seccion;
EXPLAIN ANALYZE
SELECT * FROM ops.mv_yango_cabinet_claims_for_collection
WHERE yango_payment_status='PAID_MISAPPLIED' AND is_reconcilable_enriched=true
LIMIT 50;

-- 5. EXPLAIN ANALYZE forzando uso de índice (deshabilitando Seq Scan)
SELECT '=== PLAN DE EJECUCION (FORZANDO INDICE) ===' AS seccion;
SET enable_seqscan = off;
EXPLAIN ANALYZE
SELECT * FROM ops.mv_yango_cabinet_claims_for_collection
WHERE yango_payment_status='PAID_MISAPPLIED' AND is_reconcilable_enriched=true
LIMIT 50;
SET enable_seqscan = on;

-- 6. Verificar tamaño del índice
SELECT 
    '=== TAMAÑO DEL INDICE ===' AS seccion,
    pg_size_pretty(pg_relation_size('ops.idx_mv_yango_cabinet_claims_misapplied_reconcilable')) AS index_size,
    pg_size_pretty(pg_relation_size('ops.mv_yango_cabinet_claims_for_collection')) AS table_size;






