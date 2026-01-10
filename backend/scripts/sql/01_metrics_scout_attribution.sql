-- ============================================================================
-- VISTAS: Métricas de Scout Attribution
-- ============================================================================
-- Propósito: Vistas SQL para métricas que alimentan la UI de observabilidad
-- Ejecución: Idempotente (DROP + CREATE)
-- ============================================================================

-- ============================================================================
-- 1. VISTA: ops.v_scout_attribution_metrics_snapshot
-- ============================================================================
-- Métricas instantáneas de atribución scout (para UI en tiempo real)
-- ============================================================================

DROP VIEW IF EXISTS ops.v_scout_attribution_metrics_snapshot CASCADE;

CREATE VIEW ops.v_scout_attribution_metrics_snapshot AS
WITH person_counts AS (
    SELECT 
        COUNT(DISTINCT ir.person_key) AS total_persons
    FROM canon.identity_registry ir
),
satisfactory_scout AS (
    SELECT 
        COUNT(DISTINCT ll.person_key) AS persons_with_scout_satisfactory
    FROM observational.lead_ledger ll
    WHERE ll.attributed_scout_id IS NOT NULL
),
missing_scout AS (
    SELECT 
        COUNT(DISTINCT ir.person_key) AS persons_missing_scout
    FROM canon.identity_registry ir
    WHERE NOT EXISTS (
        SELECT 1 FROM observational.lead_ledger ll
        WHERE ll.person_key = ir.person_key
            AND ll.attributed_scout_id IS NOT NULL
    )
),
conflicts_count AS (
    SELECT 
        COUNT(DISTINCT person_key) AS conflicts_count
    FROM ops.v_scout_attribution_conflicts
    WHERE EXISTS (
        SELECT 1 FROM information_schema.views
        WHERE table_schema = 'ops' AND table_name = 'v_scout_attribution_conflicts'
    )
),
backlog_a AS (
    SELECT 
        COUNT(DISTINCT person_key) AS backlog_a_events_without_scout
    FROM ops.v_persons_without_scout_categorized
    WHERE category = 'A'
    AND EXISTS (
        SELECT 1 FROM information_schema.views
        WHERE table_schema = 'ops' AND table_name = 'v_persons_without_scout_categorized'
    )
),
backlog_d AS (
    SELECT 
        COUNT(DISTINCT person_key) AS backlog_d_scout_in_events_not_in_ledger
    FROM ops.v_persons_without_scout_categorized
    WHERE category = 'D'
    AND EXISTS (
        SELECT 1 FROM information_schema.views
        WHERE table_schema = 'ops' AND table_name = 'v_persons_without_scout_categorized'
    )
),
backlog_c AS (
    SELECT 
        COUNT(DISTINCT person_key) AS backlog_c_legacy_no_events_no_ledger
    FROM ops.v_persons_without_scout_categorized
    WHERE category = 'C'
    AND EXISTS (
        SELECT 1 FROM information_schema.views
        WHERE table_schema = 'ops' AND table_name = 'v_persons_without_scout_categorized'
    )
),
last_job AS (
    SELECT 
        COALESCE(jr.status, NULL) AS last_job_status,
        COALESCE(jr.completed_at, NULL) AS last_job_ended_at,
        COALESCE(jr.started_at, NULL) AS last_job_started_at,
        COALESCE(jr.stats, NULL) AS last_job_summary,
        COALESCE(jr.error_message, NULL) AS last_job_error
    FROM (
        SELECT 
            job_type::TEXT AS job_type,
            status,
            completed_at,
            started_at,
            stats,
            error_message
        FROM ops.ingestion_runs
        WHERE job_type::TEXT = 'scout_attribution_refresh'
        ORDER BY completed_at DESC NULLS LAST, started_at DESC
        LIMIT 1
    ) jr
    UNION ALL
    SELECT NULL, NULL, NULL, NULL, NULL
    WHERE NOT EXISTS (
        SELECT 1 FROM ops.ingestion_runs
        WHERE job_type::TEXT = 'scout_attribution_refresh'
    )
    LIMIT 1
)
SELECT 
    pc.total_persons,
    COALESCE(ss.persons_with_scout_satisfactory, 0) AS persons_with_scout_satisfactory,
    CASE 
        WHEN pc.total_persons > 0 
        THEN ROUND((COALESCE(ss.persons_with_scout_satisfactory, 0)::NUMERIC / pc.total_persons * 100), 2)
        ELSE 0
    END AS pct_scout_satisfactory,
    COALESCE(ms.persons_missing_scout, 0) AS persons_missing_scout,
    COALESCE(cc.conflicts_count, 0) AS conflicts_count,
    COALESCE(ba.backlog_a_events_without_scout, 0) AS backlog_a_events_without_scout,
    COALESCE(bd.backlog_d_scout_in_events_not_in_ledger, 0) AS backlog_d_scout_in_events_not_in_ledger,
    COALESCE(bc.backlog_c_legacy_no_events_no_ledger, 0) AS backlog_c_legacy_no_events_no_ledger,
    lj.last_job_status,
    lj.last_job_ended_at,
    lj.last_job_started_at,
    CASE 
        WHEN lj.last_job_ended_at IS NOT NULL AND lj.last_job_started_at IS NOT NULL
        THEN EXTRACT(EPOCH FROM (lj.last_job_ended_at - lj.last_job_started_at))::INTEGER
        ELSE NULL
    END AS last_job_duration_seconds,
    lj.last_job_summary,
    lj.last_job_error,
    NOW() AS snapshot_timestamp
