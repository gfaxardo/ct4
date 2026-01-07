-- Verificar si hay nuevos leads disponibles para procesar

-- 1. module_ct_scouting_daily - fechas recientes
SELECT 
    'module_ct_scouting_daily' as source,
    MAX(registration_date) as max_date,
    COUNT(*) FILTER (WHERE registration_date >= '2025-12-15') as rows_since_dec15,
    COUNT(*) FILTER (WHERE registration_date >= '2025-12-20') as rows_since_dec20,
    COUNT(*) FILTER (WHERE registration_date >= '2026-01-01') as rows_since_jan1
FROM public.module_ct_scouting_daily
WHERE registration_date IS NOT NULL;

-- 2. Verificar si estos leads ya están en lead_events
SELECT 
    'lead_events (scouting)' as source,
    MAX(event_date) as max_date,
    COUNT(*) FILTER (WHERE event_date >= '2025-12-15') as events_since_dec15,
    COUNT(*) FILTER (WHERE source_table = 'module_ct_scouting_daily' AND event_date >= '2025-12-15') as scouting_events_since_dec15
FROM observational.lead_events
WHERE source_table = 'module_ct_scouting_daily';

-- 3. Leads en scouting_daily que NO están en lead_events
SELECT 
    COUNT(*) as missing_events
FROM public.module_ct_scouting_daily s
WHERE s.registration_date >= '2025-12-15'
    AND NOT EXISTS (
        SELECT 1 
        FROM observational.lead_events le
        WHERE le.source_table = 'module_ct_scouting_daily'
            AND le.source_pk = s.id::text
    );

