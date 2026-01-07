-- Verificar pagos con identidad que no aparecen en v_cabinet_financial_14d

-- 1. Pagos con driver_id que NO tienen lead_date en v_conversion_metrics
SELECT 
    COUNT(*) as payments_without_lead_date,
    COUNT(DISTINCT l.driver_id) as unique_drivers,
    MIN(l.pay_date) as min_pay_date,
    MAX(l.pay_date) as max_pay_date
FROM ops.yango_payment_status_ledger l
WHERE l.driver_id IS NOT NULL
    AND l.pay_date >= '2025-12-15'
    AND NOT EXISTS (
        SELECT 1 
        FROM observational.v_conversion_metrics vcm
        WHERE vcm.driver_id = l.driver_id
            AND vcm.origin_tag = 'cabinet'
            AND vcm.lead_date IS NOT NULL
    );

-- 2. Pagos con person_key que NO tienen lead_date en v_conversion_metrics
SELECT 
    COUNT(*) as payments_without_lead_date,
    COUNT(DISTINCT l.person_key) as unique_persons,
    MIN(l.pay_date) as min_pay_date,
    MAX(l.pay_date) as max_pay_date
FROM ops.yango_payment_status_ledger l
WHERE l.person_key IS NOT NULL
    AND l.driver_id IS NULL
    AND l.pay_date >= '2025-12-15'
    AND NOT EXISTS (
        SELECT 1 
        FROM observational.v_conversion_metrics vcm
        WHERE vcm.person_key = l.person_key
            AND vcm.origin_tag = 'cabinet'
            AND vcm.lead_date IS NOT NULL
    );

-- 3. Verificar si estos pagos tienen driver_id pero no están en v_conversion_metrics
-- (pueden ser drivers que entraron por otro origen o que no tienen lead_date)
SELECT 
    l.driver_id,
    l.person_key,
    l.pay_date,
    l.milestone_value,
    l.raw_driver_name,
    CASE 
        WHEN EXISTS (SELECT 1 FROM observational.v_conversion_metrics vcm WHERE vcm.driver_id = l.driver_id AND vcm.origin_tag = 'cabinet') THEN 'tiene_conversion_metrics'
        WHEN EXISTS (SELECT 1 FROM observational.v_conversion_metrics vcm WHERE vcm.driver_id = l.driver_id) THEN 'tiene_conversion_metrics_otro_origen'
        ELSE 'sin_conversion_metrics'
    END as conversion_status
FROM ops.yango_payment_status_ledger l
WHERE (l.driver_id IS NOT NULL OR l.person_key IS NOT NULL)
    AND l.pay_date >= '2025-12-15'
ORDER BY l.pay_date DESC
LIMIT 20;


