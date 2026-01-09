-- Verificación final del sistema completo

-- 1. Health check: lead_events e ingestion_runs
SELECT 
    source_name,
    health_status,
    max_business_date,
    business_days_lag,
    CASE 
        WHEN max_ingestion_ts IS NOT NULL 
        THEN EXTRACT(EPOCH FROM (NOW() - max_ingestion_ts))/3600 
        ELSE NULL 
    END as hours_since_last_update
FROM ops.v_data_health_status
WHERE source_name IN ('lead_events', 'ingestion_runs')
ORDER BY source_name;

-- 2. Última corrida de ingesta
SELECT 
    id,
    status,
    scope_date_from,
    scope_date_to,
    completed_at,
    CASE 
        WHEN completed_at IS NOT NULL 
        THEN EXTRACT(EPOCH FROM (NOW() - completed_at))/3600 
        ELSE NULL 
    END as hours_since_completion
FROM ops.ingestion_runs
WHERE status = 'COMPLETED'
ORDER BY completed_at DESC
LIMIT 1;

-- 3. Fecha máxima en lead_events
SELECT 
    MAX(event_date) as max_event_date,
    COUNT(*) as total_events,
    COUNT(*) FILTER (WHERE event_date >= CURRENT_DATE - INTERVAL '7 days') as events_last_7_days,
    COUNT(*) FILTER (WHERE created_at >= NOW() - INTERVAL '24 hours') as events_last_24h
FROM observational.lead_events;

-- 4. Fecha máxima en v_cabinet_financial_14d
SELECT 
    MAX(lead_date) as max_lead_date,
    COUNT(*) as total_drivers,
    COUNT(*) FILTER (WHERE lead_date >= CURRENT_DATE - INTERVAL '7 days') as drivers_last_7_days
FROM ops.v_cabinet_financial_14d;



