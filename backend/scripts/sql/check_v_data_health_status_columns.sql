-- Verificar columnas de v_data_health_status

SELECT 
    column_name,
    data_type
FROM information_schema.columns
WHERE table_schema = 'ops'
    AND table_name = 'v_data_health_status'
ORDER BY ordinal_position;



