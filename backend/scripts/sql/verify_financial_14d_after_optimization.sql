-- Verificar si v_cabinet_financial_14d ahora muestra datos más recientes

SELECT 
    MAX(lead_date) as max_lead_date,
    COUNT(*) as total_drivers,
    COUNT(*) FILTER (WHERE lead_date >= '2025-12-15') as drivers_since_dec15,
    COUNT(*) FILTER (WHERE lead_date >= '2025-12-20') as drivers_since_dec20
FROM ops.v_cabinet_financial_14d;

