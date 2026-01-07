-- Corregir origin_tag en eventos existentes de scouting_daily
-- IMPORTANTE: Todos los eventos de scouting_daily deben tener origin_tag='cabinet'
-- porque v_conversion_metrics filtra por origin_tag='cabinet' para cabinet

-- Actualizar eventos de scouting_daily para que tengan origin_tag='cabinet' en payload_json
UPDATE observational.lead_events
SET 
    payload_json = jsonb_set(
        COALESCE(payload_json, '{}'::jsonb),
        '{origin_tag}',
        '"cabinet"'
    ),
    created_at = created_at  -- Mantener created_at original
WHERE source_table = 'module_ct_scouting_daily'
    AND (
        payload_json->>'origin_tag' = 'scouting' 
        OR payload_json->>'origin_tag' IS NULL
    );

-- Verificar cuántos se actualizaron
SELECT 
    'Eventos actualizados' AS status,
    COUNT(*) AS events_updated
FROM observational.lead_events
WHERE source_table = 'module_ct_scouting_daily'
    AND payload_json->>'origin_tag' = 'cabinet';

-- Verificar distribución por fecha
SELECT 
    'Distribución por fecha' AS status,
    event_date,
    COUNT(*) AS total,
    COUNT(*) FILTER (WHERE payload_json->>'origin_tag' = 'cabinet') AS cabinet_count
FROM observational.lead_events
WHERE source_table = 'module_ct_scouting_daily'
GROUP BY event_date
ORDER BY event_date DESC
LIMIT 20;

