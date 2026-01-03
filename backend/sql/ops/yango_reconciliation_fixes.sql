-- ============================================================================
-- Fixes para Conciliación de Pagos Yango
-- ============================================================================
-- Este script corrige:
-- 1. Naming: crea alias VIEW ops.yango_payment_ledger
-- 2. Corrige pay_week_start_monday NULL en paid-only items
-- 3. Mejora columnas para UI (expected_exists, paid_exists)
-- 4. Crea vistas UI-friendly (summary_ui, items_ui)
-- ============================================================================

-- ============================================================================
-- 1. NAMING FIX: Crear alias VIEW para ops.yango_payment_ledger
-- ============================================================================
CREATE OR REPLACE VIEW ops.yango_payment_ledger AS
SELECT * FROM ops.yango_payment_status_ledger;

COMMENT ON VIEW ops.yango_payment_ledger IS 
'Alias VIEW para ops.yango_payment_status_ledger. Mantiene compatibilidad con código que referencia ops.yango_payment_ledger.';

-- ============================================================================
-- 2. CORREGIR ops.v_yango_reconciliation_detail
-- ============================================================================
-- Cambios:
-- - Calcular pay_week_start_monday desde pay_date si no hay expected
-- - sort_date = COALESCE(payable_date, paid_date, pay_date)
-- - Agregar expected_exists y paid_exists para UI
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
        match_confidence AS paid_match_confidence
    FROM ops.v_yango_payments_ledger_latest
    WHERE is_paid = true
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
        mepp.*,
        CASE 
            WHEN mepp.final_paid_is_paid = true THEN 'paid'
            WHEN mepp.final_paid_is_paid = false OR mepp.final_payment_key IS NULL THEN 'pending'
            ELSE 'pending'
        END AS reconciliation_status
    FROM matched_expected_paid_person mepp
),
paid_without_expected AS (
    -- Pagos reales que no tienen expected
    -- IMPORTANTE: calcular pay_week_start_monday desde pay_date
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
        p.paid_driver_id AS driver_id,
        p.paid_person_key AS person_key,
        p.paid_match_rule,
        p.paid_match_confidence,
        'anomaly_paid_without_expected' AS reconciliation_status,
        -- Calcular pay_week_start_monday desde pay_date (lunes de la semana)
        date_trunc('week', p.paid_date)::date AS pay_week_start_monday,
        to_char(p.paid_date, 'IYYY-IW') AS pay_iso_year_week,
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
    paid_match_rule,
    paid_match_confidence,
    match_method,
    reconciliation_status,
    sort_date,
    -- Columnas para UI
    (expected_amount IS NOT NULL) AS expected_exists,
    (paid_is_paid = true OR paid_payment_key IS NOT NULL) AS paid_exists
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
        final_paid_match_rule AS paid_match_rule,
        final_paid_match_confidence AS paid_match_confidence,
        final_match_method AS match_method,
        reconciliation_status,
        -- sort_date: COALESCE(payable_date, paid_date, pay_date)
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
        paid_match_rule,
        paid_match_confidence,
        'none' AS match_method,
        reconciliation_status,
        -- sort_date: COALESCE(payable_date, paid_date, pay_date)
        COALESCE(payable_date, paid_date) AS sort_date
    FROM paid_without_expected
) t
ORDER BY 
    pay_week_start_monday DESC,
    sort_date DESC;

COMMENT ON VIEW ops.v_yango_reconciliation_detail IS 
'Vista detalle de reconciliación Yango que compara expected (ops.v_yango_receivable_payable_detail) vs paid (ops.v_yango_payments_ledger_latest). Matching preferido por driver_id+milestone_value, fallback por person_key+milestone_value. Status: paid (expected existe y paid=true), pending (expected existe pero no paid o paid=false), anomaly_paid_without_expected (paid=true pero no expected). Ahora calcula pay_week_start_monday desde pay_date para paid-only items.';

COMMENT ON COLUMN ops.v_yango_reconciliation_detail.reconciliation_status IS 
'Estado de reconciliación: paid (coincide expected y paid), pending (expected sin paid), anomaly_paid_without_expected (paid sin expected).';

COMMENT ON COLUMN ops.v_yango_reconciliation_detail.expected_exists IS 
'Indica si existe expected_amount (true) o no (false). Útil para UI.';

COMMENT ON COLUMN ops.v_yango_reconciliation_detail.paid_exists IS 
'Indica si existe pago real (paid_is_paid=true o paid_payment_key IS NOT NULL). Útil para UI.';

-- ============================================================================
-- 3. VISTA UI-FRIENDLY: Resumen Agregado
-- ============================================================================

CREATE OR REPLACE VIEW ops.v_yango_reconciliation_summary_ui AS
SELECT 
    pay_week_start_monday,
    milestone_value,
    reconciliation_status,
    COUNT(*) AS rows_count,
    SUM(expected_amount) FILTER (WHERE expected_amount IS NOT NULL) AS amount_expected_sum,
    -- amount_paid_sum: suma de expected_amount donde paid_is_paid = true
    SUM(expected_amount) FILTER (WHERE paid_is_paid = true AND expected_amount IS NOT NULL) AS amount_paid_sum,
    -- amount_diff: diferencia entre expected y paid
    SUM(expected_amount) FILTER (WHERE expected_amount IS NOT NULL) 
        - SUM(expected_amount) FILTER (WHERE paid_is_paid = true AND expected_amount IS NOT NULL) AS amount_diff,
    COUNT(*) FILTER (WHERE expected_exists = true) AS count_expected,
    COUNT(*) FILTER (WHERE paid_exists = true) AS count_paid,
    COUNT(DISTINCT driver_id) FILTER (WHERE driver_id IS NOT NULL) AS count_drivers
