-- Verificación de ordenamiento y datos de ejemplo
-- Verificar que lead_date DESC funciona correctamente

-- 1. Verificar ordenamiento: las 3 fechas más recientes
SELECT 
    lead_date,
    iso_week,
    COUNT(*) as drivers_count
FROM ops.mv_cabinet_financial_14d
WHERE lead_date IS NOT NULL
GROUP BY lead_date, iso_week
ORDER BY lead_date DESC
LIMIT 5;

-- 2. Ejemplos de drivers con nombres y semanas ISO
SELECT 
    driver_id,
    driver_name,
    lead_date,
    iso_week,
    total_trips_14d,
    CASE 
        WHEN reached_m25_14d THEN 'M25'
        WHEN reached_m5_14d THEN 'M5'
        WHEN reached_m1_14d THEN 'M1'
        ELSE 'Ninguno'
    END as highest_milestone,
    amount_due_yango
FROM ops.mv_cabinet_financial_14d
WHERE lead_date IS NOT NULL
    AND driver_name IS NOT NULL 
    AND driver_name != 'N/A'
ORDER BY lead_date DESC NULLS LAST
LIMIT 10;




