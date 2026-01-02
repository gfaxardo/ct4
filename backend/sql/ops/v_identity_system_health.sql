-- ============================================================================
-- Vista: ops.v_identity_system_health
-- ============================================================================
-- Propósito: Proporciona métricas agregadas de salud del sistema de identidad
-- canónica en una sola fila.
--
-- Retorna: 1 fila con todas las métricas del sistema de identidad
-- - Estado de última corrida de identidad
-- - Delay desde última corrida exitosa
-- - Unmatched pendientes
-- - Alertas activas
-- - Totales del registro canónico
--
-- Uso:
--   SELECT * FROM ops.v_identity_system_health;
-- ============================================================================

CREATE OR REPLACE VIEW ops.v_identity_system_health AS
WITH 
-- Última corrida de identidad (job_type = 'identity_run')
last_run AS (
    SELECT 
        id,
        started_at,
        completed_at,
        status::text AS status,
        error_message
    FROM ops.ingestion_runs
    WHERE job_type = 'identity_run'
    ORDER BY started_at DESC
    LIMIT 1
),

-- Última corrida completada exitosamente
last_completed_run AS (
    SELECT 
        completed_at
    FROM ops.ingestion_runs
    WHERE job_type = 'identity_run' 
        AND status = 'COMPLETED'
        AND completed_at IS NOT NULL
    ORDER BY completed_at DESC
    LIMIT 1
),

-- Unmatched abiertos agregados por reason_code
unmatched_by_reason AS (
    SELECT 
        reason_code,
        COUNT(*) AS count
    FROM canon.identity_unmatched
    WHERE status = 'OPEN'
    GROUP BY reason_code
),

-- Alertas activas agregadas por severidad
alerts_by_severity AS (
    SELECT 
        severity::text AS severity,
        COUNT(*) AS count
    FROM ops.alerts
    WHERE acknowledged_at IS NULL
    GROUP BY severity
),

-- Links agregados por source_table
links_by_source AS (
    SELECT 
        source_table,
        COUNT(*) AS count
    FROM canon.identity_links
    GROUP BY source_table
)

SELECT 
    -- Timestamp de cálculo
    NOW() AS calculated_at,
    
    -- ========================================================================
    -- Última corrida de identidad
    -- ========================================================================
    lr.id AS last_run_id,
    lr.started_at AS last_run_started_at,
    lr.completed_at AS last_run_completed_at,
    COALESCE(lr.status, 'NO_RUNS') AS last_run_status,
    lr.error_message AS last_run_error_message,
    
    -- ========================================================================
    -- Delay desde última corrida completada exitosamente
    -- ========================================================================
    CASE 
        WHEN lcr.completed_at IS NOT NULL 
        THEN FLOOR(EXTRACT(EPOCH FROM (NOW() - lcr.completed_at)) / 60)::int
        ELSE NULL
    END AS minutes_since_last_completed_run,
    
    CASE 
        WHEN lcr.completed_at IS NOT NULL 
        THEN FLOOR(EXTRACT(EPOCH FROM (NOW() - lcr.completed_at)) / 3600)::int
        ELSE NULL
    END AS hours_since_last_completed_run,
    
    -- ========================================================================
    -- Unmatched abiertos
    -- ========================================================================
    COALESCE((SELECT COUNT(*) FROM canon.identity_unmatched WHERE status = 'OPEN'), 0) AS unmatched_open_count,
    
    -- Unmatched por reason_code (JSONB)
    COALESCE(
        (SELECT jsonb_object_agg(reason_code, count) 
         FROM unmatched_by_reason),
        '{}'::jsonb
    ) AS unmatched_open_by_reason,
    
    -- ========================================================================
    -- Alertas activas
    -- ========================================================================
    COALESCE((SELECT COUNT(*) FROM ops.alerts WHERE acknowledged_at IS NULL), 0) AS active_alerts_count,
    
    -- Alertas por severidad (JSONB)
    COALESCE(
        (SELECT jsonb_object_agg(severity, count) 
         FROM alerts_by_severity),
        '{}'::jsonb
    ) AS active_alerts_by_severity,
    
    -- ========================================================================
    -- Registro canónico
    -- ========================================================================
    COALESCE((SELECT COUNT(*) FROM canon.identity_registry), 0) AS total_persons,
    COALESCE((SELECT COUNT(*) FROM canon.identity_links), 0) AS total_links,
    
    -- Links por source_table (JSONB)
    COALESCE(
        (SELECT jsonb_object_agg(source_table, count) 
         FROM links_by_source),
        '{}'::jsonb
    ) AS links_by_source
