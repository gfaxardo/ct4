-- Verificaciones simples de fechas

-- 1. Fecha máxima en v_cabinet_financial_14d
SELECT 
    MAX(lead_date) as max_lead_date,
    COUNT(*) as total_drivers
FROM ops.v_cabinet_financial_14d;

-- 2. Fecha máxima en v_conversion_metrics (cabinet)
SELECT 
    MAX(lead_date) as max_lead_date,
    COUNT(*) as total_drivers
FROM observational.v_conversion_metrics
WHERE origin_tag = 'cabinet'
    AND driver_id IS NOT NULL
    AND lead_date IS NOT NULL;

-- 3. Pagos con identidad desde el 15/12
SELECT 
    COUNT(*) as payments_count,
    MAX(pay_date) as max_pay_date,
    COUNT(DISTINCT driver_id) FILTER (WHERE driver_id IS NOT NULL) as drivers_with_id,
    COUNT(DISTINCT person_key) FILTER (WHERE person_key IS NOT NULL) as persons_with_key
FROM ops.yango_payment_status_ledger
WHERE pay_date >= '2025-12-15'
    AND (driver_id IS NOT NULL OR person_key IS NOT NULL);


