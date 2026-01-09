-- Verificar estructura de v_data_health_status

-- Verificar columnas de v_data_health_status
SELECT 
    column_name,
    data_type
FROM information_schema.columns
WHERE table_schema = 'ops'
    AND table_name = 'v_data_health_status'
ORDER BY ordinal_position;

-- Verificar si el JOIN funciona correctamente
SELECT 
    f.source_name,
    c.source_type,
    f.health_status
FROM ops.v_data_freshness_status f
LEFT JOIN ops.v_data_sources_catalog c ON f.source_name = c.source_name
LIMIT 5;



