-- Verificar estructura de lead_events

-- 1. Verificar si es tabla o vista
SELECT 
    table_type,
    table_name
FROM information_schema.tables
WHERE table_schema = 'observational'
    AND table_name = 'lead_events';

-- 2. Verificar columnas
SELECT 
    column_name,
    data_type,
    is_nullable
FROM information_schema.columns
WHERE table_schema = 'observational'
    AND table_name = 'lead_events'
ORDER BY ordinal_position;

-- 3. Verificar fecha máxima y conteo
SELECT 
    MAX(event_date) as max_event_date,
    COUNT(*) as total_events,
    COUNT(*) FILTER (WHERE event_date >= '2025-12-15') as events_since_dec15,
    COUNT(DISTINCT person_key) as total_persons,
    COUNT(DISTINCT source_table) as total_source_tables
FROM observational.lead_events;


