-- Diagnóstico del gap de identidad en pagos

-- 1. Verificar cuántos pagos insertados hoy tienen driver_id
SELECT 
    'Pagos insertados hoy' AS check_type,
    COUNT(*) as total,
    COUNT(*) FILTER (WHERE driver_id IS NOT NULL) as with_driver_id,
    COUNT(*) FILTER (WHERE person_key IS NOT NULL) as with_person_key,
    COUNT(*) FILTER (WHERE driver_id IS NULL AND person_key IS NULL) as without_identity
FROM ops.yango_payment_status_ledger
WHERE snapshot_at >= CURRENT_DATE;

-- 2. Ver ejemplos de pagos sin identidad
SELECT 
    source_pk,
    pay_date,
    raw_driver_name,
    driver_name_normalized,
    milestone_value,
    driver_id,
    person_key,
    match_rule
FROM ops.yango_payment_status_ledger
WHERE snapshot_at >= CURRENT_DATE
    AND driver_id IS NULL
ORDER BY pay_date DESC
LIMIT 5;

-- 3. Verificar si la vista enriquecida puede asignar driver_id_final
SELECT 
    'Vista enriquecida' AS check_type,
    COUNT(*) as total,
    COUNT(*) FILTER (WHERE driver_id_final IS NOT NULL) as with_driver_id_final,
    COUNT(*) FILTER (WHERE person_key_final IS NOT NULL) as with_person_key_final
FROM ops.v_yango_payments_ledger_latest_enriched
WHERE pay_date >= '2025-12-18';

-- 4. Verificar si hay un proceso de backfill de identidad
-- Buscar funciones relacionadas con backfill
SELECT 
    routine_name,
    routine_type
FROM information_schema.routines
WHERE routine_schema = 'ops'
    AND routine_name LIKE '%backfill%'
    OR routine_name LIKE '%identity%';

-- 5. Verificar si los pagos sin driver_id pueden matchear por nombre
SELECT 
    l.source_pk,
    l.raw_driver_name,
    l.driver_name_normalized,
    COUNT(DISTINCT d.driver_id) as matching_drivers_count
FROM ops.yango_payment_status_ledger l
LEFT JOIN public.drivers d 
    ON UPPER(TRIM(REGEXP_REPLACE(d.full_name, '[ÀÁÂÃÄÅÈÉÊËÌÍÎÏÒÓÔÕÖÙÚÛÜÑÇ]', '', 'g'))) 
       = l.driver_name_normalized
WHERE l.snapshot_at >= CURRENT_DATE
    AND l.driver_id IS NULL
GROUP BY l.source_pk, l.raw_driver_name, l.driver_name_normalized
HAVING COUNT(DISTINCT d.driver_id) > 0
LIMIT 10;



