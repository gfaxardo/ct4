-- ============================================================================
-- Vista: ops.v_payments_driver_matrix_ct4
-- ============================================================================
-- PROPÓSITO:
-- Vista de PRESENTACIÓN que muestra 1 fila por driver con columnas por milestones
-- M1/M5/M25 y estados Yango/Scout. Similar a v_payments_driver_matrix_cabinet
-- pero usa achieved determinístico basado en viajes (summary_daily) en lugar de
-- achieved legacy basado en reglas/ventanas/lead_date.
--
-- DIFERENCIAS CLAVE vs v_payments_driver_matrix_cabinet:
-- - Achieved flags/dates vienen de ops.v_ct4_driver_achieved_from_trips (determinístico)
-- - Garantiza consistencia: si M5=true, entonces M1=true (por diseño de fuente)
-- - No permite inconsistencias M5 sin M1, M25 sin M5/M1
-- - achieved_source = 'TRIPS_CT4' para señalización
--
-- CAPA: C2 - Elegibilidad (ACHIEVED) - Versión Determinística CT4
-- ============================================================================
-- GRANO:
-- 1 fila por driver_id (agregación por driver_id)
-- ============================================================================
-- FUENTES (Dependencias):
-- - ops.v_ct4_driver_achieved_from_trips: achieved determinístico (flags y dates)
-- - ops.v_claims_payment_status_cabinet: expected_amount, paid_flag, payment_status
-- - ops.v_yango_cabinet_claims_for_collection: yango_payment_status
-- - ops.v_yango_payments_claims_cabinet_14d: window_status
-- - public.drivers: driver_name
-- - ops.v_ct4_eligible_drivers: origin_tag, person_key, identity_status
-- ============================================================================
-- COLUMNAS CLAVE:
-- - driver_id, person_key, driver_name, lead_date, week_start, origin_tag
-- - Milestones: m1_*, m5_*, m25_* (achieved_flag, achieved_date, expected_amount_yango,
--   yango_payment_status, window_status, overdue_days)
-- - Scout: scout_due_flag, scout_paid_flag, scout_amount
-- - achieved_source: 'TRIPS_CT4' (señalización)
-- - legacy_inconsistency_flag: true si legacy tenía M5 sin M1 (opcional)
-- ============================================================================
-- NOTA IMPORTANTE:
-- Esta vista garantiza consistencia de milestones: si M5=true, entonces M1=true.
-- No permite inconsistencias porque la fuente (v_ct4_driver_achieved_from_trips)
-- calcula achieved determinísticamente desde summary_daily.
-- ============================================================================

