-- ============================================================================
-- QUERY 2: CONTEOS POR CAUSA
-- ============================================================================

WITH base_paid_without AS (
    SELECT 
        r.driver_id,
        r.milestone_value,
        r.paid_person_key,
        r.pay_date
    FROM ops.v_cabinet_milestones_reconciled r
    WHERE r.reconciliation_status = 'PAID_WITHOUT_ACHIEVEMENT'
        AND r.driver_id IS NOT NULL
),
paid_details AS (
    SELECT 
        bpw.*,
        p.driver_id_original,
        p.driver_id_enriched,
        p.match_rule,
        p.match_confidence
    FROM base_paid_without bpw
    LEFT JOIN ops.v_cabinet_milestones_paid p
        ON p.driver_id = bpw.driver_id
        AND p.milestone_value = bpw.milestone_value
),
payment_rules AS (
    SELECT 
        milestone_trips AS milestone_value,
        window_days,
        valid_from,
        valid_to
    FROM ops.partner_payment_rules
    WHERE origin_tag = 'cabinet'
        AND milestone_trips IN (1, 5, 25)
        AND is_active = true
),
achieved_by_person_key AS (
    SELECT DISTINCT
        a.person_key,
        a.milestone_value
    FROM base_paid_without bpw
    INNER JOIN ops.v_cabinet_milestones_achieved a
        ON a.person_key = bpw.paid_person_key
        AND a.milestone_value = bpw.milestone_value
    WHERE bpw.paid_person_key IS NOT NULL
),
trips_in_window_calc AS (
    SELECT 
        pd.driver_id,
        pd.milestone_value,
        pd.pay_date,
        pr.window_days,
        COALESCE(SUM(
            CASE 
                WHEN sd.date_file IS NOT NULL 
                    AND sd.date_file ~ '^\d{2}-\d{2}-\d{4}$'
                    AND to_date(sd.date_file, 'DD-MM-YYYY') >= (pd.pay_date - (pr.window_days || ' days')::INTERVAL)::date
                    AND to_date(sd.date_file, 'DD-MM-YYYY') <= pd.pay_date
                THEN sd.count_orders_completed
                ELSE 0
            END
        ), 0) AS trips_in_window
    FROM paid_details pd
    LEFT JOIN payment_rules pr ON pr.milestone_value = pd.milestone_value
    LEFT JOIN public.summary_daily sd
        ON sd.driver_id = pd.driver_id
        AND sd.date_file IS NOT NULL
        AND sd.date_file ~ '^\d{2}-\d{2}-\d{4}$'
    GROUP BY pd.driver_id, pd.milestone_value, pd.pay_date, pr.window_days
),
classification AS (
    SELECT 
        pd.driver_id,
        pd.milestone_value,
        CASE
            WHEN EXISTS (
                SELECT 1 FROM achieved_by_person_key apk 
                WHERE apk.person_key = pd.paid_person_key 
                AND apk.milestone_value = pd.milestone_value
            ) THEN 'IDENTITY_MISMATCH'
            WHEN pd.driver_id_enriched IS NOT NULL 
                AND (pd.driver_id_original IS NULL OR pd.driver_id_original != pd.driver_id_enriched)
                AND pd.match_confidence != 'high' THEN 'IDENTITY_MISMATCH'
            WHEN pr.valid_from IS NOT NULL AND pd.pay_date < pr.valid_from THEN 'WINDOW_MISMATCH'
            WHEN pr.valid_to IS NOT NULL AND pd.pay_date > pr.valid_to THEN 'WINDOW_MISMATCH'
            WHEN twc.trips_in_window < pd.milestone_value THEN 'INSUFFICIENT_TRIPS_CONFIRMED'
            ELSE 'UPSTREAM_OVERPAYMENT'
        END AS classification_cause
    FROM paid_details pd
    LEFT JOIN payment_rules pr ON pr.milestone_value = pd.milestone_value
    LEFT JOIN trips_in_window_calc twc
        ON twc.driver_id = pd.driver_id
        AND twc.milestone_value = pd.milestone_value
)
SELECT 
    classification_cause,
    COUNT(*) AS total_rows,
    COUNT(DISTINCT driver_id) AS distinct_drivers,
    COUNT(*) FILTER (WHERE milestone_value = 1) AS count_m1,
    COUNT(*) FILTER (WHERE milestone_value = 5) AS count_m5,
    COUNT(*) FILTER (WHERE milestone_value = 25) AS count_m25,
    ROUND(100.0 * COUNT(*) / NULLIF((SELECT COUNT(*) FROM classification), 0), 2) AS pct_total
FROM classification
GROUP BY classification_cause
ORDER BY total_rows DESC;

-- ============================================================================
-- QUERY 3: EJEMPLOS POR CAUSA (limit 10 por causa)
-- ============================================================================

