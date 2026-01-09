-- Diagnóstico de rendimiento y datos faltantes en v_cabinet_financial_14d

-- 1. Verificar fecha máxima en v_cabinet_financial_14d
SELECT 
    MAX(lead_date) as max_lead_date,
    COUNT(*) as total_drivers,
    COUNT(*) FILTER (WHERE lead_date >= '2025-12-15') as drivers_since_dec15
FROM ops.v_cabinet_financial_14d;

-- 2. Verificar fecha máxima en v_conversion_metrics (cabinet)
SELECT 
    MAX(lead_date) as max_lead_date,
    COUNT(DISTINCT driver_id) as total_drivers
FROM observational.v_conversion_metrics
WHERE origin_tag = 'cabinet'
    AND driver_id IS NOT NULL
    AND lead_date IS NOT NULL;

-- 3. Verificar fecha máxima en v_claims_payment_status_cabinet
SELECT 
    MAX(lead_date) as max_lead_date,
    COUNT(DISTINCT driver_id) as total_drivers,
    COUNT(DISTINCT driver_id) FILTER (WHERE lead_date >= '2025-12-15') as drivers_since_dec15
FROM ops.v_claims_payment_status_cabinet
WHERE driver_id IS NOT NULL
    AND lead_date IS NOT NULL;

-- 4. Verificar pagos recientes en ledger con driver_id
SELECT 
    MAX(pay_date) as max_pay_date,
    COUNT(*) as total_payments,
    COUNT(DISTINCT driver_id) FILTER (WHERE driver_id IS NOT NULL) as payments_with_driver_id,
    COUNT(DISTINCT person_key) FILTER (WHERE person_key IS NOT NULL) as payments_with_person_key
FROM ops.yango_payment_status_ledger
WHERE pay_date >= '2025-12-15';



