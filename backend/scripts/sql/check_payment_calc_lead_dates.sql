-- Verificar lead_dates en v_payment_calculation (cabinet)

SELECT 
    MAX(lead_date) as max_lead_date,
    COUNT(DISTINCT driver_id) as total_drivers,
    COUNT(DISTINCT driver_id) FILTER (WHERE lead_date >= '2025-12-15') as drivers_since_dec15
FROM ops.v_payment_calculation
WHERE origin_tag = 'cabinet'
    AND driver_id IS NOT NULL
    AND lead_date IS NOT NULL;

