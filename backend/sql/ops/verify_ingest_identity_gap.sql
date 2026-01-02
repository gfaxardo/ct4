-- ============================================================================
-- Verificación: Gap de Identidad entre Raw Current y Ledger
-- ============================================================================
-- Queries para verificar el gap de identidad antes y después de aplicar
-- el patch de backfill de identidad en el ingest.
--
-- Ejecutar ANTES del patch para medir el gap inicial.
-- Ejecutar DESPUÉS del patch y re-ejecutar ingest para verificar que se cerró.
-- ============================================================================

-- ============================================================================
-- 1. GAP: Count de registros donde ledger.driver_id IS NULL pero raw.driver_id IS NOT NULL
-- ============================================================================
-- Este query identifica el gap principal: registros que tienen identidad
-- en raw_current pero no en el ledger.
SELECT 
    'GAP: Ledger sin identidad pero Raw con identidad' AS metric,
    COUNT(*) AS count_gap
FROM ops.v_yango_payments_raw_current rc
INNER JOIN ops.v_yango_payments_ledger_latest l
    ON l.payment_key = rc.payment_key
    AND l.state_hash = rc.state_hash
WHERE l.driver_id IS NULL
    AND rc.driver_id IS NOT NULL;

-- ============================================================================
-- 2. Distribución de match_rule en raw_current
-- ============================================================================
-- Ver distribución de reglas de matching en la vista raw actual
SELECT 
    'Distribución match_rule en raw_current' AS metric,
    match_rule,
    match_confidence,
    COUNT(*) AS count_rows,
    COUNT(*) FILTER (WHERE driver_id IS NOT NULL) AS count_with_driver_id,
    COUNT(*) FILTER (WHERE driver_id IS NULL) AS count_without_driver_id
FROM ops.v_yango_payments_raw_current
GROUP BY match_rule, match_confidence
ORDER BY match_rule, match_confidence;

-- ============================================================================
-- 3. Distribución de match_rule en ledger_latest
-- ============================================================================
-- Ver distribución de reglas de matching en el ledger (último snapshot)
SELECT 
    'Distribución match_rule en ledger_latest' AS metric,
    match_rule,
    match_confidence,
    COUNT(*) AS count_rows,
    COUNT(*) FILTER (WHERE driver_id IS NOT NULL) AS count_with_driver_id,
    COUNT(*) FILTER (WHERE driver_id IS NULL) AS count_without_driver_id
FROM ops.v_yango_payments_ledger_latest
GROUP BY match_rule, match_confidence
ORDER BY match_rule, match_confidence;

-- ============================================================================
-- 4. Comparación lado a lado: Raw vs Ledger
-- ============================================================================
-- Comparación detallada de match_rule y match_confidence entre raw y ledger
-- para los mismos payment_key y state_hash
SELECT 
    'Comparación Raw vs Ledger' AS metric,
    rc.match_rule AS raw_match_rule,
    rc.match_confidence AS raw_match_confidence,
    l.match_rule AS ledger_match_rule,
    l.match_confidence AS ledger_match_confidence,
    COUNT(*) AS count_rows,
    COUNT(*) FILTER (WHERE rc.driver_id IS NOT NULL AND l.driver_id IS NULL) AS gap_count
FROM ops.v_yango_payments_raw_current rc
INNER JOIN ops.v_yango_payments_ledger_latest l
    ON l.payment_key = rc.payment_key
    AND l.state_hash = rc.state_hash
GROUP BY rc.match_rule, rc.match_confidence, l.match_rule, l.match_confidence
ORDER BY gap_count DESC, rc.match_rule, l.match_rule;

-- ============================================================================
-- 5. Muestra de registros con gap (para inspección manual)
-- ============================================================================
-- Muestra los primeros 50 registros con gap para inspección
SELECT 
    'Muestra de registros con gap' AS metric,
    rc.payment_key,
    rc.state_hash,
    rc.raw_driver_name,
    rc.driver_name_normalized,
    rc.driver_id AS raw_driver_id,
    rc.person_key AS raw_person_key,
    rc.match_rule AS raw_match_rule,
    rc.match_confidence AS raw_match_confidence,
    l.driver_id AS ledger_driver_id,
    l.person_key AS ledger_person_key,
    l.match_rule AS ledger_match_rule,
    l.match_confidence AS ledger_match_confidence,
    l.latest_snapshot_at AS ledger_snapshot_at
FROM ops.v_yango_payments_raw_current rc
INNER JOIN ops.v_yango_payments_ledger_latest l
    ON l.payment_key = rc.payment_key
    AND l.state_hash = rc.state_hash
WHERE l.driver_id IS NULL
    AND rc.driver_id IS NOT NULL
LIMIT 50;

-- ============================================================================
-- 6. Verificación post-patch: Registros que deberían ser actualizados
-- ============================================================================
-- Query para verificar cuántos registros serían actualizados por el UPDATE
-- del patch (antes de ejecutar el ingest)
SELECT 
    'Registros candidatos para UPDATE' AS metric,
    COUNT(*) AS count_candidates
FROM ops.yango_payment_status_ledger l
INNER JOIN ops.v_yango_payments_raw_current_aliases rc
    ON l.payment_key = rc.payment_key
    AND l.state_hash = rc.state_hash
WHERE l.driver_id IS NULL
    AND rc.driver_id IS NOT NULL;

-- ============================================================================
-- 7. Verificación de matches por driver_name_unique
-- ============================================================================
-- Verificar específicamente los matches por driver_name_unique que deberían
-- estar en el ledger
SELECT 
    'Matches driver_name_unique en raw_current' AS metric,
    COUNT(*) AS total_matches,
    COUNT(*) FILTER (WHERE driver_id IS NOT NULL) AS with_driver_id
FROM ops.v_yango_payments_raw_current
WHERE match_rule = 'driver_name_unique'
    AND match_confidence = 'medium';

SELECT 
    'Matches driver_name_unique en ledger_latest' AS metric,
    COUNT(*) AS total_matches,
    COUNT(*) FILTER (WHERE driver_id IS NOT NULL) AS with_driver_id
FROM ops.v_yango_payments_ledger_latest
WHERE match_rule = 'driver_name_unique'
    AND match_confidence = 'medium';

