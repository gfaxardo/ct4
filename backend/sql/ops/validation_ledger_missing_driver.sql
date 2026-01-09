-- ============================================================================
-- VALIDACIÓN: Ledger con driver_id NULL y Matching Fallback
-- Objetivo: Entender el estado del ledger y por qué no matchea con claims
-- ============================================================================

-- 1) LEDGER ROWS CON driver_id NULL
-- Muestra cuántos registros en el ledger tienen driver_id NULL
SELECT 
    'Ledger rows con driver_id NULL' AS metric,
    COUNT(*) AS count_rows,
    COUNT(*) FILTER (WHERE is_paid = true) AS count_is_paid_true,
    COUNT(*) FILTER (WHERE person_key IS NOT NULL) AS count_with_person_key,
    COUNT(*) FILTER (WHERE is_paid = true AND person_key IS NOT NULL) AS count_is_paid_true_with_person_key
FROM ops.v_yango_payments_ledger_latest
WHERE driver_id IS NULL;

-- 2) LEDGER PAID ROWS CON driver_id NULL
-- Registros pagados que no tienen driver_id (potencialmente matchables por person_key)
SELECT 
    payment_key,
    pay_date,
    is_paid,
    milestone_value,
    driver_id,
    person_key,
    raw_driver_name,
    match_rule,
    match_confidence
FROM ops.v_yango_payments_ledger_latest
WHERE driver_id IS NULL
    AND is_paid = true
ORDER BY pay_date DESC NULLS LAST
LIMIT 20;

-- 3) OVERLAP CLAIMS VS LEDGER POR driver_id
-- Verificar cuántos matches existen por driver_id + milestone_value
SELECT 
    'Matches por driver_id' AS match_type,
    COUNT(*) AS count_matches,
    SUM(c.expected_amount) AS total_matched_amount
FROM ops.v_yango_payments_claims_cabinet_14d c
WHERE c.match_method = 'driver_id'
    AND c.is_paid_effective = true;

-- 4) OVERLAP CLAIMS VS LEDGER POR person_key (FALLBACK)
-- Verificar cuántos matches existen por person_key + milestone_value (fallback)
SELECT 
    'Matches por person_key (fallback)' AS match_type,
    COUNT(*) AS count_matches,
    SUM(c.expected_amount) AS total_matched_amount
FROM ops.v_yango_payments_claims_cabinet_14d c
WHERE c.match_method = 'person_key'
    AND c.is_paid_effective = true;

-- 5) TOP 20 LEDGER PAID ROWS QUE NO MATCHEAN NINGÚN CLAIM
-- Registros pagados en el ledger que no tienen match en claims
-- (útil para auditoría y entender qué pagos no se pueden atribuir)
SELECT 
    l.payment_key,
    l.pay_date,
    l.is_paid,
    l.milestone_value,
    l.driver_id,
    l.person_key,
    l.raw_driver_name,
    l.match_rule,
    l.match_confidence,
    CASE 
        WHEN l.driver_id IS NULL THEN 'driver_id_null'
        WHEN NOT EXISTS (
            SELECT 1 FROM ops.v_yango_payments_claims_cabinet_14d c
            WHERE c.driver_id = l.driver_id AND c.milestone_value = l.milestone_value
        ) THEN 'no_match_by_driver_id'
        WHEN l.person_key IS NOT NULL AND NOT EXISTS (
            SELECT 1 FROM ops.v_yango_payments_claims_cabinet_14d c
            WHERE c.person_key = l.person_key AND c.milestone_value = l.milestone_value
        ) THEN 'no_match_by_person_key'
        ELSE 'unknown'
    END AS unmatched_reason
FROM ops.v_yango_payments_ledger_latest l
WHERE l.is_paid = true
    AND (
        -- No existe match por driver_id
        l.driver_id IS NULL
        OR NOT EXISTS (
            SELECT 1 FROM ops.v_yango_payments_claims_cabinet_14d c
            WHERE c.driver_id = l.driver_id 
                AND c.milestone_value = l.milestone_value
        )
    )
    AND (
        -- No existe match por person_key (fallback)
        l.person_key IS NULL
        OR NOT EXISTS (
            SELECT 1 FROM ops.v_yango_payments_claims_cabinet_14d c
            WHERE c.person_key = l.person_key 
                AND c.milestone_value = l.milestone_value
        )
    )
ORDER BY l.pay_date DESC NULLS LAST
LIMIT 20;

-- 6) DISTRIBUCIÓN DE match_method EN CLAIMS
-- Ver cómo se distribuyen los matches (driver_id vs person_key vs none)
SELECT 
    match_method,
    COUNT(*) AS count_rows,
    SUM(expected_amount) AS total_amount,
    COUNT(*) FILTER (WHERE paid_status = 'paid') AS count_paid,
    SUM(expected_amount) FILTER (WHERE paid_status = 'paid') AS amount_paid
FROM ops.v_yango_payments_claims_cabinet_14d
GROUP BY match_method
ORDER BY match_method;

-- 7) COMPARACIÓN: CLAIMS SIN driver_id QUE PUEDEN MATCHEAR POR person_key
-- Ver cuántos claims sin driver_id tienen person_key y podrían matchear
SELECT 
    'Claims sin driver_id con person_key' AS metric,
    COUNT(*) AS count_rows,
    SUM(expected_amount) AS total_amount,
    COUNT(*) FILTER (WHERE paid_status = 'paid') AS count_paid,
    COUNT(*) FILTER (WHERE match_method = 'person_key') AS count_matched_by_person_key
FROM ops.v_yango_payments_claims_cabinet_14d
WHERE driver_id IS NULL
    AND person_key IS NOT NULL;

-- 8) RESUMEN EJECUTIVO
-- Vista general del estado del matching
SELECT 
    'Resumen Ejecutivo' AS section,
    (SELECT COUNT(*) FROM ops.v_yango_payments_ledger_latest WHERE driver_id IS NULL AND is_paid = true) AS ledger_paid_without_driver_id,
    (SELECT COUNT(*) FROM ops.v_yango_payments_claims_cabinet_14d WHERE match_method = 'driver_id' AND paid_status = 'paid') AS claims_matched_by_driver_id,
    (SELECT COUNT(*) FROM ops.v_yango_payments_claims_cabinet_14d WHERE match_method = 'person_key' AND paid_status = 'paid') AS claims_matched_by_person_key,
    (SELECT COUNT(*) FROM ops.v_yango_payments_claims_cabinet_14d WHERE match_method = 'none' AND paid_status = 'paid') AS claims_paid_without_match,
    (SELECT COUNT(*) FROM ops.v_yango_payments_claims_cabinet_14d WHERE driver_id IS NULL AND person_key IS NOT NULL) AS claims_without_driver_id_but_with_person_key;






