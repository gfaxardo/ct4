-- ============================================================================
-- Vista: Detalle de Reconciliación Yango (Expected vs Paid)
-- ============================================================================
-- Compara pagos esperados (expected) desde ops.v_yango_receivable_payable_detail
-- con pagos reales (paid) desde ops.v_yango_payments_ledger_latest.
--
-- Matching:
-- - Preferir por driver_id + milestone_value
-- - Fallback por person_key + milestone_value
--
-- Status:
-- - 'paid': is_paid_effective = true
-- - 'pending': resto de casos
-- ============================================================================

CREATE OR REPLACE VIEW ops.v_yango_reconciliation_detail AS
WITH expected_payments AS (
    SELECT 
        pay_week_start_monday,
        pay_iso_year_week,
        payable_date,
        achieved_date,
        lead_date,
        lead_origin,
        payer,
        milestone_type,
        milestone_value,
        window_days,
        trips_in_window,
        person_key,
        driver_id,
        amount AS expected_amount,
        currency,
        created_at_export
    FROM ops.v_yango_receivable_payable_detail
),
paid_payments AS (
    SELECT 
        payment_key,
        latest_snapshot_at,
        source_pk AS paid_source_pk,
        pay_date AS paid_date,
        pay_time AS paid_time,
        raw_driver_name AS paid_raw_driver_name,
        driver_name_normalized AS paid_driver_name_normalized,
        milestone_value AS paid_milestone_value,
        is_paid,
        driver_id AS paid_driver_id,
        person_key AS paid_person_key,
        match_rule AS paid_match_rule,
        match_confidence AS paid_match_confidence,
        -- Columna derivada: is_paid_effective considera múltiples indicadores de pago
        (
            is_paid = true 
            OR payment_key IS NOT NULL
            OR pay_date IS NOT NULL
            OR latest_snapshot_at IS NOT NULL
            OR source_pk IS NOT NULL
        ) AS is_paid_effective
    FROM ops.v_yango_payments_ledger_latest
    WHERE (
        is_paid = true 
        OR payment_key IS NOT NULL
        OR pay_date IS NOT NULL
        OR latest_snapshot_at IS NOT NULL
        OR source_pk IS NOT NULL
    )
),
matched_expected_paid AS (
    -- Matching por driver_id + milestone_value (preferido)
    SELECT 
        e.*,
        p.payment_key,
        p.latest_snapshot_at,
        p.paid_source_pk,
        p.paid_date,
        p.paid_time,
        p.paid_raw_driver_name,
        p.paid_driver_name_normalized,
        p.is_paid AS paid_is_paid,
        p.is_paid_effective AS paid_is_paid_effective,
        p.paid_match_rule,
        p.paid_match_confidence,
        'driver_id_milestone' AS match_method
    FROM expected_payments e
    LEFT JOIN paid_payments p
        ON p.paid_driver_id = e.driver_id
        AND p.paid_milestone_value = e.milestone_value
        AND e.driver_id IS NOT NULL
),
matched_expected_paid_person AS (
    -- Fallback: matching por person_key + milestone_value (si no hay match por driver_id)
    SELECT 
        mep.*,
        COALESCE(
            mep.payment_key,
            p2.payment_key
        ) AS final_payment_key,
        COALESCE(
            mep.latest_snapshot_at,
            p2.latest_snapshot_at
        ) AS final_latest_snapshot_at,
        COALESCE(
            mep.paid_source_pk,
            p2.paid_source_pk
        ) AS final_paid_source_pk,
        COALESCE(
            mep.paid_date,
            p2.paid_date
        ) AS final_paid_date,
        COALESCE(
            mep.paid_time,
            p2.paid_time
        ) AS final_paid_time,
        COALESCE(
            mep.paid_raw_driver_name,
            p2.paid_raw_driver_name
        ) AS final_paid_raw_driver_name,
        COALESCE(
            mep.paid_driver_name_normalized,
            p2.paid_driver_name_normalized
        ) AS final_paid_driver_name_normalized,
        COALESCE(
            mep.paid_is_paid,
            p2.is_paid
        ) AS final_paid_is_paid,
        COALESCE(
            mep.paid_is_paid_effective,
            p2.is_paid_effective
        ) AS final_paid_is_paid_effective,
        COALESCE(
            mep.paid_match_rule,
            p2.paid_match_rule
        ) AS final_paid_match_rule,
        COALESCE(
            mep.paid_match_confidence,
            p2.paid_match_confidence
        ) AS final_paid_match_confidence,
        CASE 
            WHEN mep.payment_key IS NOT NULL THEN mep.match_method
            WHEN p2.payment_key IS NOT NULL THEN 'person_key_milestone'
            ELSE 'none'
        END AS final_match_method
    FROM matched_expected_paid mep
    LEFT JOIN paid_payments p2
        ON p2.paid_person_key = mep.person_key
        AND p2.paid_milestone_value = mep.milestone_value
        AND mep.person_key IS NOT NULL
        AND mep.payment_key IS NULL  -- Solo si no hay match por driver_id
),
expected_with_status AS (
    SELECT 
        mepp.*
    FROM matched_expected_paid_person mepp
),
paid_without_expected AS (
    -- Pagos reales que no tienen expected
    SELECT 
        p.payment_key,
        p.latest_snapshot_at,
        p.paid_source_pk,
        p.paid_date,
        p.paid_time,
        p.paid_raw_driver_name,
        p.paid_driver_name_normalized,
        p.paid_milestone_value AS milestone_value,
        p.is_paid AS paid_is_paid,
        p.is_paid_effective,
        p.paid_driver_id AS driver_id,
        p.paid_person_key AS person_key,
        p.paid_match_rule,
        p.paid_match_confidence,
        NULL::date AS pay_week_start_monday,
        NULL::text AS pay_iso_year_week,
        NULL::date AS payable_date,
        NULL::date AS achieved_date,
        NULL::date AS lead_date,
        NULL::text AS lead_origin,
        NULL::text AS payer,
        NULL::text AS milestone_type,
        NULL::integer AS window_days,
        NULL::integer AS trips_in_window,
        NULL::numeric AS expected_amount,
        NULL::text AS currency,
        NULL::timestamptz AS created_at_export,
        NULL::text AS final_payment_key,
        NULL::timestamptz AS final_latest_snapshot_at,
        NULL::text AS final_paid_source_pk,
        NULL::date AS final_paid_date,
        NULL::time AS final_paid_time,
        NULL::text AS final_paid_raw_driver_name,
        NULL::text AS final_paid_driver_name_normalized,
        NULL::boolean AS final_paid_is_paid,
        NULL::boolean AS final_paid_is_paid_effective,
        NULL::text AS final_paid_match_rule,
        NULL::text AS final_paid_match_confidence,
        NULL::text AS final_match_method
    FROM paid_payments p
    WHERE NOT EXISTS (
        SELECT 1
        FROM expected_payments e
        WHERE (
            (e.driver_id = p.paid_driver_id AND e.milestone_value = p.paid_milestone_value AND e.driver_id IS NOT NULL)
            OR (e.person_key = p.paid_person_key AND e.milestone_value = p.paid_milestone_value AND e.person_key IS NOT NULL)
        )
    )
)
-- Unión de expected con status y paid sin expected
SELECT 
    pay_week_start_monday,
    pay_iso_year_week,
    payable_date,
    achieved_date,
    lead_date,
    lead_origin,
    payer,
    milestone_type,
    milestone_value,
    window_days,
    trips_in_window,
    person_key,
    driver_id,
    expected_amount,
    currency,
    created_at_export,
    paid_payment_key,
    paid_snapshot_at,
    paid_source_pk,
    paid_date,
    paid_time,
    paid_raw_driver_name,
    paid_driver_name_normalized,
    paid_is_paid,
    is_paid_effective,
    paid_match_rule,
    paid_match_confidence,
    match_method,
    CASE
        WHEN is_paid_effective = true
        THEN 'paid'
        ELSE 'pending'
    END AS reconciliation_status,
    sort_date
