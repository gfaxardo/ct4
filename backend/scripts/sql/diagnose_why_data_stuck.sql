-- Diagnóstico completo: ¿Por qué los datos siguen hasta el 14/12?

-- 1. Verificar fecha máxima en lead_events
SELECT 
    'lead_events' as source,
    MAX(event_date) as max_date,
    COUNT(*) as total_events,
    COUNT(*) FILTER (WHERE event_date >= '2025-12-15') as events_since_dec15
FROM observational.lead_events;

-- 2. Verificar si hay nuevos leads en tablas fuente (module_ct_scouting_daily)
SELECT 
    'module_ct_scouting_daily' as source,
    MAX(registration_date) as max_date,
    COUNT(*) as total_rows,
    COUNT(*) FILTER (WHERE registration_date >= '2025-12-15') as rows_since_dec15
FROM public.module_ct_scouting_daily
WHERE registration_date IS NOT NULL;

-- 3. Verificar última corrida de ingesta y su resultado
SELECT 
    id,
    status,
    scope_date_from,
    scope_date_to,
    completed_at,
    started_at,
    error_message,
    stats
FROM ops.ingestion_runs
ORDER BY started_at DESC
LIMIT 3;

-- 4. Verificar fecha máxima en v_conversion_metrics
SELECT 
    'v_conversion_metrics (cabinet)' as source,
    MAX(lead_date) as max_date,
    COUNT(DISTINCT driver_id) as total_drivers
FROM observational.v_conversion_metrics
WHERE origin_tag = 'cabinet'
    AND driver_id IS NOT NULL
    AND lead_date IS NOT NULL;

-- 5. Verificar fecha máxima en v_cabinet_financial_14d
SELECT 
    'v_cabinet_financial_14d' as source,
    MAX(lead_date) as max_date,
    COUNT(*) as total_drivers
FROM ops.v_cabinet_financial_14d;


