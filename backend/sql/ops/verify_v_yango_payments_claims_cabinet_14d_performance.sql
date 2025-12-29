-- Verification script: Check query plan and performance for v_yango_payments_claims_cabinet_14d
-- This confirms that the filter pushdown optimization is working correctly

-- IMPORTANT: Set a timeout to prevent hanging
SET LOCAL statement_timeout = '30000ms';

-- 1. Check the query plan with EXPLAIN ANALYZE (without actually executing)
-- This shows the execution plan without running the full query
EXPLAIN (ANALYZE, BUFFERS, VERBOSE)
SELECT 
    pay_week_start_monday,
    milestone_value,
    COUNT(*) AS row_count,
    SUM(expected_amount) AS total_expected
FROM ops.v_yango_payments_claims_cabinet_14d
GROUP BY pay_week_start_monday, milestone_value
ORDER BY pay_week_start_monday DESC, milestone_value
LIMIT 5;

-- 2. Verify that base_claims and ledger_enriched filters are being applied
-- Check the actual date range in the view (this should be fast with the filter)
SELECT 
    MIN(pay_week_start_monday) AS min_week,
    MAX(pay_week_start_monday) AS max_week,
    COUNT(*) AS total_rows,
    COUNT(DISTINCT pay_week_start_monday) AS distinct_weeks
FROM ops.v_yango_payments_claims_cabinet_14d;

-- 3. Expected results:
-- - min_week should be approximately 2 weeks ago from current week start (14 days)
-- - total_rows should be significantly reduced compared to unfiltered view
-- - Query execution time should be < 5-10 seconds
-- - EXPLAIN ANALYZE should show that filters are applied in base_claims and ledger_enriched CTEs

