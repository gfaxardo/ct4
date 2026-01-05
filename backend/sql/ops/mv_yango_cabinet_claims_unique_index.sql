-- ============================================================================
-- Índice Único para ops.mv_yango_cabinet_claims_for_collection
-- ============================================================================
-- PROPÓSITO:
-- Crear índice único en el grano canónico (driver_id, milestone_value) para
-- habilitar REFRESH MATERIALIZED VIEW CONCURRENTLY.
--
-- PREREQUISITOS:
-- 1. La MV NO debe tener duplicados por (driver_id, milestone_value)
--    - Verificar ejecutando: docs/ops/yango_cabinet_claims_mv_duplicates.sql (Query 2)
--    - Si Query 2 retorna filas, resolver duplicados antes de crear el índice
--
-- 2. Este comando NO puede ejecutarse dentro de una transacción
--    - CONCURRENTLY requiere que no haya transacción activa
--    - Ejecutar directamente con psql, no con BEGIN/COMMIT
--
-- GRANO CANÓNICO:
-- (driver_id, milestone_value)
--
-- USO:
--   psql -d database -f backend/sql/ops/mv_yango_cabinet_claims_unique_index.sql
--
-- O ejecutar directamente:
--   psql -d database -c "CREATE UNIQUE INDEX CONCURRENTLY IF NOT EXISTS ..."
-- ============================================================================

CREATE UNIQUE INDEX CONCURRENTLY IF NOT EXISTS ux_mv_yango_cabinet_claims_for_collection_grain
  ON ops.mv_yango_cabinet_claims_for_collection (driver_id, milestone_value);

COMMENT ON INDEX ops.ux_mv_yango_cabinet_claims_for_collection_grain IS 
'Índice único en el grano canónico (driver_id, milestone_value). 
Prerequisito para REFRESH MATERIALIZED VIEW CONCURRENTLY. 
Requiere que no haya duplicados por este grano.';

-- ============================================================================
-- Verificación post-creación
-- ============================================================================
-- Ejecutar después de crear el índice para confirmar que existe:
--
-- SELECT 
--     schemaname,
--     indexname,
--     indexdef
-- FROM pg_indexes
-- WHERE schemaname = 'ops'
--   AND tablename = 'mv_yango_cabinet_claims_for_collection'
--   AND indexname = 'ux_mv_yango_cabinet_claims_for_collection_grain';
-- ============================================================================



