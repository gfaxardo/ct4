-- Verificar qué tablas existen relacionadas con cabinet

-- 1. Verificar v_conversion_metrics (cabinet) - fecha máxima
SELECT 
    'v_conversion_metrics (cabinet)' as source,
    MAX(lead_date) as max_lead_date,
    COUNT(DISTINCT driver_id) as total_drivers,
    COUNT(DISTINCT driver_id) FILTER (WHERE lead_date >= '2025-12-15') as drivers_since_dec15
FROM observational.v_conversion_metrics
WHERE origin_tag = 'cabinet'
    AND driver_id IS NOT NULL
    AND lead_date IS NOT NULL;

-- 2. Verificar tablas que podrían tener leads de cabinet
SELECT 
    table_schema,
    table_name
FROM information_schema.tables
WHERE table_schema = 'public'
    AND (table_name LIKE '%cabinet%' OR table_name LIKE '%lead%')
ORDER BY table_name;