FROM person_counts pc
CROSS JOIN satisfactory_scout ss
CROSS JOIN missing_scout ms
CROSS JOIN conflicts_count cc
CROSS JOIN backlog_a ba
CROSS JOIN backlog_d bd
CROSS JOIN backlog_c bc
CROSS JOIN last_job lj;

COMMENT ON VIEW ops.v_scout_attribution_metrics_snapshot IS 
'Métricas instantáneas de atribución scout para UI en tiempo real. Incluye: total persons, satisfactory %, missing, conflicts, backlog por categorías (A/C/D), estado del último job.';

-- ============================================================================
-- 2. VISTA: ops.v_scout_attribution_metrics_daily
-- ============================================================================
-- Métricas diarias históricas para tendencias (últimos 30 días)
-- ============================================================================

DROP VIEW IF EXISTS ops.v_scout_attribution_metrics_daily CASCADE;

CREATE VIEW ops.v_scout_attribution_metrics_daily AS
WITH date_series AS (
    SELECT generate_series(
        CURRENT_DATE - INTERVAL '30 days',
        CURRENT_DATE,
        '1 day'::INTERVAL
    )::DATE AS metric_date
),
daily_metrics AS (
    SELECT 
        ds.metric_date,
        COUNT(DISTINCT ir.person_key) AS total_persons,
        COUNT(DISTINCT ll.person_key) FILTER (WHERE ll.attributed_scout_id IS NOT NULL) AS satisfactory_count,
        COUNT(DISTINCT ir.person_key) FILTER (
            WHERE NOT EXISTS (
                SELECT 1 FROM observational.lead_ledger ll2
                WHERE ll2.person_key = ir.person_key
                    AND ll2.attributed_scout_id IS NOT NULL
            )
        ) AS missing_count,
        -- Contar por fuente (aproximado por fecha de creación del link)
        COUNT(DISTINCT il.person_key) FILTER (
            WHERE il.source_table = 'module_ct_scouting_daily'
            AND DATE(il.linked_at) = ds.metric_date
        ) AS by_source_scouting_daily,
        COUNT(DISTINCT le.person_key) FILTER (
            WHERE le.source_table = 'module_ct_cabinet_leads'
            AND DATE(le.event_date) = ds.metric_date
            AND (le.scout_id IS NOT NULL OR le.payload_json->>'scout_id' IS NOT NULL)
        ) AS by_source_cabinet_leads,
        COUNT(DISTINCT ll.person_key) FILTER (
            WHERE ll.attributed_scout_id IS NOT NULL
            AND DATE(ll.updated_at) = ds.metric_date
        ) AS by_source_lead_ledger
    FROM date_series ds
    CROSS JOIN canon.identity_registry ir
    LEFT JOIN observational.lead_ledger ll ON ll.person_key = ir.person_key
    LEFT JOIN canon.identity_links il ON il.person_key = ir.person_key
    LEFT JOIN observational.lead_events le ON le.person_key = ir.person_key
    GROUP BY ds.metric_date
)
SELECT 
    metric_date,
    total_persons,
    satisfactory_count,
    CASE 
        WHEN total_persons > 0 
        THEN ROUND((satisfactory_count::NUMERIC / total_persons * 100), 2)
        ELSE 0
    END AS pct_satisfactory,
    missing_count,
    by_source_scouting_daily,
    by_source_cabinet_leads,
    by_source_lead_ledger,
    NOW() AS computed_at
FROM daily_metrics
ORDER BY metric_date DESC;

COMMENT ON VIEW ops.v_scout_attribution_metrics_daily IS 
'Métricas diarias históricas de atribución scout (últimos 30 días) para gráficos de tendencias en UI.';

