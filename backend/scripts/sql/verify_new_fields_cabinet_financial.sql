-- Verificación de nuevos campos en v_cabinet_financial_14d
-- driver_name e iso_week

-- 1. Verificar que los campos existen
SELECT 
    column_name, 
    data_type
FROM information_schema.columns
WHERE table_schema = 'ops'
AND table_name = 'v_cabinet_financial_14d'
AND column_name IN ('driver_name', 'iso_week')
ORDER BY column_name;

-- 2. Muestra de datos (5 filas, ordenadas por lead_date DESC)
SELECT 
    driver_id,
    driver_name,
    lead_date,
    iso_week,
    total_trips_14d,
    amount_due_yango
FROM ops.v_cabinet_financial_14d
WHERE lead_date IS NOT NULL
ORDER BY lead_date DESC NULLS LAST
LIMIT 5;

-- 3. Verificar ordenamiento (fechas más recientes primero)
SELECT 
    lead_date,
    COUNT(*) as count
FROM ops.v_cabinet_financial_14d
WHERE lead_date IS NOT NULL
GROUP BY lead_date
ORDER BY lead_date DESC
LIMIT 3;


