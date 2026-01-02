-- ============================================================================
-- Script de Diagnóstico: Verificar Índice Parcial y Uso
-- ============================================================================
-- Ejecutar este script en tu cliente SQL para diagnosticar por qué el índice
-- no se está usando.
-- ============================================================================

-- 1. Verificar que el índice existe y su definición
SELECT 
    '=== INDICES EXISTENTES ===' AS seccion,
    indexname,
    indexdef
FROM pg_indexes
WHERE schemaname = 'ops'
    AND tablename = 'mv_yango_cabinet_claims_for_collection'
ORDER BY indexname;

-- 2. Estadísticas de la tabla
SELECT 
    '=== ESTADISTICAS ===' AS seccion,
    COUNT(*) AS total_rows,
    COUNT(*) FILTER (WHERE yango_payment_status = 'PAID_MISAPPLIED') AS misapplied_count,
    COUNT(*) FILTER (WHERE is_reconcilable_enriched = true) AS reconcilable_count,
    COUNT(*) FILTER (WHERE yango_payment_status = 'PAID_MISAPPLIED' AND is_reconcilable_enriched = true) AS misapplied_reconcilable_count,
    COUNT(*) FILTER (WHERE yango_payment_status = 'PAID_MISAPPLIED' AND is_reconcilable_enriched = false) AS misapplied_not_reconcilable_count
FROM ops.mv_yango_cabinet_claims_for_collection;

-- 3. Actualizar estadísticas
ANALYZE ops.mv_yango_cabinet_claims_for_collection;

-- 4. EXPLAIN ANALYZE - Consulta original (puede que no haya filas)
SELECT '=== PLAN: Consulta Original (PAID_MISAPPLIED + is_reconcilable_enriched=true) ===' AS seccion;
EXPLAIN ANALYZE
SELECT * FROM ops.mv_yango_cabinet_claims_for_collection
WHERE yango_payment_status='PAID_MISAPPLIED' AND is_reconcilable_enriched=true
LIMIT 50;

-- 5. EXPLAIN ANALYZE - Solo PAID_MISAPPLIED (debería usar el índice parcial)
SELECT '=== PLAN: Solo PAID_MISAPPLIED (deberia usar indice parcial) ===' AS seccion;
EXPLAIN ANALYZE
SELECT * FROM ops.mv_yango_cabinet_claims_for_collection
WHERE yango_payment_status='PAID_MISAPPLIED'
LIMIT 50;

-- 6. EXPLAIN ANALYZE - PAID_MISAPPLIED + is_reconcilable_enriched=false (debería usar el índice)
SELECT '=== PLAN: PAID_MISAPPLIED + is_reconcilable_enriched=false ===' AS seccion;
EXPLAIN ANALYZE
SELECT * FROM ops.mv_yango_cabinet_claims_for_collection
WHERE yango_payment_status='PAID_MISAPPLIED' AND is_reconcilable_enriched=false
LIMIT 50;

-- 7. Forzar uso del índice (deshabilitar Seq Scan)
SELECT '=== PLAN: Forzando uso de indice (enable_seqscan=off) ===' AS seccion;
SET enable_seqscan = off;
EXPLAIN ANALYZE
SELECT * FROM ops.mv_yango_cabinet_claims_for_collection
WHERE yango_payment_status='PAID_MISAPPLIED' AND is_reconcilable_enriched=true
LIMIT 50;
SET enable_seqscan = on;

-- 8. Verificar estadísticas del índice
SELECT 
    '=== ESTADISTICAS DEL INDICE ===' AS seccion,
    indexrelname AS index_name,
    idx_scan AS index_scans,
    idx_tup_read AS tuples_read,
    idx_tup_fetch AS tuples_fetched
FROM pg_stat_user_indexes
WHERE schemaname = 'ops'
    AND tablename = 'mv_yango_cabinet_claims_for_collection'
    AND indexrelname LIKE '%misapplied%reconcilable%';

-- 9. Tamaño del índice vs tabla
SELECT 
    '=== TAMAÑOS ===' AS seccion,
    pg_size_pretty(pg_relation_size('ops.idx_mv_yango_cabinet_claims_misapplied_reconcilable')) AS index_size,
    pg_size_pretty(pg_relation_size('ops.mv_yango_cabinet_claims_for_collection')) AS table_size;

-- 10. Verificar si el índice está marcado como válido
SELECT 
    '=== ESTADO DEL INDICE ===' AS seccion,
    i.relname AS index_name,
    CASE 
        WHEN NOT indisvalid THEN 'INVALID'
        WHEN indisready AND NOT indisvalid THEN 'READY'
        ELSE 'VALID'
    END AS index_status
FROM pg_index idx
JOIN pg_class i ON i.oid = idx.indexrelid
JOIN pg_class t ON t.oid = idx.indrelid
JOIN pg_namespace n ON n.oid = t.relnamespace
WHERE n.nspname = 'ops'
    AND t.relname = 'mv_yango_cabinet_claims_for_collection'
    AND i.relname LIKE '%misapplied%reconcilable%';