FROM (
    SELECT 
        pay_week_start_monday,
        pay_iso_year_week,
        payable_date,
        achieved_date,
        lead_date,
        lead_origin,
        payer,
        milestone_type,
        milestone_value,
        window_days,
        trips_in_window,
        person_key,
        driver_id,
        expected_amount,
        currency,
        created_at_export,
        final_payment_key AS paid_payment_key,
        final_latest_snapshot_at AS paid_snapshot_at,
        final_paid_source_pk AS paid_source_pk,
        final_paid_date AS paid_date,
        final_paid_time AS paid_time,
        final_paid_raw_driver_name AS paid_raw_driver_name,
        final_paid_driver_name_normalized AS paid_driver_name_normalized,
        final_paid_is_paid AS paid_is_paid,
        final_paid_is_paid_effective AS is_paid_effective,
        final_paid_match_rule AS paid_match_rule,
        final_paid_match_confidence AS paid_match_confidence,
        final_match_method AS match_method,
        COALESCE(payable_date, final_paid_date) AS sort_date
    FROM expected_with_status

    UNION ALL

    SELECT 
        pay_week_start_monday,
        pay_iso_year_week,
        payable_date,
        achieved_date,
        lead_date,
        lead_origin,
        payer,
        milestone_type,
        milestone_value,
        window_days,
        trips_in_window,
        person_key,
        driver_id,
        expected_amount,
        currency,
        created_at_export,
        payment_key AS paid_payment_key,
        latest_snapshot_at AS paid_snapshot_at,
        paid_source_pk,
        paid_date,
        paid_time,
        paid_raw_driver_name,
        paid_driver_name_normalized,
        paid_is_paid,
        is_paid_effective,
        paid_match_rule,
        paid_match_confidence,
        'none' AS match_method,
        COALESCE(payable_date, paid_date) AS sort_date
    FROM paid_without_expected
) t
ORDER BY 
    pay_week_start_monday DESC,
    sort_date DESC;

COMMENT ON VIEW ops.v_yango_reconciliation_detail IS 
'Vista detalle de reconciliación Yango que compara expected (ops.v_yango_receivable_payable_detail) vs paid (ops.v_yango_payments_ledger_latest). Matching preferido por driver_id+milestone_value, fallback por person_key+milestone_value. Status: paid (is_paid_effective=true), pending (resto de casos).';

COMMENT ON COLUMN ops.v_yango_reconciliation_detail.reconciliation_status IS 
'Estado de reconciliación: paid (is_paid_effective=true), pending (resto de casos).';

COMMENT ON COLUMN ops.v_yango_reconciliation_detail.is_paid_effective IS 
'Indicador efectivo de pago: true si is_paid=true OR paid_payment_key IS NOT NULL OR paid_date IS NOT NULL OR paid_snapshot_at IS NOT NULL OR paid_source_pk IS NOT NULL. Usado para reconciliation_status.';

-- ============================================================================
-- Validación automática: Conteo por reconciliation_status
-- ============================================================================
SELECT reconciliation_status, COUNT(*)
FROM ops.v_yango_reconciliation_detail
GROUP BY 1
ORDER BY 1;
