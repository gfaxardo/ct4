-- Encontrar leads en scouting_daily que NO están en lead_events después del 14/12

-- 1. Leads en scouting_daily después del 14/12
SELECT 
    'scouting_daily (después 14/12)' as source,
    COUNT(*) as total_leads,
    MIN(registration_date) as min_date,
    MAX(registration_date) as max_date
FROM public.module_ct_scouting_daily
WHERE registration_date >= '2025-12-15'
    AND registration_date IS NOT NULL;

-- 2. Leads que NO están en lead_events
SELECT 
    s.id,
    s.registration_date,
    s.driver_phone,
    s.driver_name,
    s.created_at
FROM public.module_ct_scouting_daily s
WHERE s.registration_date >= '2025-12-15'
    AND s.registration_date IS NOT NULL
    AND NOT EXISTS (
        SELECT 1 
        FROM observational.lead_events le
        WHERE le.source_table = 'module_ct_scouting_daily'
            AND le.source_pk = s.id::text
    )
ORDER BY s.registration_date DESC
LIMIT 20;

-- 3. Verificar eventos con person_key NULL (no aparecen en v_conversion_metrics)
SELECT 
    COUNT(*) as events_without_person_key,
    MAX(event_date) as max_event_date
FROM observational.lead_events
WHERE person_key IS NULL
    AND event_date >= '2025-12-15';