FROM ops.v_yango_reconciliation_detail
WHERE pay_week_start_monday IS NOT NULL
GROUP BY 
    pay_week_start_monday,
    milestone_value,
    reconciliation_status
ORDER BY 
    pay_week_start_monday DESC,
    milestone_value,
    reconciliation_status;

COMMENT ON VIEW ops.v_yango_reconciliation_summary_ui IS 
'Vista agregada semanal UI-friendly de reconciliación Yango. Agrupa por semana, milestone_value y reconciliation_status. Proporciona métricas limpias para UI: rows_count, amount_expected_sum, amount_paid_sum, amount_diff.';

COMMENT ON COLUMN ops.v_yango_reconciliation_summary_ui.amount_expected_sum IS 
'Suma de montos expected (solo donde expected_amount IS NOT NULL).';

COMMENT ON COLUMN ops.v_yango_reconciliation_summary_ui.amount_paid_sum IS 
'Suma de montos expected donde paid_is_paid = true (montos que fueron pagados).';

COMMENT ON COLUMN ops.v_yango_reconciliation_summary_ui.amount_diff IS 
'Diferencia entre expected y paid: amount_expected_sum - amount_paid_sum. Positivo indica pendiente, negativo indica sobrepago.';

-- ============================================================================
-- 4. VISTA UI-FRIENDLY: Items Detallados
-- ============================================================================

CREATE OR REPLACE VIEW ops.v_yango_reconciliation_items_ui AS
SELECT 
    pay_week_start_monday,
    paid_raw_driver_name,
    milestone_value,
    expected_amount,
    paid_is_paid,
    reconciliation_status,
    -- Campos adicionales útiles para UI
    payable_date,
    paid_date,
    driver_id,
    person_key,
    expected_exists,
    paid_exists
FROM ops.v_yango_reconciliation_detail
WHERE pay_week_start_monday IS NOT NULL
ORDER BY 
    pay_week_start_monday DESC,
    COALESCE(payable_date, paid_date) DESC,
    milestone_value,
    reconciliation_status;

COMMENT ON VIEW ops.v_yango_reconciliation_items_ui IS 
'Vista detalle UI-friendly de items de reconciliación Yango. Proporciona columnas limpias para tabla del frontend: pay_week_start_monday, paid_raw_driver_name, milestone_value, expected_amount, paid_is_paid, reconciliation_status.';

COMMENT ON COLUMN ops.v_yango_reconciliation_items_ui.paid_raw_driver_name IS 
'Nombre del driver desde el pago real (raw, sin normalizar).';

COMMENT ON COLUMN ops.v_yango_reconciliation_items_ui.expected_exists IS 
'Indica si existe expected_amount (true) o no (false).';

COMMENT ON COLUMN ops.v_yango_reconciliation_items_ui.paid_exists IS 
'Indica si existe pago real (paid_is_paid=true o paid_payment_key IS NOT NULL).';

-- ============================================================================
-- VALIDACIONES
-- ============================================================================

-- Validación 1: Count de ledger (alias y tabla)
-- SELECT 
--     (SELECT COUNT(*) FROM ops.yango_payment_status_ledger) AS count_ledger_table,
--     (SELECT COUNT(*) FROM ops.yango_payment_ledger) AS count_ledger_alias;

-- Validación 2: Top 50 de ops.v_yango_reconciliation_detail con week NOT NULL
-- SELECT 
--     pay_week_start_monday,
--     payable_date,
--     paid_date,
--     sort_date,
--     reconciliation_status,
--     expected_amount,
--     paid_is_paid,
--     paid_raw_driver_name,
--     milestone_value
-- FROM ops.v_yango_reconciliation_detail
-- WHERE pay_week_start_monday IS NOT NULL
-- ORDER BY pay_week_start_monday DESC, sort_date DESC
-- LIMIT 50;

-- Validación 3: Conteo por reconciliation_status
-- SELECT 
--     reconciliation_status,
--     COUNT(*) AS count_items,
--     COUNT(*) FILTER (WHERE pay_week_start_monday IS NOT NULL) AS count_with_week,
--     COUNT(*) FILTER (WHERE pay_week_start_monday IS NULL) AS count_without_week
-- FROM ops.v_yango_reconciliation_detail
-- GROUP BY reconciliation_status
-- ORDER BY reconciliation_status;

-- Validación 4: Conteo semanal en summary_ui
-- SELECT 
--     pay_week_start_monday,
--     milestone_value,
--     reconciliation_status,
--     rows_count,
--     amount_expected_sum,
--     amount_paid_sum,
--     amount_diff,
--     count_expected,
--     count_paid,
--     count_drivers
-- FROM ops.v_yango_reconciliation_summary_ui
-- ORDER BY pay_week_start_monday DESC, milestone_value, reconciliation_status
-- LIMIT 100;



















