-- ============================================================================
-- Pasos para Aplicar el Patch de Identidad en Ingest de Pagos
-- ============================================================================
-- Este script guía el proceso completo de aplicación del patch y verificación.
-- Ejecutar los pasos en orden.
-- ============================================================================

-- ============================================================================
-- PASO 1: Verificar el GAP inicial (ANTES del patch)
-- ============================================================================
-- Ejecutar este query para medir cuántos registros tienen identidad en raw
-- pero no en el ledger
SELECT 
    'GAP INICIAL: Ledger sin identidad pero Raw con identidad' AS paso,
    COUNT(*) AS count_gap,
    'Ejecutar ANTES del patch' AS nota
FROM ops.v_yango_payments_raw_current rc
INNER JOIN ops.v_yango_payments_ledger_latest l
    ON l.payment_key = rc.payment_key
    AND l.state_hash = rc.state_hash
WHERE l.driver_id IS NULL
    AND rc.driver_id IS NOT NULL;

-- ============================================================================
-- PASO 2: Aplicar el Patch (OBLIGATORIO)
-- ============================================================================
-- IMPORTANTE: Ejecutar primero este archivo para crear/actualizar la función:
-- backend/sql/ops/patch_ingest_identity_upsert.sql
--
-- O ejecutar directamente el contenido del archivo patch_ingest_identity_upsert.sql
-- que crea/actualiza la función ops.ingest_yango_payments_snapshot() con el UPDATE posterior.
--
-- Verificar que la función existe antes de continuar:
SELECT 
    'Verificación: Función existe' AS paso,
    CASE 
        WHEN EXISTS (
            SELECT 1 
            FROM pg_proc p
            JOIN pg_namespace n ON p.pronamespace = n.oid
            WHERE n.nspname = 'ops' 
            AND p.proname = 'ingest_yango_payments_snapshot'
        ) THEN '✅ Función existe'
        ELSE '❌ Función NO existe - EJECUTAR patch_ingest_identity_upsert.sql PRIMERO'
    END AS estado;

-- ============================================================================
-- PASO 3: Verificar que el patch se aplicó correctamente
-- ============================================================================
-- Verificar que la función existe y tiene el UPDATE posterior
SELECT 
    'Verificación: Función tiene UPDATE posterior' AS paso,
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
-- PASO 4: Ejecutar el Ingest para aplicar el backfill
-- ============================================================================
-- Esta función ejecutará el INSERT idempotente + el UPDATE posterior
-- que backfilleará la identidad
SELECT 
    'Ejecutando ingest con backfill de identidad...' AS paso,
    ops.ingest_yango_payments_snapshot() AS filas_insertadas;
-- Nota: El UPDATE se ejecuta automáticamente dentro de la función

-- ============================================================================
-- PASO 5: Verificar el GAP después del patch
-- ============================================================================
-- Ejecutar este query DESPUÉS del ingest para verificar que el gap se cerró
SELECT 
    'GAP DESPUÉS: Ledger sin identidad pero Raw con identidad' AS paso,
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
-- PASO 6: Verificación detallada - Comparación Raw vs Ledger
-- ============================================================================
-- Ver distribución de matches en raw_current vs ledger_latest
SELECT 
    'Distribución en raw_current' AS vista,
    match_rule,
    match_confidence,
    COUNT(*) AS total,
    COUNT(*) FILTER (WHERE driver_id IS NOT NULL) AS con_driver_id
FROM ops.v_yango_payments_raw_current
WHERE match_rule = 'driver_name_unique'
GROUP BY match_rule, match_confidence

UNION ALL

SELECT 
    'Distribución en ledger_latest' AS vista,
    match_rule,
    match_confidence,
    COUNT(*) AS total,
    COUNT(*) FILTER (WHERE driver_id IS NOT NULL) AS con_driver_id
FROM ops.v_yango_payments_ledger_latest
WHERE match_rule = 'driver_name_unique'
GROUP BY match_rule, match_confidence
ORDER BY vista, match_rule, match_confidence;

-- ============================================================================
-- PASO 7: Verificar registros actualizados en el último snapshot
-- ============================================================================
-- Ver cuántos registros fueron actualizados con identidad en el último snapshot
SELECT 
    'Registros actualizados con identidad' AS paso,
    COUNT(*) AS count_updated,
    MAX(latest_snapshot_at) AS ultimo_snapshot_at
FROM ops.v_yango_payments_ledger_latest
WHERE match_rule = 'driver_name_unique'
    AND match_confidence = 'medium'
    AND driver_id IS NOT NULL
    AND latest_snapshot_at >= NOW() - INTERVAL '1 hour'; -- Última hora

