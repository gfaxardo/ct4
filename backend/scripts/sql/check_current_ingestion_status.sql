-- Verificar estado actual de ingesta y lead_events

-- 1. Última corrida de ingesta
SELECT 
    id,
    status,
    scope_date_from,
    scope_date_to,
    completed_at,
    started_at,
    EXTRACT(EPOCH FROM (NOW() - completed_at))/3600 as hours_since_completion
FROM ops.ingestion_runs
WHERE status = 'COMPLETED'
ORDER BY completed_at DESC
LIMIT 5;

-- 2. Fecha máxima en lead_events
SELECT 
    MAX(event_date) as max_event_date,
    COUNT(*) as total_events,
    COUNT(*) FILTER (WHERE event_date >= '2025-12-15') as events_since_dec15,
    COUNT(*) FILTER (WHERE created_at >= NOW() - INTERVAL '7 days') as events_last_7_days
FROM observational.lead_events;

-- 3. Fecha máxima en v_conversion_metrics (cabinet)
SELECT 
    MAX(lead_date) as max_lead_date,
    COUNT(DISTINCT driver_id) as total_drivers
FROM observational.v_conversion_metrics
WHERE origin_tag = 'cabinet'
    AND driver_id IS NOT NULL
    AND lead_date IS NOT NULL;

