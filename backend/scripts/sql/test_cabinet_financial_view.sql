-- Prueba rápida de la vista v_cabinet_financial_14d con nuevos campos
-- Verificar que driver_name e iso_week están presentes y el ordenamiento funciona

-- Muestra de 10 filas ordenadas por lead_date DESC (más reciente primero)
SELECT 
    driver_id,
    driver_name,
    lead_date,
    iso_week,
    total_trips_14d,
    reached_m1_14d,
    reached_m5_14d,
    reached_m25_14d,
    expected_total_yango,
    amount_due_yango
FROM ops.v_cabinet_financial_14d
WHERE lead_date IS NOT NULL
ORDER BY lead_date DESC NULLS LAST
LIMIT 10;