CREATE OR REPLACE VIEW ops.v_payments_driver_matrix_ct4 AS
WITH achieved_from_trips AS (
    -- Achieved determinístico desde vista pivot
    SELECT 
        driver_id,
        origin_tag,
        person_key,
        identity_status,
        m1_achieved_flag,
        m1_achieved_date,
        m5_achieved_flag,
        m5_achieved_date,
        m25_achieved_flag,
        m25_achieved_date
    FROM ops.v_ct4_driver_achieved_from_trips
),
base_claims AS (
    -- Claims para obtener expected_amount, paid_flag, payment_status
    SELECT 
        c.driver_id,
        c.milestone_value,
        c.expected_amount,
        c.paid_flag,
        c.paid_date,
        c.days_overdue,
        c.payment_status,
        c.reason_code,
        c.lead_date
    FROM ops.v_claims_payment_status_cabinet c
    WHERE c.milestone_value IN (1, 5, 25)
),
yango_status AS (
    -- Yango payment status
    SELECT 
        y.driver_id,
        y.milestone_value,
        y.yango_payment_status,
        y.driver_name,
        y.lead_date
    FROM ops.v_yango_cabinet_claims_for_collection y
    WHERE y.milestone_value IN (1, 5, 25)
),
window_status_data AS (
    -- Window status
    SELECT 
        w.driver_id,
        w.milestone_value,
        CASE 
            WHEN w.window_status = 'active' THEN 'in_window'
            WHEN w.window_status = 'expired' THEN 'expired'
            ELSE w.window_status
        END AS window_status,
        w.lead_date
    FROM ops.v_yango_payments_claims_cabinet_14d w
    WHERE w.milestone_value IN (1, 5, 25)
),
driver_info AS (
    -- Driver name
    SELECT 
        d.driver_id,
        d.full_name AS driver_name
    FROM public.drivers d
),
legacy_inconsistencies AS (
    -- Detectar inconsistencias en legacy para señalización
    SELECT 
        dm.driver_id,
        (dm.m5_achieved_flag = true AND COALESCE(dm.m1_achieved_flag, false) = false)
            OR (dm.m25_achieved_flag = true AND COALESCE(dm.m5_achieved_flag, false) = false)
            AS legacy_inconsistency_flag
    FROM ops.v_payments_driver_matrix_cabinet dm
    WHERE dm.origin_tag IN ('cabinet', 'fleet_migration')
),
driver_milestones AS (
    -- Agregar por driver_id combinando achieved determinístico con claims/pagos
    SELECT 
        a.driver_id,
        a.person_key,
        a.origin_tag,
        MAX(di.driver_name) AS driver_name,
        -- lead_date: usar la más temprana entre achieved dates o claims
        LEAST(
            COALESCE(a.m1_achieved_date, a.m5_achieved_date, a.m25_achieved_date),
            MIN(bc.lead_date)
        ) AS lead_date,
        -- week_start: lunes de la semana de lead_date
        DATE_TRUNC('week', LEAST(
            COALESCE(a.m1_achieved_date, a.m5_achieved_date, a.m25_achieved_date),
            MIN(bc.lead_date)
        ))::date AS week_start,
        -- connected_flag y connected_date (TODO: implementar cuando exista fuente)
        false AS connected_flag,
        NULL::date AS connected_date,
        -- Milestone M1 (achieved desde trips determinístico)
        a.m1_achieved_flag,
        a.m1_achieved_date,
        MAX(CASE WHEN bc.milestone_value = 1 THEN bc.expected_amount END) AS m1_expected_amount_yango,
        MAX(CASE WHEN bc.milestone_value = 1 THEN ys.yango_payment_status END) AS m1_yango_payment_status,
        MAX(CASE WHEN bc.milestone_value = 1 THEN ws.window_status END) AS m1_window_status,
        MAX(CASE WHEN bc.milestone_value = 1 THEN bc.days_overdue END) AS m1_overdue_days,
        -- Milestone M5 (achieved desde trips determinístico)
        a.m5_achieved_flag,
        a.m5_achieved_date,
        MAX(CASE WHEN bc.milestone_value = 5 THEN bc.expected_amount END) AS m5_expected_amount_yango,
        MAX(CASE WHEN bc.milestone_value = 5 THEN ys.yango_payment_status END) AS m5_yango_payment_status,
        MAX(CASE WHEN bc.milestone_value = 5 THEN ws.window_status END) AS m5_window_status,
        MAX(CASE WHEN bc.milestone_value = 5 THEN bc.days_overdue END) AS m5_overdue_days,
        -- Milestone M25 (achieved desde trips determinístico)
        a.m25_achieved_flag,
        a.m25_achieved_date,
        MAX(CASE WHEN bc.milestone_value = 25 THEN bc.expected_amount END) AS m25_expected_amount_yango,
        MAX(CASE WHEN bc.milestone_value = 25 THEN ys.yango_payment_status END) AS m25_yango_payment_status,
        MAX(CASE WHEN bc.milestone_value = 25 THEN ws.window_status END) AS m25_window_status,
        MAX(CASE WHEN bc.milestone_value = 25 THEN bc.days_overdue END) AS m25_overdue_days,
        -- Scout (TODO: implementar cuando exista fuente)
        NULL::boolean AS scout_due_flag,
        NULL::boolean AS scout_paid_flag,
        NULL::numeric(12,2) AS scout_amount,
        -- Señalización
        'TRIPS_CT4' AS achieved_source,
        COALESCE(li.legacy_inconsistency_flag, false) AS legacy_inconsistency_flag
    FROM achieved_from_trips a
    LEFT JOIN base_claims bc ON bc.driver_id = a.driver_id
    LEFT JOIN yango_status ys 
        ON ys.driver_id = a.driver_id 
        AND ys.milestone_value = bc.milestone_value
    LEFT JOIN window_status_data ws 
        ON ws.driver_id = a.driver_id 
        AND ws.milestone_value = bc.milestone_value
    LEFT JOIN driver_info di ON di.driver_id = a.driver_id
    LEFT JOIN legacy_inconsistencies li ON li.driver_id = a.driver_id
    GROUP BY 
        a.driver_id, 
        a.person_key, 
        a.origin_tag,
        a.m1_achieved_flag,
        a.m1_achieved_date,
        a.m5_achieved_flag,
        a.m5_achieved_date,
        a.m25_achieved_flag,
        a.m25_achieved_date,
        li.legacy_inconsistency_flag
)
SELECT 
    driver_id,
    person_key,
    driver_name,
    lead_date,
    week_start,
    origin_tag,
    connected_flag,
    connected_date,
    -- Milestone M1
    m1_achieved_flag,
    m1_achieved_date,
    m1_expected_amount_yango,
    m1_yango_payment_status,
    m1_window_status,
    m1_overdue_days,
    -- Milestone M5
    m5_achieved_flag,
    m5_achieved_date,
    m5_expected_amount_yango,
    m5_yango_payment_status,
    m5_window_status,
    m5_overdue_days,
    -- Milestone M25
    m25_achieved_flag,
    m25_achieved_date,
    m25_expected_amount_yango,
    m25_yango_payment_status,
    m25_window_status,
    m25_overdue_days,
    -- Scout
    scout_due_flag,
    scout_paid_flag,
    scout_amount,
    -- Señalización
    achieved_source,
    legacy_inconsistency_flag
