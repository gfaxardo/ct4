-- ============================================================================
-- VALIDACIÓN: Identidad del Ledger Yango
-- ============================================================================
-- Scripts de validación para el enriquecimiento de identidad del ledger Yango
-- usando matching por nombre contra public.drivers.
-- ============================================================================

-- 1) DISTRIBUCIÓN DE identity_status
SELECT 
    identity_status,
    match_rule,
    COUNT(*) AS count_rows,
    COUNT(*) FILTER (WHERE driver_id_final IS NOT NULL) AS count_with_driver_id,
    COUNT(*) FILTER (WHERE is_paid = true) AS count_is_paid_true
FROM ops.v_yango_payments_ledger_latest_enriched
GROUP BY identity_status, match_rule
ORDER BY identity_status, match_rule;

-- 2) DISTRIBUCIÓN DE is_paid=true POR identity_status
SELECT 
    identity_status,
    COUNT(*) AS count_total,
    COUNT(*) FILTER (WHERE is_paid = true) AS count_is_paid_true,
    ROUND(100.0 * COUNT(*) FILTER (WHERE is_paid = true) / NULLIF(COUNT(*), 0), 2) AS pct_is_paid_true
FROM ops.v_yango_payments_ledger_latest_enriched
GROUP BY identity_status
ORDER BY identity_status;

-- 3) MUESTRA DE 20 CASOS AMBIGUOS
SELECT 
    payment_key,
    raw_driver_name,
    driver_name_normalized,
    identity_status,
    match_rule,
    match_confidence,
    driver_id_original,
    driver_id_enriched,
    driver_id_final,
    is_paid,
    pay_date,
    milestone_value
FROM ops.v_yango_payments_ledger_latest_enriched
WHERE identity_status = 'ambiguous'
ORDER BY pay_date DESC NULLS LAST, payment_key
LIMIT 20;

-- 4) MUESTRA DE 20 CASOS NO_MATCH
SELECT 
    payment_key,
    raw_driver_name,
    driver_name_normalized,
    identity_status,
    match_rule,
    match_confidence,
    driver_id_original,
    driver_id_enriched,
    driver_id_final,
    is_paid,
    pay_date,
    milestone_value
FROM ops.v_yango_payments_ledger_latest_enriched
WHERE identity_status = 'no_match'
ORDER BY pay_date DESC NULLS LAST, payment_key
LIMIT 20;

-- 5) DISTRIBUCIÓN DE match_rule Y match_confidence
SELECT 
    match_rule,
    match_confidence,
    COUNT(*) AS count_rows,
    COUNT(*) FILTER (WHERE driver_id_final IS NOT NULL) AS count_with_driver_id,
    COUNT(*) FILTER (WHERE is_paid = true) AS count_is_paid_true
FROM ops.v_yango_payments_ledger_latest_enriched
GROUP BY match_rule, match_confidence
ORDER BY 
    CASE match_confidence 
        WHEN 'high' THEN 1
        WHEN 'medium' THEN 2
        WHEN 'low' THEN 3
        ELSE 4
    END,
    match_rule;

-- 6) RESUMEN: TOTALES POR CATEGORÍA
SELECT 
    'Total ledger rows' AS category,
    COUNT(*)::text AS value
FROM ops.v_yango_payments_ledger_latest_enriched

UNION ALL

SELECT 
    'Ledger is_paid=true' AS category,
    COUNT(*) FILTER (WHERE is_paid = true)::text AS value
FROM ops.v_yango_payments_ledger_latest_enriched

UNION ALL

SELECT 
    'Confirmed (upstream)' AS category,
    COUNT(*) FILTER (WHERE identity_status = 'confirmed')::text AS value
FROM ops.v_yango_payments_ledger_latest_enriched

UNION ALL

SELECT 
    'Enriched (name match)' AS category,
    COUNT(*) FILTER (WHERE identity_status = 'enriched')::text AS value
FROM ops.v_yango_payments_ledger_latest_enriched

UNION ALL

SELECT 
    'Ambiguous' AS category,
    COUNT(*) FILTER (WHERE identity_status = 'ambiguous')::text AS value
FROM ops.v_yango_payments_ledger_latest_enriched

UNION ALL

SELECT 
    'No match' AS category,
    COUNT(*) FILTER (WHERE identity_status = 'no_match')::text AS value
FROM ops.v_yango_payments_ledger_latest_enriched

UNION ALL

SELECT 
    'is_paid=true AND confirmed' AS category,
    COUNT(*) FILTER (WHERE is_paid = true AND identity_status = 'confirmed')::text AS value
FROM ops.v_yango_payments_ledger_latest_enriched

UNION ALL

SELECT 
    'is_paid=true AND enriched' AS category,
    COUNT(*) FILTER (WHERE is_paid = true AND identity_status = 'enriched')::text AS value
FROM ops.v_yango_payments_ledger_latest_enriched

UNION ALL

SELECT 
    'is_paid=true AND ambiguous' AS category,
    COUNT(*) FILTER (WHERE is_paid = true AND identity_status = 'ambiguous')::text AS value
FROM ops.v_yango_payments_ledger_latest_enriched

UNION ALL

SELECT 
    'is_paid=true AND no_match' AS category,
    COUNT(*) FILTER (WHERE is_paid = true AND identity_status = 'no_match')::text AS value
FROM ops.v_yango_payments_ledger_latest_enriched;
