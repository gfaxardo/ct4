-- Verificación simple de fechas en v_cabinet_financial_14d

SELECT 
    MAX(lead_date) as max_lead_date,
    COUNT(*) as total_drivers
FROM ops.v_cabinet_financial_14d;