FROM driver_milestones;

-- ============================================================================
-- Comentarios
-- ============================================================================
COMMENT ON VIEW ops.v_payments_driver_matrix_ct4 IS 
'Vista de PRESENTACIÓN que muestra 1 fila por driver con columnas por milestones M1/M5/M25 y estados Yango/Scout. Similar a v_payments_driver_matrix_cabinet pero usa achieved determinístico basado en viajes (summary_daily) en lugar de achieved legacy. Garantiza consistencia: si M5=true, entonces M1=true. Grano: driver_id (1 fila por driver_id).';

COMMENT ON COLUMN ops.v_payments_driver_matrix_ct4.driver_id IS 
'ID del conductor. Grano principal de la vista (1 fila por driver_id).';

COMMENT ON COLUMN ops.v_payments_driver_matrix_ct4.person_key IS 
'Person key del conductor (identidad canónica). Fuente: ops.v_ct4_driver_achieved_from_trips.';

COMMENT ON COLUMN ops.v_payments_driver_matrix_ct4.driver_name IS 
'Nombre del conductor desde public.drivers.full_name. Puede ser NULL si no existe.';

COMMENT ON COLUMN ops.v_payments_driver_matrix_ct4.lead_date IS 
'Fecha más temprana entre achieved dates (desde trips) o lead_date de claims.';

COMMENT ON COLUMN ops.v_payments_driver_matrix_ct4.week_start IS 
'Lunes de la semana de lead_date. Calculado como DATE_TRUNC(''week'', lead_date)::date.';

COMMENT ON COLUMN ops.v_payments_driver_matrix_ct4.origin_tag IS 
'Origen del lead: ''cabinet'' o ''fleet_migration''. Fuente: ops.v_ct4_driver_achieved_from_trips.';

COMMENT ON COLUMN ops.v_payments_driver_matrix_ct4.m1_achieved_flag IS 
'Flag indicando si el driver alcanzó M1. Fuente: ops.v_ct4_driver_achieved_from_trips (determinístico desde summary_daily).';

COMMENT ON COLUMN ops.v_payments_driver_matrix_ct4.m1_achieved_date IS 
'Fecha en que el driver alcanzó M1 según summary_daily (primer día con trips >= 1). Fuente: ops.v_ct4_driver_achieved_from_trips.';

COMMENT ON COLUMN ops.v_payments_driver_matrix_ct4.m5_achieved_flag IS 
'Flag indicando si el driver alcanzó M5. Fuente: ops.v_ct4_driver_achieved_from_trips (determinístico desde summary_daily). Garantiza: si M5=true, entonces M1=true.';

COMMENT ON COLUMN ops.v_payments_driver_matrix_ct4.m5_achieved_date IS 
'Fecha en que el driver alcanzó M5 según summary_daily (primer día con trips >= 5). Fuente: ops.v_ct4_driver_achieved_from_trips.';

COMMENT ON COLUMN ops.v_payments_driver_matrix_ct4.m25_achieved_flag IS 
'Flag indicando si el driver alcanzó M25. Fuente: ops.v_ct4_driver_achieved_from_trips (determinístico desde summary_daily). Garantiza: si M25=true, entonces M5=true y M1=true.';

COMMENT ON COLUMN ops.v_payments_driver_matrix_ct4.m25_achieved_date IS 
'Fecha en que el driver alcanzó M25 según summary_daily (primer día con trips >= 25). Fuente: ops.v_ct4_driver_achieved_from_trips.';

COMMENT ON COLUMN ops.v_payments_driver_matrix_ct4.achieved_source IS 
'Fuente de achieved: siempre ''TRIPS_CT4'' para señalización en frontend. Indica que achieved viene de cálculo determinístico basado en viajes.';

COMMENT ON COLUMN ops.v_payments_driver_matrix_ct4.legacy_inconsistency_flag IS 
'Flag indicando si el driver tenía inconsistencias en legacy (v_payments_driver_matrix_cabinet): M5 sin M1 o M25 sin M5. TRUE si legacy tenía inconsistencia, FALSE o NULL si no.';




