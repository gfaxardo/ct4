-- Test simple de v_data_health_status

SELECT 
    source_name,
    source_type,
    health_status
FROM ops.v_data_health_status
LIMIT 5;


