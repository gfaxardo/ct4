-- Queries SQL de Verificación para Matching S3 por Placa
-- Ejecutar después de correr populate-events para cabinet (2025-11-01 a 2025-12-23)

-- 1. Total events por source_table
SELECT 
    source_table, 
    COUNT(*) as total
FROM observational.lead_events
GROUP BY source_table
ORDER BY source_table;

-- 2. With person_key por source_table
SELECT 
    source_table, 
    COUNT(*) as total,
    COUNT(person_key) as with_person_key,
    COUNT(*) - COUNT(person_key) as without_person_key,
    ROUND(100.0 * COUNT(person_key) / COUNT(*), 2) as match_rate_percent
FROM observational.lead_events
GROUP BY source_table
ORDER BY source_table;

-- 3. Top 20 person_key con conteos por source
SELECT 
    person_key, 
    source_table,
    COUNT(*) as event_count
FROM observational.lead_events
WHERE person_key IS NOT NULL
GROUP BY person_key, source_table
ORDER BY event_count DESC
LIMIT 20;

-- 4. Cabinet events resueltos por plate
SELECT 
    COUNT(*) as resolved_by_plate
FROM observational.lead_events
WHERE source_table = 'module_ct_cabinet_leads'
  AND person_key IS NOT NULL
  AND payload_json->>'matched_by' = 'plate';

-- 5. Cabinet events ambiguos por plate
SELECT 
    COUNT(*) as ambiguous_by_plate
FROM observational.lead_events
WHERE source_table = 'module_ct_cabinet_leads'
  AND payload_json->'match_meta'->>'plate_match' = 'ambiguous';

-- QUERIES ADICIONALES PARA ANÁLISIS DETALLADO

-- 6. Breakdown de matched_by para cabinet
SELECT 
    payload_json->>'matched_by' as matched_by,
    COUNT(*) as count,
    COUNT(person_key) FILTER (WHERE person_key IS NOT NULL) as with_person_key,
    COUNT(*) FILTER (WHERE person_key IS NULL) as without_person_key
FROM observational.lead_events
WHERE source_table = 'module_ct_cabinet_leads'
GROUP BY payload_json->>'matched_by'
ORDER BY count DESC;

-- 7. Breakdown de plate_match para cabinet
SELECT 
    payload_json->'match_meta'->>'plate_match' as plate_match,
    COUNT(*) as count
FROM observational.lead_events
WHERE source_table = 'module_ct_cabinet_leads'
  AND payload_json->>'matched_by' = 'plate'
GROUP BY payload_json->'match_meta'->>'plate_match'
ORDER BY count DESC;

-- 8. Ejemplos de eventos con matching por placa (top 10)
SELECT 
    id,
    source_pk,
    person_key,
    event_date,
    payload_json->>'asset_plate_number' as plate_raw,
    payload_json->>'plate_norm' as plate_norm,
    payload_json->>'matched_by' as matched_by,
    payload_json->'match_meta' as match_meta
FROM observational.lead_events
WHERE source_table = 'module_ct_cabinet_leads'
  AND payload_json->>'matched_by' = 'plate'
ORDER BY event_date DESC
LIMIT 10;

-- 9. Ejemplos de eventos ambiguos por placa
SELECT 
    id,
    source_pk,
    person_key,
    event_date,
    payload_json->>'asset_plate_number' as plate_raw,
    payload_json->>'plate_norm' as plate_norm,
    payload_json->'match_meta'->>'candidates' as candidates_count
FROM observational.lead_events
WHERE source_table = 'module_ct_cabinet_leads'
  AND payload_json->'match_meta'->>'plate_match' = 'ambiguous'
ORDER BY event_date DESC
LIMIT 10;

-- 10. Comparación antes/después: eventos cabinet con y sin person_key
SELECT 
    CASE 
        WHEN person_key IS NOT NULL THEN 'Con person_key'
        ELSE 'Sin person_key'
    END as estado,
    COUNT(*) as total,
    COUNT(*) FILTER (WHERE payload_json->>'matched_by' = 'plate') as matched_by_plate,
    COUNT(*) FILTER (WHERE payload_json->>'matched_by' = 'license') as matched_by_license,
    COUNT(*) FILTER (WHERE payload_json->>'matched_by' = 'phone_last9') as matched_by_phone,
    COUNT(*) FILTER (WHERE payload_json->>'matched_by' = 'none') as matched_by_none
FROM observational.lead_events
WHERE source_table = 'module_ct_cabinet_leads'
GROUP BY 
    CASE 
        WHEN person_key IS NOT NULL THEN 'Con person_key'
        ELSE 'Sin person_key'
    END;








