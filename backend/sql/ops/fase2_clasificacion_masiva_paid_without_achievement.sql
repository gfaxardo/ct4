-- ============================================================================
-- FASE 2: Clasificación Masiva PAID_WITHOUT_ACHIEVEMENT
-- ============================================================================
-- PROPÓSITO:
-- Clasificar TODOS los casos PAID_WITHOUT_ACHIEVEMENT en 4 causas mutuamente excluyentes:
-- 1) IDENTITY_MISMATCH - Problema de identidad (person_key/driver_id mismatch)
-- 2) WINDOW_MISMATCH - Regla válida pero ventana distinta a la esperada
-- 3) INSUFFICIENT_TRIPS_CONFIRMED - Trips insuficientes en summary_daily
-- 4) UPSTREAM_OVERPAYMENT - Yango pagó sin suficiente evidencia operativa (default)
--
-- METODOLOGÍA:
-- - SQL read-only (no recalcula, no modifica)
-- - Usa ops.v_cabinet_milestones_reconciled como fuente principal
-- - Usa summary_daily solo como evidencia (no recalcula milestones)
-- - Clasificación mutuamente excluyente (una causa por caso)
-- - Prioridad de clasificación: IDENTITY_MISMATCH > WINDOW_MISMATCH > INSUFFICIENT_TRIPS_CONFIRMED > UPSTREAM_OVERPAYMENT
-- ============================================================================

-- ============================================================================
-- QUERY 1: CLASIFICACIÓN MASIVA (todos los casos)
-- ============================================================================
-- Clasifica cada caso PAID_WITHOUT_ACHIEVEMENT en una de las 4 causas.
-- Incluye evidencia: trips_in_window, first_day_in_window, last_day_in_window, classification_evidence
-- ============================================================================

WITH base_paid_without AS (
    -- Base: Todos los casos PAID_WITHOUT_ACHIEVEMENT
    SELECT 
        r.driver_id,
        r.milestone_value,
        r.paid_person_key,
        r.pay_date,
        r.payment_key,
        r.identity_status,
        r.match_rule,
        r.match_confidence
    FROM ops.v_cabinet_milestones_reconciled r
    WHERE r.reconciliation_status = 'PAID_WITHOUT_ACHIEVEMENT'
        AND r.driver_id IS NOT NULL
),
paid_details AS (
    -- Enriquecer con detalles del PAID
    SELECT 
        bpw.*,
        p.driver_id_original,
        p.driver_id_enriched,
        p.person_key_original,
        p.raw_driver_name,
        p.latest_snapshot_at
    FROM base_paid_without bpw
    LEFT JOIN ops.v_cabinet_milestones_paid p
        ON p.driver_id = bpw.driver_id
        AND p.milestone_value = bpw.milestone_value
),
payment_rules AS (
    -- Reglas de pago aplicables (para verificar ventanas)
    SELECT 
        milestone_trips AS milestone_value,
        window_days,
        valid_from,
        valid_to,
        amount
    FROM ops.partner_payment_rules
    WHERE origin_tag = 'cabinet'
        AND milestone_trips IN (1, 5, 25)
        AND is_active = true
),
achieved_by_person_key AS (
    -- Verificar si existe ACHIEVED por person_key (pero no por driver_id)
    SELECT DISTINCT
        a.person_key,
        a.milestone_value,
        true AS exists_achieved_by_person_key
    FROM base_paid_without bpw
    INNER JOIN ops.v_cabinet_milestones_achieved a
        ON a.person_key = bpw.paid_person_key
        AND a.milestone_value = bpw.milestone_value
    WHERE bpw.paid_person_key IS NOT NULL
),
trips_in_window_calc AS (
    -- Calcular trips en ventana [pay_date - window_days, pay_date]
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
    LEFT JOIN payment_rules pr
        ON pr.milestone_value = pd.milestone_value
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
        pd.paid_person_key,
        pd.pay_date,
        pd.payment_key,
        pd.identity_status,
        pd.match_rule,
        pd.match_confidence,
        pd.driver_id_original,
        pd.driver_id_enriched,
        pd.person_key_original,
        pd.raw_driver_name,
        pd.latest_snapshot_at,
        pr.window_days AS rule_window_days,
        pr.valid_from AS rule_valid_from,
        pr.valid_to AS rule_valid_to,
        twc.first_day_in_window,
        twc.last_day_in_window,
        twc.trips_in_window,
        apk.exists_achieved_by_person_key,
        
        -- CLASIFICACIÓN (prioridad: más específica primero)
        CASE
            -- 1. IDENTITY_MISMATCH: existe achieved por person_key pero no por driver_id
            --    O driver_id_enriched != driver_id_original con match_confidence != 'high'
            WHEN apk.exists_achieved_by_person_key = true THEN 'IDENTITY_MISMATCH'
            WHEN pd.driver_id_enriched IS NOT NULL 
                AND (pd.driver_id_original IS NULL OR pd.driver_id_original != pd.driver_id_enriched)
                AND pd.match_confidence != 'high' THEN 'IDENTITY_MISMATCH'
            
            -- 2. WINDOW_MISMATCH: pay_date fuera de [valid_from, valid_to]
            WHEN pr.valid_from IS NOT NULL AND pd.pay_date < pr.valid_from THEN 'WINDOW_MISMATCH'
            WHEN pr.valid_to IS NOT NULL AND pd.pay_date > pr.valid_to THEN 'WINDOW_MISMATCH'
            
            -- 3. INSUFFICIENT_TRIPS_CONFIRMED: trips_in_window < milestone_value
            WHEN twc.trips_in_window < pd.milestone_value THEN 'INSUFFICIENT_TRIPS_CONFIRMED'
            
            -- 4. UPSTREAM_OVERPAYMENT: default
            ELSE 'UPSTREAM_OVERPAYMENT'
        END AS classification_cause,
        
        -- Evidencia textual
        CASE
            WHEN apk.exists_achieved_by_person_key = true THEN 
                'Found ACHIEVED by person_key but not by driver_id'
            WHEN pd.driver_id_enriched IS NOT NULL 
                AND (pd.driver_id_original IS NULL OR pd.driver_id_original != pd.driver_id_enriched)
                AND pd.match_confidence != 'high' THEN 
                'Matching enriched: driver_id_original=' || COALESCE(pd.driver_id_original, 'NULL') || 
                ', driver_id_enriched=' || pd.driver_id_enriched || 
                ', confidence=' || pd.match_confidence
            WHEN pr.valid_from IS NOT NULL AND pd.pay_date < pr.valid_from THEN 
                'pay_date (' || pd.pay_date || ') before rule valid_from (' || pr.valid_from || ')'
            WHEN pr.valid_to IS NOT NULL AND pd.pay_date > pr.valid_to THEN 
                'pay_date (' || pd.pay_date || ') after rule valid_to (' || pr.valid_to || ')'
            WHEN twc.trips_in_window < pd.milestone_value THEN 
                'trips_in_window=' || twc.trips_in_window || ' < milestone=' || pd.milestone_value || 
                ' (window: ' || twc.first_day_in_window || ' to ' || twc.last_day_in_window || ')'
            ELSE 
                'No specific evidence found - upstream overpayment'
        END AS classification_evidence
        
    FROM paid_details pd
    LEFT JOIN payment_rules pr
        ON pr.milestone_value = pd.milestone_value
    LEFT JOIN trips_in_window_calc twc
        ON twc.driver_id = pd.driver_id
        AND twc.milestone_value = pd.milestone_value
    LEFT JOIN achieved_by_person_key apk
        ON apk.person_key = pd.paid_person_key
        AND apk.milestone_value = pd.milestone_value
)
SELECT 
    driver_id,
    milestone_value,
    paid_person_key,
    pay_date,
    payment_key,
    identity_status,
    match_rule,
    match_confidence,
    driver_id_original,
    driver_id_enriched,
    person_key_original,
    raw_driver_name,
    rule_window_days,
    rule_valid_from,
    rule_valid_to,
    first_day_in_window,
    last_day_in_window,
    trips_in_window,
    classification_cause,
    classification_evidence
