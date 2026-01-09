-- Verificar que el fix de origin_tag funcionó

-- 1. Verificar eventos actualizados
SELECT 
    COUNT(*) as events_with_cabinet_tag,
    MAX(event_date) as max_event_date
FROM observational.lead_events
WHERE source_table = 'module_ct_scouting_daily'
    AND payload_json->>'origin_tag' = 'cabinet'
    AND event_date >= '2025-12-15';

-- 2. Verificar v_conversion_metrics (cabinet) después del fix
SELECT 
    MAX(lead_date) as max_lead_date,
    COUNT(DISTINCT driver_id) as total_drivers,
    COUNT(DISTINCT driver_id) FILTER (WHERE lead_date >= '2025-12-15') as drivers_since_dec15
FROM observational.v_conversion_metrics
WHERE origin_tag = 'cabinet'
    AND driver_id IS NOT NULL
    AND lead_date IS NOT NULL;

-- 3. Verificar v_cabinet_financial_14d
SELECT 
    MAX(lead_date) as max_lead_date,
    COUNT(*) as total_drivers,
    COUNT(*) FILTER (WHERE lead_date >= '2025-12-15') as drivers_since_dec15
FROM ops.v_cabinet_financial_14d;



