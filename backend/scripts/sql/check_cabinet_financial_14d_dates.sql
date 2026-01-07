-- Verificar fechas en v_cabinet_financial_14d y pagos disponibles

-- 1. Fecha máxima en v_cabinet_financial_14d
SELECT 
    'v_cabinet_financial_14d' AS source,
    MAX(lead_date) as max_lead_date,
    MIN(lead_date) as min_lead_date,
    COUNT(*) as total_drivers
FROM ops.v_cabinet_financial_14d;

-- 2. Fecha máxima en pagos del ledger (con driver_id o person_key)
SELECT 
    'yango_payment_status_ledger (con identidad)' AS source,
    MAX(pay_date) as max_pay_date,
    MIN(pay_date) as min_pay_date,
    COUNT(*) as total_payments,
    COUNT(DISTINCT driver_id) FILTER (WHERE driver_id IS NOT NULL) as unique_drivers_with_id,
    COUNT(DISTINCT person_key) FILTER (WHERE person_key IS NOT NULL) as unique_persons_with_key
FROM ops.yango_payment_status_ledger
WHERE (driver_id IS NOT NULL OR person_key IS NOT NULL)
    AND pay_date >= '2025-12-01';

-- 3. Pagos desde el 15/12/2025 en adelante que tienen identidad
SELECT 
    COUNT(*) as payments_since_dec15,
    COUNT(DISTINCT driver_id) FILTER (WHERE driver_id IS NOT NULL) as unique_drivers,
    COUNT(DISTINCT person_key) FILTER (WHERE person_key IS NOT NULL) as unique_persons,
    MIN(pay_date) as min_pay_date,
    MAX(pay_date) as max_pay_date
FROM ops.yango_payment_status_ledger
WHERE pay_date >= '2025-12-15'
    AND (driver_id IS NOT NULL OR person_key IS NOT NULL);

-- 4. Verificar si estos pagos aparecen en v_claims_payment_status_cabinet
SELECT 
    'v_claims_payment_status_cabinet' AS source,
    MAX(lead_date) as max_lead_date,
    MIN(lead_date) as min_lead_date,
    COUNT(*) as total_claims,
    COUNT(*) FILTER (WHERE paid_flag = true) as paid_claims
FROM ops.v_claims_payment_status_cabinet
WHERE lead_date >= '2025-12-01';

-- 5. Verificar pagos que deberían aparecer pero no están en claims
SELECT 
    l.driver_id,
    l.person_key,
    l.pay_date,
    l.milestone_value,
    l.raw_driver_name
FROM ops.yango_payment_status_ledger l
WHERE l.pay_date >= '2025-12-15'
    AND (l.driver_id IS NOT NULL OR l.person_key IS NOT NULL)
    AND NOT EXISTS (
        SELECT 1 
        FROM ops.v_claims_payment_status_cabinet c
        WHERE (c.driver_id = l.driver_id OR c.person_key = l.person_key)
            AND c.milestone_value = l.milestone_value
    )
ORDER BY l.pay_date DESC
LIMIT 20;

-- 6. Verificar lead_date máxima en v_conversion_metrics (cabinet)
SELECT 
    'v_conversion_metrics (cabinet)' AS source,
    MAX(lead_date) as max_lead_date,
    MIN(lead_date) as min_lead_date,
    COUNT(*) as total_drivers
FROM observational.v_conversion_metrics
WHERE origin_tag = 'cabinet'
    AND driver_id IS NOT NULL
    AND lead_date IS NOT NULL;