FROM classification
ORDER BY classification_cause, pay_date DESC, driver_id, milestone_value;

-- ============================================================================
-- QUERY 2: CONTEOS POR CAUSA
-- ============================================================================
-- Resumen estadístico: cuántos casos hay en cada causa
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
    COUNT(*) AS total_cases,
    COUNT(DISTINCT driver_id) AS unique_drivers,
    COUNT(*) FILTER (WHERE milestone_value = 1) AS count_m1,
    COUNT(*) FILTER (WHERE milestone_value = 5) AS count_m5,
    COUNT(*) FILTER (WHERE milestone_value = 25) AS count_m25,
    ROUND(100.0 * COUNT(*) / NULLIF((SELECT COUNT(*) FROM classification), 0), 2) AS pct_total
FROM classification
GROUP BY classification_cause
ORDER BY total_cases DESC;

-- ============================================================================
-- QUERY 3: EJEMPLOS POR CAUSA (limit 10 por causa)
-- ============================================================================
-- Muestra hasta 10 ejemplos de cada causa para análisis detallado
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
        pd.*,
        pr.window_days AS rule_window_days,
        pr.valid_from AS rule_valid_from,
        pr.valid_to AS rule_valid_to,
        twc.first_day_in_window,
        twc.last_day_in_window,
        twc.trips_in_window,
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
    paid_person_key,
    pay_date,
    payment_key,
    identity_status,
    match_rule,
    match_confidence,
    driver_id_original,
    driver_id_enriched,
    person_key_original,
    raw_driver_name,
    rule_window_days,
    rule_valid_from,
    rule_valid_to,
    first_day_in_window,
    last_day_in_window,
    trips_in_window,
    classification_evidence
FROM classification
WHERE row_num <= 10
ORDER BY classification_cause, pay_date DESC, driver_id, milestone_value;
