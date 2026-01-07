-- Verificar y ejecutar backfill de identidad para pagos sin driver_id

-- 1. Verificar cuántos pagos insertados hoy NO tienen driver_id
SELECT 
    COUNT(*) as total_inserted_today,
    COUNT(*) FILTER (WHERE driver_id IS NOT NULL) as with_driver_id,
    COUNT(*) FILTER (WHERE driver_id IS NULL) as without_driver_id
FROM ops.yango_payment_status_ledger
WHERE snapshot_at >= CURRENT_DATE;

-- 2. Verificar si existe la función de backfill
SELECT 
    routine_name,
    routine_type
FROM information_schema.routines
WHERE routine_schema = 'ops'
    AND routine_name IN ('backfill_ledger_identity', 'enrich_ledger_identity');

-- 3. Si existe, ejecutar backfill (dry_run primero para ver qué haría)
-- NOTA: Comentar esta línea si no quieres ejecutarlo todavía
-- SELECT * FROM ops.backfill_ledger_identity(0.85, true);  -- dry_run = true

-- 4. Verificar si hay pagos que pueden matchear por nombre
SELECT 
    COUNT(*) as can_match_by_name
FROM ops.yango_payment_status_ledger l
WHERE l.snapshot_at >= CURRENT_DATE
    AND l.driver_id IS NULL
    AND EXISTS (
        SELECT 1 
        FROM public.drivers d 
        WHERE UPPER(TRIM(REGEXP_REPLACE(d.full_name, '[ÀÁÂÃÄÅÈÉÊËÌÍÎÏÒÓÔÕÖÙÚÛÜÑÇ]', '', 'g'))) 
              = l.driver_name_normalized
    );