WITH base_paid_without AS (
    SELECT 
        r.driver_id,
        r.milestone_value,
        r.paid_person_key,
        r.pay_date,
        r.payment_key,
        r.identity_status,
        r.match_rule
    FROM ops.v_cabinet_milestones_reconciled r
    WHERE r.reconciliation_status = 'PAID_WITHOUT_ACHIEVEMENT'
        AND r.driver_id IS NOT NULL
),
paid_details AS (
    SELECT 
        bpw.*,
        p.driver_id_original,
        p.driver_id_enriched,
        p.person_key_original,
        p.raw_driver_name,
        p.match_confidence
    FROM base_paid_without bpw
    LEFT JOIN ops.v_cabinet_milestones_paid p
        ON p.driver_id = bpw.driver_id
        AND p.milestone_value = bpw.milestone_value
),
payment_rules AS (
    SELECT 
        milestone_trips AS milestone_value,
        window_days,
        valid_from,
        valid_to
    FROM ops.partner_payment_rules
    WHERE origin_tag = 'cabinet'
        AND milestone_trips IN (1, 5, 25)
        AND is_active = true
),
achieved_by_person_key AS (
    SELECT DISTINCT
        a.person_key,
        a.milestone_value
    FROM base_paid_without bpw
    INNER JOIN ops.v_cabinet_milestones_achieved a
        ON a.person_key = bpw.paid_person_key
        AND a.milestone_value = bpw.milestone_value
    WHERE bpw.paid_person_key IS NOT NULL
),
trips_in_window_calc AS (
    SELECT 
        pd.driver_id,
        pd.milestone_value,
        pd.pay_date,
        pr.window_days,
        (pd.pay_date - (pr.window_days || ' days')::INTERVAL)::date AS first_day_in_window,
        pd.pay_date AS last_day_in_window,
        COALESCE(SUM(
            CASE 
                WHEN sd.date_file IS NOT NULL 
                    AND sd.date_file ~ '^\d{2}-\d{2}-\d{4}$'
                    AND to_date(sd.date_file, 'DD-MM-YYYY') >= (pd.pay_date - (pr.window_days || ' days')::INTERVAL)::date
                    AND to_date(sd.date_file, 'DD-MM-YYYY') <= pd.pay_date
                THEN sd.count_orders_completed
                ELSE 0
            END
        ), 0) AS trips_in_window
    FROM paid_details pd
    LEFT JOIN payment_rules pr ON pr.milestone_value = pd.milestone_value
    LEFT JOIN public.summary_daily sd
        ON sd.driver_id = pd.driver_id
        AND sd.date_file IS NOT NULL
        AND sd.date_file ~ '^\d{2}-\d{2}-\d{4}$'
    GROUP BY pd.driver_id, pd.milestone_value, pd.pay_date, pr.window_days
),
classification AS (
    SELECT 
        pd.driver_id,
        pd.milestone_value,
        pd.pay_date,
        pd.payment_key,
        pr.window_days,
        pr.valid_from,
        pr.valid_to,
        twc.first_day_in_window,
        twc.last_day_in_window,
        twc.trips_in_window,
        pd.match_rule,
        pd.match_confidence,
        pd.driver_id_original,
        pd.driver_id_enriched,
        pd.person_key_original,
        CASE
            WHEN EXISTS (
                SELECT 1 FROM achieved_by_person_key apk 
                WHERE apk.person_key = pd.paid_person_key 
                AND apk.milestone_value = pd.milestone_value
            ) THEN 'IDENTITY_MISMATCH'
            WHEN pd.driver_id_enriched IS NOT NULL 
                AND (pd.driver_id_original IS NULL OR pd.driver_id_original != pd.driver_id_enriched)
                AND pd.match_confidence != 'high' THEN 'IDENTITY_MISMATCH'
            WHEN pr.valid_from IS NOT NULL AND pd.pay_date < pr.valid_from THEN 'WINDOW_MISMATCH'
            WHEN pr.valid_to IS NOT NULL AND pd.pay_date > pr.valid_to THEN 'WINDOW_MISMATCH'
            WHEN twc.trips_in_window < pd.milestone_value THEN 'INSUFFICIENT_TRIPS_CONFIRMED'
            ELSE 'UPSTREAM_OVERPAYMENT'
        END AS classification_cause,
        CASE
            WHEN EXISTS (
                SELECT 1 FROM achieved_by_person_key apk 
                WHERE apk.person_key = pd.paid_person_key 
                AND apk.milestone_value = pd.milestone_value
            ) THEN 'Found ACHIEVED by person_key but not by driver_id'
            WHEN pd.driver_id_enriched IS NOT NULL 
                AND (pd.driver_id_original IS NULL OR pd.driver_id_original != pd.driver_id_enriched)
                AND pd.match_confidence != 'high' THEN 
                'Matching enriched: confidence=' || pd.match_confidence
            WHEN pr.valid_from IS NOT NULL AND pd.pay_date < pr.valid_from THEN 
                'pay_date before rule valid_from'
            WHEN pr.valid_to IS NOT NULL AND pd.pay_date > pr.valid_to THEN 
                'pay_date after rule valid_to'
            WHEN twc.trips_in_window < pd.milestone_value THEN 
                'trips_in_window=' || twc.trips_in_window || ' < milestone=' || pd.milestone_value
            ELSE 'No specific evidence - upstream overpayment'
        END AS classification_evidence,
        ROW_NUMBER() OVER (
            PARTITION BY 
                CASE
                    WHEN EXISTS (
                        SELECT 1 FROM achieved_by_person_key apk 
                        WHERE apk.person_key = pd.paid_person_key 
                        AND apk.milestone_value = pd.milestone_value
                    ) THEN 'IDENTITY_MISMATCH'
                    WHEN pd.driver_id_enriched IS NOT NULL 
                        AND (pd.driver_id_original IS NULL OR pd.driver_id_original != pd.driver_id_enriched)
                        AND pd.match_confidence != 'high' THEN 'IDENTITY_MISMATCH'
                    WHEN pr.valid_from IS NOT NULL AND pd.pay_date < pr.valid_from THEN 'WINDOW_MISMATCH'
                    WHEN pr.valid_to IS NOT NULL AND pd.pay_date > pr.valid_to THEN 'WINDOW_MISMATCH'
                    WHEN twc.trips_in_window < pd.milestone_value THEN 'INSUFFICIENT_TRIPS_CONFIRMED'
                    ELSE 'UPSTREAM_OVERPAYMENT'
                END
            ORDER BY pd.pay_date DESC, pd.driver_id
        ) AS row_num
    FROM paid_details pd
    LEFT JOIN payment_rules pr ON pr.milestone_value = pd.milestone_value
    LEFT JOIN trips_in_window_calc twc
        ON twc.driver_id = pd.driver_id
        AND twc.milestone_value = pd.milestone_value
)
SELECT 
    classification_cause,
    driver_id,
    milestone_value,
    pay_date,
    payment_key,
    window_days,
    valid_from,
    valid_to,
    trips_in_window,
    first_day_in_window,
    last_day_in_window,
    match_rule,
    match_confidence,
    driver_id_original,
    driver_id_enriched,
    person_key_original,
    classification_evidence
