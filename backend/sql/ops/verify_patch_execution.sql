-- ============================================================================
-- Verificación: Ejecución del Patch de Identidad
-- ============================================================================
-- Queries para verificar que el UPDATE posterior se ejecutó correctamente
-- y cuántas filas fueron actualizadas con identidad.
-- ============================================================================

-- ============================================================================
-- 1. Verificar que la función existe y tiene el UPDATE posterior
-- ============================================================================
SELECT 
    'Verificación: Función tiene UPDATE posterior' AS verificación,
    CASE 
        WHEN NOT EXISTS (
            SELECT 1 
            FROM pg_proc p
            JOIN pg_namespace n ON p.pronamespace = n.oid
            WHERE n.nspname = 'ops' 
            AND p.proname = 'ingest_yango_payments_snapshot'
        ) THEN '❌ Función NO existe - ejecutar patch_ingest_identity_upsert.sql primero'
        WHEN pg_get_functiondef('ops.ingest_yango_payments_snapshot()'::regproc)::text 
             LIKE '%UPDATE ops.yango_payment_status_ledger%' 
        THEN '✅ Patch aplicado correctamente'
        ELSE '❌ Patch NO aplicado - ejecutar patch_ingest_identity_upsert.sql'
    END AS estado;

-- ============================================================================
-- 2. Verificar registros actualizados recientemente con identidad
-- ============================================================================
-- Contar cuántos registros tienen identidad y fueron actualizados recientemente
-- (en la última hora, asumiendo que el ingest se ejecutó recientemente)
SELECT 
    'Registros con identidad actualizados recientemente' AS verificación,
    COUNT(*) AS count_updated,
    MAX(latest_snapshot_at) AS ultimo_snapshot_at,
    MIN(latest_snapshot_at) AS primer_snapshot_at
FROM ops.v_yango_payments_ledger_latest
WHERE match_rule = 'driver_name_unique'
    AND match_confidence = 'medium'
    AND driver_id IS NOT NULL
    AND latest_snapshot_at >= NOW() - INTERVAL '2 hours';

-- ============================================================================
-- 3. Comparar distribución de matches antes/después
-- ============================================================================
-- Ver cuántos matches por driver_name_unique hay en raw vs ledger
SELECT 
    'raw_current: matches driver_name_unique' AS fuente,
    COUNT(*) AS total,
    COUNT(*) FILTER (WHERE driver_id IS NOT NULL) AS con_driver_id,
    COUNT(*) FILTER (WHERE driver_id IS NULL) AS sin_driver_id
FROM ops.v_yango_payments_raw_current
WHERE match_rule = 'driver_name_unique'
    AND match_confidence = 'medium'

UNION ALL

SELECT 
    'ledger_latest: matches driver_name_unique' AS fuente,
    COUNT(*) AS total,
    COUNT(*) FILTER (WHERE driver_id IS NOT NULL) AS con_driver_id,
    COUNT(*) FILTER (WHERE driver_id IS NULL) AS sin_driver_id
FROM ops.v_yango_payments_ledger_latest
WHERE match_rule = 'driver_name_unique'
    AND match_confidence = 'medium';

-- ============================================================================
-- 4. Verificar el gap actual (debería ser 0)
-- ============================================================================
SELECT 
    'GAP actual: Ledger sin identidad pero Raw con identidad' AS verificación,
    COUNT(*) AS count_gap,
    CASE 
        WHEN COUNT(*) = 0 THEN '✅ Gap cerrado completamente'
        ELSE '⚠️ Aún hay ' || COUNT(*) || ' registros con gap'
    END AS resultado
FROM ops.v_yango_payments_raw_current rc
INNER JOIN ops.v_yango_payments_ledger_latest l
    ON l.payment_key = rc.payment_key
    AND l.state_hash = rc.state_hash
WHERE l.driver_id IS NULL
    AND rc.driver_id IS NOT NULL;

-- ============================================================================
-- 5. Verificar que el UPDATE se puede ejecutar manualmente
-- ============================================================================
-- Este query muestra cuántos registros serían actualizados si ejecutáramos
-- el UPDATE manualmente (para debugging)
SELECT 
    'Registros candidatos para UPDATE (gap actual)' AS verificación,
    COUNT(*) AS count_candidates
FROM ops.yango_payment_status_ledger l
INNER JOIN ops.v_yango_payments_raw_current_aliases rc
    ON l.payment_key = rc.payment_key
    AND l.state_hash = rc.state_hash
WHERE l.driver_id IS NULL
    AND rc.driver_id IS NOT NULL;

-- ============================================================================
-- 6. Verificar el último snapshot_at en el ledger
-- ============================================================================
-- Ver cuándo fue el último snapshot para entender si el ingest se ejecutó
SELECT 
    'Último snapshot en el ledger' AS verificación,
    MAX(snapshot_at) AS ultimo_snapshot_at,
    COUNT(*) FILTER (WHERE snapshot_at >= NOW() - INTERVAL '1 hour') AS registros_ultima_hora,
    COUNT(*) AS total_registros
FROM ops.yango_payment_status_ledger;

-- ============================================================================
-- 7. Muestra de registros con identidad en el ledger
-- ============================================================================
-- Ver una muestra de registros que tienen identidad en el ledger
SELECT 
    'Muestra: Registros con identidad en ledger' AS verificación,
    payment_key,
    raw_driver_name,
    driver_id,
    person_key,
    match_rule,
    match_confidence,
    latest_snapshot_at
FROM ops.v_yango_payments_ledger_latest
WHERE match_rule = 'driver_name_unique'
    AND match_confidence = 'medium'
    AND driver_id IS NOT NULL
ORDER BY latest_snapshot_at DESC
LIMIT 10;

