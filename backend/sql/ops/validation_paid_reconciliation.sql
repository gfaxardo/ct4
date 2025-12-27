-- ============================================================================
-- VALIDACIÓN: Reconciliación de Pagos (Paid Confirmed vs Paid Enriched)
-- ============================================================================
-- Scripts de validación para la reconciliación de pagos usando paid_confirmed
-- (identity confirmada desde upstream) vs paid_enriched (identity enriquecida).
-- ============================================================================

-- 1) TOTALES: EXPECTED vs PAID_CONFIRMED vs PAID_ENRICHED
SELECT 
    'Total Expected' AS metric,
    COUNT(*) AS count_rows,
    COALESCE(SUM(expected_amount), 0) AS total_amount
FROM ops.v_yango_payments_claims_cabinet_14d

UNION ALL

SELECT 
    'Paid Confirmed' AS metric,
    COUNT(*) FILTER (WHERE paid_status = 'paid_confirmed') AS count_rows,
    COALESCE(SUM(expected_amount) FILTER (WHERE paid_status = 'paid_confirmed'), 0) AS total_amount
FROM ops.v_yango_payments_claims_cabinet_14d

UNION ALL

SELECT 
    'Paid Enriched' AS metric,
    COUNT(*) FILTER (WHERE paid_status = 'paid_enriched') AS count_rows,
    COALESCE(SUM(expected_amount) FILTER (WHERE paid_status = 'paid_enriched'), 0) AS total_amount
FROM ops.v_yango_payments_claims_cabinet_14d

UNION ALL

SELECT 
    'Pending Active' AS metric,
    COUNT(*) FILTER (WHERE paid_status = 'pending_active') AS count_rows,
    COALESCE(SUM(expected_amount) FILTER (WHERE paid_status = 'pending_active'), 0) AS total_amount
FROM ops.v_yango_payments_claims_cabinet_14d

UNION ALL

SELECT 
    'Pending Expired' AS metric,
    COUNT(*) FILTER (WHERE paid_status = 'pending_expired') AS count_rows,
    COALESCE(SUM(expected_amount) FILTER (WHERE paid_status = 'pending_expired'), 0) AS total_amount
FROM ops.v_yango_payments_claims_cabinet_14d;

-- 2) BREAKDOWN POR SEMANA
SELECT 
    pay_week_start_monday,
    COUNT(*) AS count_total,
    COUNT(*) FILTER (WHERE paid_status = 'paid_confirmed') AS count_paid_confirmed,
    COUNT(*) FILTER (WHERE paid_status = 'paid_enriched') AS count_paid_enriched,
    COUNT(*) FILTER (WHERE paid_status = 'pending_active') AS count_pending_active,
    COUNT(*) FILTER (WHERE paid_status = 'pending_expired') AS count_pending_expired,
    COALESCE(SUM(expected_amount), 0) AS total_expected,
    COALESCE(SUM(expected_amount) FILTER (WHERE paid_status = 'paid_confirmed'), 0) AS total_paid_confirmed,
    COALESCE(SUM(expected_amount) FILTER (WHERE paid_status = 'paid_enriched'), 0) AS total_paid_enriched,
    COALESCE(SUM(expected_amount) FILTER (WHERE paid_status = 'pending_expired'), 0) AS total_pending_expired
FROM ops.v_yango_payments_claims_cabinet_14d
GROUP BY pay_week_start_monday
ORDER BY pay_week_start_monday DESC
LIMIT 20;

-- 3) BREAKDOWN POR MILESTONE
SELECT 
    milestone_value,
    COUNT(*) AS count_total,
    COUNT(*) FILTER (WHERE paid_status = 'paid_confirmed') AS count_paid_confirmed,
    COUNT(*) FILTER (WHERE paid_status = 'paid_enriched') AS count_paid_enriched,
    COUNT(*) FILTER (WHERE paid_status = 'pending_active') AS count_pending_active,
    COUNT(*) FILTER (WHERE paid_status = 'pending_expired') AS count_pending_expired,
    COALESCE(SUM(expected_amount), 0) AS total_expected,
    COALESCE(SUM(expected_amount) FILTER (WHERE paid_status = 'paid_confirmed'), 0) AS total_paid_confirmed,
    COALESCE(SUM(expected_amount) FILTER (WHERE paid_status = 'paid_enriched'), 0) AS total_paid_enriched,
    COALESCE(SUM(expected_amount) FILTER (WHERE paid_status = 'pending_expired'), 0) AS total_pending_expired
FROM ops.v_yango_payments_claims_cabinet_14d
GROUP BY milestone_value
ORDER BY milestone_value;

-- 4) DISTRIBUCIÓN DE paid_status
SELECT 
    paid_status,
    COUNT(*) AS count_rows,
    COALESCE(SUM(expected_amount), 0) AS total_amount,
    ROUND(100.0 * COUNT(*) / NULLIF((SELECT COUNT(*) FROM ops.v_yango_payments_claims_cabinet_14d), 0), 2) AS pct_count,
    ROUND(100.0 * COALESCE(SUM(expected_amount), 0) / NULLIF((SELECT SUM(expected_amount) FROM ops.v_yango_payments_claims_cabinet_14d), 0), 2) AS pct_amount
FROM ops.v_yango_payments_claims_cabinet_14d
GROUP BY paid_status
ORDER BY 
    CASE paid_status
        WHEN 'paid_confirmed' THEN 1
        WHEN 'paid_enriched' THEN 2
        WHEN 'pending_active' THEN 3
        WHEN 'pending_expired' THEN 4
        ELSE 5
    END;

-- 5) MUESTRA DE PAID_ENRICHED (para revisión)
SELECT 
    driver_id,
    person_key,
    lead_date,
    pay_week_start_monday,
    milestone_value,
    expected_amount,
    currency,
    due_date,
    window_status,
    paid_status,
    is_paid_effective,
    match_method
FROM ops.v_yango_payments_claims_cabinet_14d
WHERE paid_status = 'paid_enriched'
ORDER BY pay_week_start_monday DESC, lead_date DESC
LIMIT 20;

-- 6) COMPARACIÓN: PAID_CONFIRMED vs PAID_ENRICHED
SELECT 
    'Paid Confirmed (real)' AS type,
    COUNT(*) AS count_rows,
    COALESCE(SUM(expected_amount), 0) AS total_amount
FROM ops.v_yango_payments_claims_cabinet_14d
WHERE paid_status = 'paid_confirmed'

UNION ALL

SELECT 
    'Paid Enriched (probable)' AS type,
    COUNT(*) AS count_rows,
    COALESCE(SUM(expected_amount), 0) AS total_amount
FROM ops.v_yango_payments_claims_cabinet_14d
WHERE paid_status = 'paid_enriched'

UNION ALL

SELECT 
    'Difference (Enriched - Confirmed)' AS type,
    (SELECT COUNT(*) FROM ops.v_yango_payments_claims_cabinet_14d WHERE paid_status = 'paid_enriched') - 
    (SELECT COUNT(*) FROM ops.v_yango_payments_claims_cabinet_14d WHERE paid_status = 'paid_confirmed') AS count_rows,
    (SELECT COALESCE(SUM(expected_amount), 0) FROM ops.v_yango_payments_claims_cabinet_14d WHERE paid_status = 'paid_enriched') - 
    (SELECT COALESCE(SUM(expected_amount), 0) FROM ops.v_yango_payments_claims_cabinet_14d WHERE paid_status = 'paid_confirmed') AS total_amount;
