-- Verificar los 11 pagos sin driver_id y si pueden matchear

-- 1. Ver los 11 pagos sin driver_id
SELECT 
    source_pk,
    pay_date,
    raw_driver_name,
    driver_name_normalized,
    milestone_value,
    match_rule,
    match_confidence
FROM ops.yango_payment_status_ledger
WHERE snapshot_at >= CURRENT_DATE
    AND driver_id IS NULL
ORDER BY pay_date DESC;

-- 2. Verificar si estos nombres pueden matchear con drivers
SELECT 
    l.source_pk,
    l.raw_driver_name,
    l.driver_name_normalized,
    COUNT(DISTINCT d.driver_id) as matching_drivers_count,
    STRING_AGG(DISTINCT d.full_name, ', ') as matching_driver_names
FROM ops.yango_payment_status_ledger l
LEFT JOIN public.drivers d 
    ON UPPER(TRIM(REGEXP_REPLACE(REGEXP_REPLACE(d.full_name, '[ÀÁÂÃÄÅÈÉÊËÌÍÎÏÒÓÔÕÖÙÚÛÜÑÇ]', '', 'g'), '[^A-Z0-9 ]', '', 'g'))) 
       = l.driver_name_normalized
WHERE l.snapshot_at >= CURRENT_DATE
    AND l.driver_id IS NULL
GROUP BY l.source_pk, l.raw_driver_name, l.driver_name_normalized
ORDER BY matching_drivers_count DESC;

-- 3. Verificar si la vista raw_current tiene driver_id para estos pagos
SELECT 
    l.source_pk,
    l.pay_date,
    l.driver_name_normalized,
    rc.driver_id as raw_current_driver_id,
    rc.person_key as raw_current_person_key,
    rc.match_rule as raw_current_match_rule
FROM ops.yango_payment_status_ledger l
LEFT JOIN ops.v_yango_payments_raw_current_aliases rc
    ON rc.source_pk::text = l.source_pk
    AND rc.milestone_value = l.milestone_value
WHERE l.snapshot_at >= CURRENT_DATE
    AND l.driver_id IS NULL
ORDER BY l.pay_date DESC;

