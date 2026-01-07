-- Verificaciones simples sin usar v_cabinet_financial_14d

-- 1. Fecha máxima en v_conversion_metrics (cabinet) - SIMPLE
SELECT 
    MAX(lead_date) as max_lead_date_cm,
    COUNT(DISTINCT driver_id) as total_drivers_cm
FROM observational.v_conversion_metrics
WHERE origin_tag = 'cabinet'
    AND driver_id IS NOT NULL
    AND lead_date IS NOT NULL;

-- 2. Fecha máxima en v_claims_payment_status_cabinet - SIMPLE
SELECT 
    MAX(lead_date) as max_lead_date_claims,
    COUNT(DISTINCT driver_id) as total_drivers_claims
FROM ops.v_claims_payment_status_cabinet
WHERE driver_id IS NOT NULL
    AND lead_date IS NOT NULL;

-- 3. Pagos recientes en ledger
SELECT 
    MAX(pay_date) as max_pay_date,
    COUNT(*) FILTER (WHERE pay_date >= '2025-12-15') as payments_since_dec15,
    COUNT(DISTINCT driver_id) FILTER (WHERE driver_id IS NOT NULL AND pay_date >= '2025-12-15') as drivers_with_payments
FROM ops.yango_payment_status_ledger;