FROM 
    -- Asegurar que siempre retorne 1 fila, incluso si no hay corridas
    (SELECT 1) AS dummy
    LEFT JOIN last_run lr ON true
    LEFT JOIN last_completed_run lcr ON true;

-- ============================================================================
-- Comentarios
-- ============================================================================

COMMENT ON VIEW ops.v_identity_system_health IS 
'Vista de salud del sistema de identidad canónica. Retorna 1 fila con métricas agregadas: última corrida, delay, unmatched, alertas y totales del registro canónico.';

COMMENT ON COLUMN ops.v_identity_system_health.calculated_at IS 
'Timestamp de cuando se calculó esta métrica (NOW()).';

COMMENT ON COLUMN ops.v_identity_system_health.last_run_id IS 
'ID de la última corrida de identidad (job_type = identity_run). NULL si no hay corridas.';

COMMENT ON COLUMN ops.v_identity_system_health.last_run_started_at IS 
'Fecha/hora de inicio de la última corrida de identidad. NULL si no hay corridas.';

COMMENT ON COLUMN ops.v_identity_system_health.last_run_completed_at IS 
'Fecha/hora de finalización de la última corrida. NULL si aún está corriendo o no hay corridas.';

COMMENT ON COLUMN ops.v_identity_system_health.last_run_status IS 
'Estado de la última corrida: RUNNING, COMPLETED, FAILED, o NO_RUNS si no hay corridas.';

COMMENT ON COLUMN ops.v_identity_system_health.minutes_since_last_completed_run IS 
'Minutos transcurridos desde la última corrida completada exitosamente. NULL si no hay corridas completadas.';

COMMENT ON COLUMN ops.v_identity_system_health.hours_since_last_completed_run IS 
'Horas transcurridas desde la última corrida completada exitosamente. NULL si no hay corridas completadas.';

COMMENT ON COLUMN ops.v_identity_system_health.last_run_error_message IS 
'Mensaje de error de la última corrida. NULL si no hay error o no hay corridas.';

COMMENT ON COLUMN ops.v_identity_system_health.unmatched_open_count IS 
'Total de registros unmatched con status = OPEN. 0 si no hay unmatched.';

COMMENT ON COLUMN ops.v_identity_system_health.unmatched_open_by_reason IS 
'JSONB con conteo de unmatched por reason_code. Formato: {"reason_code": count, ...}. {} si no hay unmatched.';

COMMENT ON COLUMN ops.v_identity_system_health.active_alerts_count IS 
'Total de alertas activas (acknowledged_at IS NULL). 0 si no hay alertas activas.';

COMMENT ON COLUMN ops.v_identity_system_health.active_alerts_by_severity IS 
'JSONB con conteo de alertas activas por severidad. Formato: {"info": count, "warning": count, "error": count}. {} si no hay alertas.';

COMMENT ON COLUMN ops.v_identity_system_health.total_persons IS 
'Total de personas en el registro canónico (canon.identity_registry). 0 si está vacío.';

COMMENT ON COLUMN ops.v_identity_system_health.total_links IS 
'Total de vínculos creados (canon.identity_links). 0 si está vacío.';

COMMENT ON COLUMN ops.v_identity_system_health.links_by_source IS 
'JSONB con conteo de links por source_table. Formato: {"source_table": count, ...}. {} si no hay links.';

-- ============================================================================
-- Ejemplo de uso
-- ============================================================================
-- 
-- Aplicar la vista:
--   \i backend/sql/ops/v_identity_system_health.sql
--
-- Consultar la vista:
--   SELECT * FROM ops.v_identity_system_health;
--
-- Ejemplo de salida esperada:
--   calculated_at                    | 2024-01-15 10:30:00+00
--   last_run_id                      | 42
--   last_run_started_at              | 2024-01-15 09:00:00+00
--   last_run_completed_at            | 2024-01-15 09:15:00+00
--   last_run_status                  | COMPLETED
--   minutes_since_last_completed_run | 75
--   hours_since_last_completed_run   | 1
--   last_run_error_message           | NULL
--   unmatched_open_count             | 15
--   unmatched_open_by_reason          | {"NO_CANDIDATES": 10, "AMBIGUOUS": 5}
--   active_alerts_count              | 3
--   active_alerts_by_severity        | {"warning": 2, "info": 1}
--   total_persons                    | 1250
--   total_links                      | 3450
--   links_by_source                  | {"module_ct_cabinet_leads": 2000, "module_ct_scouting_daily": 1450}
-- ============================================================================