FROM classification
WHERE row_num <= 10
ORDER BY classification_cause, pay_date DESC, driver_id, milestone_value;

-- ============================================================================
-- SANITY A: Distribución de date_file inválido en summary_daily
-- ============================================================================

SELECT 
    CASE 
        WHEN date_file IS NULL THEN 'NULL'
        WHEN date_file !~ '^\d{2}-\d{2}-\d{4}$' THEN 'INVALID_FORMAT'
        ELSE 'VALID'
    END AS date_file_status,
    COUNT(*) AS total_rows,
    COUNT(DISTINCT driver_id) AS distinct_drivers,
    ROUND(100.0 * COUNT(*) / NULLIF((SELECT COUNT(*) FROM public.summary_daily), 0), 2) AS pct_total
FROM public.summary_daily
GROUP BY 
    CASE 
        WHEN date_file IS NULL THEN 'NULL'
        WHEN date_file !~ '^\d{2}-\d{2}-\d{4}$' THEN 'INVALID_FORMAT'
        ELSE 'VALID'
    END
ORDER BY total_rows DESC;

-- ============================================================================
-- SANITY B: pay_date min/max + últimos 10 pagos PAID_WITHOUT_ACHIEVEMENT
-- ============================================================================

WITH min_max AS (
    SELECT 
        MIN(r.pay_date) AS pay_date_min,
        MAX(r.pay_date) AS pay_date_max
    FROM ops.v_cabinet_milestones_reconciled r
    WHERE r.reconciliation_status = 'PAID_WITHOUT_ACHIEVEMENT'
        AND r.driver_id IS NOT NULL
),
last_10 AS (
    SELECT 
        r.pay_date,
        r.driver_id,
        r.milestone_value,
        r.payment_key
    FROM ops.v_cabinet_milestones_reconciled r
    WHERE r.reconciliation_status = 'PAID_WITHOUT_ACHIEVEMENT'
        AND r.driver_id IS NOT NULL
    ORDER BY r.pay_date DESC, r.driver_id, r.milestone_value
    LIMIT 10
)
SELECT 
    'MIN_MAX' AS section,
    mm.pay_date_min AS pay_date,
    mm.pay_date_max,
    NULL::text AS driver_id,
    NULL::integer AS milestone_value,
    NULL::text AS payment_key
FROM min_max mm

UNION ALL

SELECT 
    'LAST_10' AS section,
    l.pay_date,
    NULL::date AS pay_date_max,
    l.driver_id,
    l.milestone_value,
    l.payment_key
FROM last_10 l

ORDER BY section, pay_date DESC;

