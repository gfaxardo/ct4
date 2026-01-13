-- ============================================================================
-- Vista: ops.v_cabinet_kpi_red_recovery_metrics_daily
-- ============================================================================
-- PROPÓSITO:
-- Métricas diarias de recovery del KPI rojo:
-- - backlog_start: backlog al inicio del día
-- - new_backlog_in: cuántos leads entraron hoy al KPI rojo
-- - matched_out: cuántos salieron hoy por recovery
-- - backlog_end: backlog al final del día
-- - net_change: cambio neto (end - start)
-- - top_fail_reason: razón de fallo más común
-- ============================================================================
-- GRANO:
-- 1 fila por día
-- ============================================================================
-- FUENTES:
-- - ops.v_cabinet_kpi_red_backlog (backlog actual)
-- - ops.cabinet_kpi_red_recovery_queue (cola de recovery)
-- ============================================================================

CREATE OR REPLACE VIEW ops.v_cabinet_kpi_red_recovery_metrics_daily AS
WITH dates AS (
    -- Generar serie de fechas desde la fecha mínima hasta hoy
    SELECT generate_series(
        (SELECT MIN(lead_date) FROM ops.v_cabinet_kpi_red_backlog),
        CURRENT_DATE,
        '1 day'::interval
    )::DATE AS metric_date
),
daily_backlog AS (
    -- Backlog al inicio de cada día (usando snapshot histórico si existe, sino usando lead_date)
    SELECT
        d.metric_date,
        COUNT(DISTINCT krb.lead_source_pk) AS backlog_count
    FROM dates d
    LEFT JOIN ops.v_cabinet_kpi_red_backlog krb
        ON krb.lead_date <= d.metric_date
    GROUP BY d.metric_date
),
daily_matched AS (
    -- Leads matched cada día
    SELECT
        DATE(updated_at) AS match_date,
        COUNT(*) AS matched_count
    FROM ops.cabinet_kpi_red_recovery_queue
    WHERE status = 'matched'
        AND updated_at IS NOT NULL
    GROUP BY DATE(updated_at)
),
daily_fail_reasons AS (
    -- Razón de fallo más común por día (para leads failed)
    SELECT
        DATE(updated_at) AS fail_date,
        fail_reason,
        COUNT(*) AS fail_count,
        ROW_NUMBER() OVER (PARTITION BY DATE(updated_at) ORDER BY COUNT(*) DESC) AS rn
    FROM ops.cabinet_kpi_red_recovery_queue
    WHERE status = 'failed'
        AND updated_at IS NOT NULL
        AND fail_reason IS NOT NULL
    GROUP BY DATE(updated_at), fail_reason
),
top_fail_reason_by_date AS (
    SELECT
        fail_date,
        fail_reason AS top_fail_reason
    FROM daily_fail_reasons
    WHERE rn = 1
),
daily_new_backlog AS (
    -- Leads que entraron al backlog cada día (aproximado por lead_date)
    SELECT
        lead_date AS new_date,
        COUNT(*) AS new_backlog_count
    FROM ops.v_cabinet_kpi_red_backlog
    GROUP BY lead_date
)
SELECT
    d.metric_date,
    COALESCE(db_backlog.backlog_count, 0) AS backlog_start,
    COALESCE(dnb.new_backlog_count, 0) AS new_backlog_in,
    COALESCE(dm.matched_count, 0) AS matched_out,
    COALESCE(db_backlog.backlog_count, 0) + COALESCE(dnb.new_backlog_count, 0) - COALESCE(dm.matched_count, 0) AS backlog_end,
    COALESCE(dnb.new_backlog_count, 0) - COALESCE(dm.matched_count, 0) AS net_change,
    tfr.top_fail_reason
FROM dates d
LEFT JOIN daily_backlog db_backlog ON db_backlog.metric_date = d.metric_date
LEFT JOIN daily_new_backlog dnb ON dnb.new_date = d.metric_date
LEFT JOIN daily_matched dm ON dm.match_date = d.metric_date
LEFT JOIN top_fail_reason_by_date tfr ON tfr.fail_date = d.metric_date
ORDER BY d.metric_date DESC;

COMMENT ON VIEW ops.v_cabinet_kpi_red_recovery_metrics_daily IS
'Vista que proporciona métricas diarias de recovery del KPI rojo.';

COMMENT ON COLUMN ops.v_cabinet_kpi_red_recovery_metrics_daily.metric_date IS
'Fecha de la métrica.';

COMMENT ON COLUMN ops.v_cabinet_kpi_red_recovery_metrics_daily.backlog_start IS
'Backlog al inicio del día.';

COMMENT ON COLUMN ops.v_cabinet_kpi_red_recovery_metrics_daily.new_backlog_in IS
'Leads que entraron al backlog en este día.';

COMMENT ON COLUMN ops.v_cabinet_kpi_red_recovery_metrics_daily.matched_out IS
'Leads que fueron matched (salieron del backlog) en este día.';

COMMENT ON COLUMN ops.v_cabinet_kpi_red_recovery_metrics_daily.backlog_end IS
'Backlog al final del día (backlog_start + new_backlog_in - matched_out).';

COMMENT ON COLUMN ops.v_cabinet_kpi_red_recovery_metrics_daily.net_change IS
'Cambio neto del backlog (new_backlog_in - matched_out).';

COMMENT ON COLUMN ops.v_cabinet_kpi_red_recovery_metrics_daily.top_fail_reason IS
'Razón de fallo más común en los leads matched este día.';
