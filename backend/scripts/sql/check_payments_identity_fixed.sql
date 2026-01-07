-- Verificar si los pagos insertados tienen identidad asignada

-- 1. Pagos insertados hoy (los 108) - verificar si tienen driver_id/person_key
SELECT 
    COUNT(*) as total_inserted_today,
    COUNT(*) FILTER (WHERE driver_id IS NOT NULL) as with_driver_id,
    COUNT(*) FILTER (WHERE person_key IS NOT NULL) as with_person_key,
    COUNT(*) FILTER (WHERE driver_id IS NULL AND person_key IS NULL) as without_identity,
    MIN(pay_date) as min_pay_date,
    MAX(pay_date) as max_pay_date
FROM ops.yango_payment_status_ledger
WHERE snapshot_at >= CURRENT_DATE;

-- 2. Ver algunos ejemplos de pagos sin identidad
SELECT 
    source_pk,
    pay_date,
    raw_driver_name,
    driver_name_normalized,
    milestone_value,
    driver_id,
    person_key,
    match_rule,
    match_confidence
FROM ops.yango_payment_status_ledger
WHERE snapshot_at >= CURRENT_DATE
    AND driver_id IS NULL
    AND person_key IS NULL
ORDER BY pay_date DESC
LIMIT 10;

-- 3. Verificar si estos pagos aparecen en la vista enriquecida
SELECT 
    COUNT(*) as in_enriched_view,
    COUNT(*) FILTER (WHERE driver_id_final IS NOT NULL) as with_driver_id_final,
    COUNT(*) FILTER (WHERE person_key_final IS NOT NULL) as with_person_key_final
FROM ops.v_yango_payments_ledger_latest_enriched
WHERE pay_date >= '2025-12-18';

-- 4. Verificar si estos pagos están siendo usados en v_claims_payment_status_cabinet
SELECT 
    COUNT(*) as in_claims_view,
    COUNT(*) FILTER (WHERE driver_id IS NOT NULL) as with_driver_id
FROM ops.v_claims_payment_status_cabinet
WHERE pay_date >= '2025-12-18';

-- 5. Comparar pagos en el ledger vs pagos en la vista de claims
SELECT 
    'Ledger (últimos 30 días)' AS source,
    COUNT(*) as total_payments,
    COUNT(*) FILTER (WHERE driver_id IS NOT NULL) as with_driver_id,
    SUM(CASE WHEN milestone_value = 1 THEN 1 ELSE 0 END) as m1_count,
    SUM(CASE WHEN milestone_value = 5 THEN 1 ELSE 0 END) as m5_count,
    SUM(CASE WHEN milestone_value = 25 THEN 1 ELSE 0 END) as m25_count
FROM ops.yango_payment_status_ledger
WHERE pay_date >= CURRENT_DATE - INTERVAL '30 days';

SELECT 
    'Claims view (últimos 30 días)' AS source,
    COUNT(*) as total_payments,
    COUNT(*) FILTER (WHERE driver_id IS NOT NULL) as with_driver_id,
    SUM(CASE WHEN milestone_value = 1 THEN 1 ELSE 0 END) as m1_count,
    SUM(CASE WHEN milestone_value = 5 THEN 1 ELSE 0 END) as m5_count,
    SUM(CASE WHEN milestone_value = 25 THEN 1 ELSE 0 END) as m25_count
FROM ops.v_claims_payment_status_cabinet
WHERE pay_date >= CURRENT_DATE - INTERVAL '30 days';


