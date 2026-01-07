-- Prueba de la vista materializada mv_cabinet_financial_14d
-- Verificar que incluye los nuevos campos

-- Conteo total
SELECT COUNT(*) as total_drivers FROM ops.mv_cabinet_financial_14d;

-- Muestra de 5 filas con los nuevos campos
SELECT 
    driver_id,
    driver_name,
    lead_date,
    iso_week,
    total_trips_14d,
    expected_total_yango,
    amount_due_yango
FROM ops.mv_cabinet_financial_14d
WHERE lead_date IS NOT NULL
ORDER BY lead_date DESC NULLS LAST
LIMIT 5;

-- Verificar que hay drivers con nombres
SELECT 
    COUNT(*) as drivers_with_name,
    COUNT(*) FILTER (WHERE driver_name IS NOT NULL AND driver_name != 'N/A') as drivers_with_real_name
FROM ops.mv_cabinet_financial_14d;



