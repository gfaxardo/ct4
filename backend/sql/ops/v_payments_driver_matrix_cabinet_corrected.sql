-- ============================================================================
-- Vista: ops.v_payments_driver_matrix_cabinet
-- ============================================================================
-- Vista de PRESENTACIÓN (no recalcula reglas) que muestra 1 fila por driver
-- con columnas por milestones M1/M5/M25 y estados Yango/Scout.
-- ============================================================================

DROP VIEW IF EXISTS ops.v_payments_driver_matrix_cabinet CASCADE;

CREATE VIEW ops.v_payments_driver_matrix_cabinet AS
WITH base_claims AS (
    -- Base: claims por driver y milestone desde v_claims_payment_status_cabinet
    SELECT 
        c.driver_id,
        c.person_key,
        c.lead_date,
        c.milestone_value,
        c.expected_amount,
        c.paid_flag,
        c.paid_date,
        c.days_overdue,
        c.payment_status,
        c.reason_code
    FROM ops.v_claims_payment_status_cabinet c
    WHERE c.milestone_value IN (1, 5, 25)
),
-- Enriquecer con yango_payment_status desde v_yango_cabinet_claims_for_collection
yango_status AS (
    SELECT 
        y.driver_id,
        y.milestone_value,
        y.yango_payment_status,
        y.driver_name,
        y.lead_date
    FROM ops.v_yango_cabinet_claims_for_collection y
    WHERE y.milestone_value IN (1, 5, 25)
),
-- Enriquecer con window_status desde v_yango_payments_claims_cabinet_14d
-- Mapear 'active' a 'in_window' para cumplir con requerimiento
window_status_data AS (
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
-- Obtener origin_tag y connected_date
-- Usa v_payment_calculation como fuente principal
origin_and_connected_data AS (
    SELECT DISTINCT ON (driver_id, person_key)
        pc.driver_id,
        pc.person_key,
        pc.origin_tag,
        NULL::date AS connected_date,  -- TODO: Obtener desde v_conversion_metrics si es necesario
        pc.lead_date
    FROM ops.v_payment_calculation pc
    WHERE pc.origin_tag IN ('cabinet', 'fleet_migration')
        AND pc.driver_id IS NOT NULL
    ORDER BY pc.driver_id, pc.person_key, pc.lead_date DESC
),
-- Obtener driver_name desde public.drivers
driver_info AS (
    SELECT 
        d.driver_id,
        d.full_name AS driver_name
    FROM public.drivers d
),
-- Agregar por driver_id pivotando milestones
driver_milestones AS (
    SELECT 
        bc.driver_id,
        -- person_key (UUID): usar array_agg en lugar de MAX
        (array_agg(bc.person_key ORDER BY bc.lead_date DESC NULLS LAST))[1] AS person_key,
        -- Información base del driver
        MAX(di.driver_name) AS driver_name,
        MIN(bc.lead_date) AS lead_date,  -- Primera lead_date entre todos los milestones
        MAX(ocd.origin_tag) AS origin_tag,
        -- connected_flag y connected_date
        -- TODO: Implementar cuando exista fuente confiable de first_connection_date
        false AS connected_flag,
        NULL::date AS connected_date,
        -- week_start: lunes de la semana de lead_date
        DATE_TRUNC('week', MIN(bc.lead_date))::date AS week_start,
        -- Milestone M1 (milestone_value = 1)
        -- Flags booleanos: usar BOOL_OR en lugar de MAX(CASE ... THEN true ELSE false END)
        BOOL_OR(bc.milestone_value = 1) AS m1_achieved_flag,
        MAX(CASE WHEN bc.milestone_value = 1 THEN bc.lead_date END) AS m1_achieved_date,
        MAX(CASE WHEN bc.milestone_value = 1 THEN bc.expected_amount END) AS m1_expected_amount_yango,
        MAX(CASE WHEN bc.milestone_value = 1 THEN ys.yango_payment_status END) AS m1_yango_payment_status,
        MAX(CASE WHEN bc.milestone_value = 1 THEN ws.window_status END) AS m1_window_status,
        MAX(CASE WHEN bc.milestone_value = 1 THEN bc.days_overdue END) AS m1_overdue_days,
        -- Milestone M5 (milestone_value = 5)
        BOOL_OR(bc.milestone_value = 5) AS m5_achieved_flag,
        MAX(CASE WHEN bc.milestone_value = 5 THEN bc.lead_date END) AS m5_achieved_date,
        MAX(CASE WHEN bc.milestone_value = 5 THEN bc.expected_amount END) AS m5_expected_amount_yango,
        MAX(CASE WHEN bc.milestone_value = 5 THEN ys.yango_payment_status END) AS m5_yango_payment_status,
        MAX(CASE WHEN bc.milestone_value = 5 THEN ws.window_status END) AS m5_window_status,
        MAX(CASE WHEN bc.milestone_value = 5 THEN bc.days_overdue END) AS m5_overdue_days,
        -- Milestone M25 (milestone_value = 25)
        BOOL_OR(bc.milestone_value = 25) AS m25_achieved_flag,
        MAX(CASE WHEN bc.milestone_value = 25 THEN bc.lead_date END) AS m25_achieved_date,
        MAX(CASE WHEN bc.milestone_value = 25 THEN bc.expected_amount END) AS m25_expected_amount_yango,
        MAX(CASE WHEN bc.milestone_value = 25 THEN ys.yango_payment_status END) AS m25_yango_payment_status,
        MAX(CASE WHEN bc.milestone_value = 25 THEN ws.window_status END) AS m25_window_status,
        MAX(CASE WHEN bc.milestone_value = 25 THEN bc.days_overdue END) AS m25_overdue_days,
        -- TODO: Scout - dejar NULLs por ahora
        NULL::boolean AS scout_due_flag,
        NULL::boolean AS scout_paid_flag,
        NULL::numeric(12,2) AS scout_amount
    FROM base_claims bc
    LEFT JOIN yango_status ys 
        ON ys.driver_id = bc.driver_id 
        AND ys.milestone_value = bc.milestone_value
    LEFT JOIN window_status_data ws 
        ON ws.driver_id = bc.driver_id 
        AND ws.milestone_value = bc.milestone_value
    LEFT JOIN origin_and_connected_data ocd 
        ON ocd.driver_id = bc.driver_id
        AND (ocd.person_key = bc.person_key OR (ocd.person_key IS NULL AND bc.person_key IS NULL))
    LEFT JOIN driver_info di 
        ON di.driver_id = bc.driver_id
    GROUP BY bc.driver_id
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
    -- TODO: Scout - campos NULLs por ahora
    scout_due_flag,
    scout_paid_flag,
    scout_amount
FROM driver_milestones;

