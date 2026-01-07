-- Verificar y corregir vistas de health

-- 1. Verificar si v_data_health_status tiene source_type
SELECT 
    column_name,
    data_type
FROM information_schema.columns
WHERE table_schema = 'ops'
    AND table_name = 'v_data_health_status'
ORDER BY ordinal_position;

-- 2. Verificar si v_data_sources_catalog tiene source_type
SELECT 
    column_name,
    data_type
FROM information_schema.columns
WHERE table_schema = 'ops'
    AND table_name = 'v_data_sources_catalog'
ORDER BY ordinal_position;

