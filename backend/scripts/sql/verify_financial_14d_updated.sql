-- Verificar si v_cabinet_financial_14d ahora incluye más drivers

-- 1. Fecha máxima en v_cabinet_financial_14d
SELECT 
    MAX(lead_date) as max_lead_date,
    MIN(lead_date) as min_lead_date,
    COUNT(*) as total_drivers,
    COUNT(*) FILTER (WHERE lead_date >= '2025-12-15') as drivers_since_dec15
FROM ops.v_cabinet_financial_14d;

-- 2. Verificar drivers con pagos que tienen driver_id o person_key
SELECT 
    COUNT(DISTINCT driver_id) FILTER (WHERE driver_id IS NOT NULL) as drivers_with_id,
    COUNT(DISTINCT person_key) FILTER (WHERE person_key IS NOT NULL) as persons_with_key,
    MAX(pay_date) as max_pay_date
FROM ops.yango_payment_status_ledger
WHERE (driver_id IS NOT NULL OR person_key IS NOT NULL)
    AND pay_date >= '2025-12-15';

-- 3. Verificar si estos drivers aparecen en v_claims_payment_status_cabinet
SELECT 
    COUNT(DISTINCT driver_id) as drivers_in_claims,
    MAX(lead_date) as max_lead_date_in_claims
FROM ops.v_claims_payment_status_cabinet
WHERE driver_id IS NOT NULL
    AND lead_date >= '2025-12-15';

