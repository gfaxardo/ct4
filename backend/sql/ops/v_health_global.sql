-- ============================================================================
-- Vista: ops.v_health_global
-- ============================================================================
-- Vista que agrega el estado global de salud del sistema basado en checks.
-- ============================================================================

CREATE OR REPLACE VIEW ops.v_health_global AS
WITH check_statuses AS (
    SELECT 
        severity,
        status,
        COUNT(*) as count
    FROM ops.v_health_checks
    GROUP BY severity, status
),
status_summary AS (
    SELECT
        COALESCE(SUM(CASE WHEN severity = 'error' AND status = 'ERROR' THEN count ELSE 0 END), 0) AS error_count,
        COALESCE(SUM(CASE WHEN severity = 'warning' AND status = 'WARN' THEN count ELSE 0 END), 0) AS warn_count,
        COALESCE(SUM(CASE WHEN status = 'OK' THEN count ELSE 0 END), 0) AS ok_count
    FROM check_statuses
)
SELECT
    CASE
        WHEN error_count > 0 THEN 'ERROR'
        WHEN warn_count > 0 THEN 'WARN'
        ELSE 'OK'
    END AS global_status,
    error_count,
    warn_count,
    ok_count,
    NOW() AS calculated_at
FROM status_summary;

COMMENT ON VIEW ops.v_health_global IS 
'Vista que agrega el estado global de salud del sistema basado en checks.';

COMMENT ON COLUMN ops.v_health_global.global_status IS 
'Estado global: OK, WARN, o ERROR. ERROR si hay checks con severity=error y status=ERROR. WARN si hay checks con status WARN o ERROR. OK en caso contrario.';

COMMENT ON COLUMN ops.v_health_global.error_count IS 
'Número de checks con severity=error y status=ERROR.';

COMMENT ON COLUMN ops.v_health_global.warn_count IS 
'Número de checks con severity=warning y status=WARN.';

COMMENT ON COLUMN ops.v_health_global.ok_count IS 
'Número de checks con status=OK.';

COMMENT ON COLUMN ops.v_health_global.calculated_at IS 
'Timestamp de cálculo del estado global.';




