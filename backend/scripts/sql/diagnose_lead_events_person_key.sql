-- Diagnóstico: eventos con person_key NULL

-- 1. Eventos con person_key NULL después del 14/12
SELECT 
    COUNT(*) as events_without_person_key,
    MAX(event_date) as max_event_date,
    MIN(event_date) as min_event_date
FROM observational.lead_events
WHERE person_key IS NULL
    AND event_date >= '2025-12-15';

-- 2. Eventos con person_key después del 14/12
SELECT 
    COUNT(*) as events_with_person_key,
    MAX(event_date) as max_event_date,
    MIN(event_date) as min_event_date
FROM observational.lead_events
WHERE person_key IS NOT NULL
    AND event_date >= '2025-12-15';

-- 3. Verificar si v_conversion_metrics tiene estos person_keys
SELECT 
    COUNT(DISTINCT le.person_key) as person_keys_in_lead_events,
    COUNT(DISTINCT cm.person_key) as person_keys_in_conversion_metrics
FROM observational.lead_events le
LEFT JOIN observational.v_conversion_metrics cm ON cm.person_key = le.person_key
WHERE le.person_key IS NOT NULL
    AND le.event_date >= '2025-12-15';

-- 4. Verificar si hay identity_links para estos person_keys
SELECT 
    COUNT(DISTINCT le.person_key) as person_keys_in_lead_events,
    COUNT(DISTINCT il.person_key) as person_keys_with_identity_links,
    COUNT(DISTINCT il.person_key) FILTER (
        WHERE il.source_table = 'drivers'
    ) as person_keys_with_driver_links
FROM observational.lead_events le
LEFT JOIN canon.identity_links il ON il.person_key = le.person_key
WHERE le.person_key IS NOT NULL
    AND le.event_date >= '2025-12-15';

