-- ============================================================================
-- Health Check SQL para ops.mv_yango_cabinet_claims_for_collection
-- ============================================================================
-- Devuelve estado de salud de la MV basado en ops.mv_refresh_log
-- ============================================================================
-- 
-- Uso:
--   SELECT * FROM ops.v_yango_cabinet_claims_mv_health;
-- 
-- O ejecutar directamente:
--   psql -d database -f docs/ops/yango_cabinet_claims_mv_health.sql
-- ============================================================================

-- Crear vista de health check si no existe
CREATE OR REPLACE VIEW ops.v_yango_cabinet_claims_mv_health AS
SELECT 
    'ops.mv_yango_cabinet_claims_for_collection' AS mv_name,
    
    -- Último refresh exitoso
    MAX(CASE WHEN status IN ('OK', 'SUCCESS') THEN refresh_finished_at 
             WHEN status IN ('OK', 'SUCCESS') AND refresh_finished_at IS NULL THEN refreshed_at 
             ELSE NULL END) AS last_ok_refresh_finished_at,
    
    -- Horas desde último refresh exitoso
    EXTRACT(EPOCH FROM (NOW() - MAX(CASE WHEN status IN ('OK', 'SUCCESS') THEN refresh_finished_at 
                                          WHEN status IN ('OK', 'SUCCESS') AND refresh_finished_at IS NULL THEN refreshed_at 
                                          ELSE NULL END))) / 3600.0 AS hours_since_ok_refresh,
    
    -- Bucket de status basado en horas
    CASE 
        WHEN MAX(CASE WHEN status IN ('OK', 'SUCCESS') THEN refresh_finished_at 
                      WHEN status IN ('OK', 'SUCCESS') AND refresh_finished_at IS NULL THEN refreshed_at 
                      ELSE NULL END) IS NULL THEN 'NO_REFRESH'
        WHEN EXTRACT(EPOCH FROM (NOW() - MAX(CASE WHEN status IN ('OK', 'SUCCESS') THEN refresh_finished_at 
                                                   WHEN status IN ('OK', 'SUCCESS') AND refresh_finished_at IS NULL THEN refreshed_at 
                                                   ELSE NULL END))) / 3600.0 < 24 THEN 'OK'
        WHEN EXTRACT(EPOCH FROM (NOW() - MAX(CASE WHEN status IN ('OK', 'SUCCESS') THEN refresh_finished_at 
                                                   WHEN status IN ('OK', 'SUCCESS') AND refresh_finished_at IS NULL THEN refreshed_at 
                                                   ELSE NULL END))) / 3600.0 < 48 THEN 'WARN'
        ELSE 'CRIT'
    END AS status_bucket,
    
    -- Último status (OK, ERROR, RUNNING, etc.)
    (SELECT status 
     FROM ops.mv_refresh_log 
     WHERE schema_name = 'ops' 
       AND mv_name = 'mv_yango_cabinet_claims_for_collection'
     ORDER BY refresh_started_at DESC, refreshed_at DESC
     LIMIT 1) AS last_status,
    
    -- Último error si existe
    (SELECT error_message 
     FROM ops.mv_refresh_log 
     WHERE schema_name = 'ops' 
       AND mv_name = 'mv_yango_cabinet_claims_for_collection'
       AND status IN ('ERROR', 'FAILED')
     ORDER BY refresh_started_at DESC, refreshed_at DESC
     LIMIT 1) AS last_error,
    
    -- Filas después del último refresh exitoso
    (SELECT rows_after_refresh 
     FROM ops.mv_refresh_log 
     WHERE schema_name = 'ops' 
       AND mv_name = 'mv_yango_cabinet_claims_for_collection'
       AND status IN ('OK', 'SUCCESS')
     ORDER BY refresh_finished_at DESC, refreshed_at DESC
     LIMIT 1) AS rows_after_refresh,
    
    -- Timestamp de cálculo
    NOW() AS calculated_at

FROM ops.mv_refresh_log
WHERE schema_name = 'ops' 
  AND mv_name = 'mv_yango_cabinet_claims_for_collection';

COMMENT ON VIEW ops.v_yango_cabinet_claims_mv_health IS 
'Health check para ops.mv_yango_cabinet_claims_for_collection. 
Devuelve: last_ok_refresh_finished_at, hours_since_ok_refresh, status_bucket (OK <24h, WARN 24-48h, CRIT >48h), 
last_status, last_error, rows_after_refresh.';

-- ============================================================================
-- Query de ejemplo para verificar health
-- ============================================================================
-- SELECT * FROM ops.v_yango_cabinet_claims_mv_health;
-- ============================================================================








