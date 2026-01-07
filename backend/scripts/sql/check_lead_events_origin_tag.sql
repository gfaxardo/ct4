-- Verificar origin_tag en lead_events

-- 1. Eventos de scouting_daily y su origin_tag
SELECT 
    source_table,
    COUNT(*) as total_events,
    COUNT(*) FILTER (WHERE payload_json->>'origin_tag' = 'cabinet') as with_cabinet_tag,
    COUNT(*) FILTER (WHERE payload_json->>'origin_tag' = 'scouting') as with_scouting_tag,
    COUNT(*) FILTER (WHERE payload_json->>'origin_tag' IS NULL) as with_null_tag,
    MAX(event_date) as max_event_date
FROM observational.lead_events
WHERE source_table = 'module_ct_scouting_daily'
    AND event_date >= '2025-12-15'
GROUP BY source_table;

-- 2. Verificar cómo v_conversion_metrics interpreta estos eventos
SELECT 
    le.source_table,
    le.payload_json->>'origin_tag' as payload_origin_tag,
    CASE 
        WHEN le.source_table = 'module_ct_scouting_daily' THEN 'cabinet'
        ELSE 'unknown'
    END as computed_origin_tag,
    COUNT(*) as count
FROM observational.lead_events le
WHERE le.source_table = 'module_ct_scouting_daily'
    AND le.event_date >= '2025-12-15'
    AND le.person_key IS NOT NULL
GROUP BY le.source_table, le.payload_json->>'origin_tag'
ORDER BY count DESC;

-- 3. Verificar si estos eventos aparecen en v_conversion_metrics
SELECT 
    cm.origin_tag,
    COUNT(DISTINCT cm.person_key) as total_persons,
    MAX(cm.lead_date) as max_lead_date
FROM observational.v_conversion_metrics cm
WHERE cm.person_key IN (
    SELECT DISTINCT person_key 
    FROM observational.lead_events 
    WHERE source_table = 'module_ct_scouting_daily'
        AND event_date >= '2025-12-15'
        AND person_key IS NOT NULL
)
GROUP BY cm.origin_tag;


