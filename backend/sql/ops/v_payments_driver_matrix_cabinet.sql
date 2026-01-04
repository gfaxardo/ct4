-- ============================================================================
-- Vista: ops.v_payments_driver_matrix_cabinet
-- ============================================================================
-- PROPÓSITO:
-- Vista de PRESENTACIÓN (no recalcula reglas) que muestra 1 fila por driver
-- con columnas por milestones M1/M5/M25 y estados Yango/Scout. Diseñada para
-- visualización en dashboards y reportes operativos.
-- ============================================================================
-- GRANO:
-- 1 fila por driver_id (agregación por GROUP BY bc.driver_id)
-- ============================================================================
-- FUENTES (Dependencias):
-- - ops.v_claims_payment_status_cabinet: claims base con milestones
-- - ops.v_yango_cabinet_claims_for_collection: yango_payment_status
-- - ops.v_yango_payments_claims_cabinet_14d: window_status
-- - public.drivers: driver_name
-- - ops.v_payment_calculation: origin_tag
-- ============================================================================
-- COLUMNAS CLAVE:
-- - driver_id, person_key, driver_name, lead_date, week_start, origin_tag
-- - Milestones: m1_*, m5_*, m25_* (achieved_flag, achieved_date, expected_amount_yango,
--   yango_payment_status, window_status, overdue_days)
-- - Scout: scout_due_flag, scout_paid_flag, scout_amount
-- - Flags de inconsistencia: m5_without_m1_flag, m25_without_m5_flag, milestone_inconsistency_notes
-- ============================================================================
-- NOTA IMPORTANTE:
-- Milestones superiores pueden existir sin evidencia del milestone anterior en claims.
-- Esto es esperado y se marca con flags de inconsistencia (m5_without_m1_flag, etc.).
-- No se inventan datos: si M1 no existe en claims, m1_* será NULL aunque M5 exista.
-- ============================================================================

CREATE OR REPLACE VIEW ops.v_payments_driver_matrix_cabinet AS
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
        -- first_connection_date puede venir de v_conversion_metrics si está disponible
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
        -- person_key: seleccionar el del milestone más reciente (mejor que MAX arbitrario)
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
        -- Usar BOOL_OR para flags booleanos (más eficiente y semánticamente correcto)
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
        -- Fuente potencial: ops.scout_payment_rules + ops.v_scout_liquidation_paid_items
        NULL::boolean AS scout_due_flag,
        NULL::boolean AS scout_paid_flag,
        NULL::numeric(12,2) AS scout_amount,
        -- Flags de inconsistencia de milestones
        -- M5 sin M1: M5 tiene achieved_flag pero M1 no tiene achieved_flag
        (BOOL_OR(bc.milestone_value = 5) = true
         AND COALESCE(BOOL_OR(bc.milestone_value = 1), false) = false) AS m5_without_m1_flag,
        -- M25 sin M5: M25 tiene achieved_flag pero M5 no tiene achieved_flag
        (BOOL_OR(bc.milestone_value = 25) = true
         AND COALESCE(BOOL_OR(bc.milestone_value = 5), false) = false) AS m25_without_m5_flag,
        -- Notas de inconsistencia (texto corto)
        CASE 
            WHEN (BOOL_OR(bc.milestone_value = 5) = true
                  AND COALESCE(BOOL_OR(bc.milestone_value = 1), false) = false)
                 AND (BOOL_OR(bc.milestone_value = 25) = true
                      AND COALESCE(BOOL_OR(bc.milestone_value = 5), false) = false)
            THEN 'M5 sin M1, M25 sin M5'
            WHEN (BOOL_OR(bc.milestone_value = 5) = true
                  AND COALESCE(BOOL_OR(bc.milestone_value = 1), false) = false)
            THEN 'M5 sin M1'
            WHEN (BOOL_OR(bc.milestone_value = 25) = true
                  AND COALESCE(BOOL_OR(bc.milestone_value = 5), false) = false)
            THEN 'M25 sin M5'
            ELSE NULL
        END AS milestone_inconsistency_notes
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
    -- Scout
    scout_due_flag,
    scout_paid_flag,
    scout_amount,
    -- Flags de inconsistencia de milestones
    m5_without_m1_flag,
    m25_without_m5_flag,
    milestone_inconsistency_notes
FROM driver_milestones;

-- ============================================================================
-- Comentarios de la Vista
-- ============================================================================
COMMENT ON VIEW ops.v_payments_driver_matrix_cabinet IS 
'Vista de PRESENTACIÓN (no recalcula reglas) que muestra 1 fila por driver con columnas por milestones M1/M5/M25 y estados Yango/Scout. Diseñada para visualización en dashboards y reportes operativos. Grano: driver_id (1 fila por driver_id).';

COMMENT ON COLUMN ops.v_payments_driver_matrix_cabinet.driver_id IS 
'ID del conductor. Grano principal de la vista (1 fila por driver_id).';

COMMENT ON COLUMN ops.v_payments_driver_matrix_cabinet.person_key IS 
'Person key del conductor (identidad canónica). Seleccionado del milestone más reciente. Puede ser NULL si no existe.';

COMMENT ON COLUMN ops.v_payments_driver_matrix_cabinet.driver_name IS 
'Nombre del conductor desde public.drivers.full_name. Puede ser NULL si no existe en la tabla drivers.';

COMMENT ON COLUMN ops.v_payments_driver_matrix_cabinet.lead_date IS 
'Primera fecha de lead_date entre todos los milestones del driver. Fuente: ops.v_claims_payment_status_cabinet.lead_date.';

COMMENT ON COLUMN ops.v_payments_driver_matrix_cabinet.week_start IS 
'Lunes de la semana de lead_date. Calculado como DATE_TRUNC(''week'', lead_date)::date.';

COMMENT ON COLUMN ops.v_payments_driver_matrix_cabinet.origin_tag IS 
'Origen del lead: ''cabinet'' o ''fleet_migration''. Fuente: ops.v_payment_calculation.origin_tag.';

COMMENT ON COLUMN ops.v_payments_driver_matrix_cabinet.connected_flag IS 
'TODO: Flag indicando si el driver se conectó. Fuente potencial: observational.v_conversion_metrics.first_connection_date. Por ahora siempre false.';

COMMENT ON COLUMN ops.v_payments_driver_matrix_cabinet.connected_date IS 
'TODO: Fecha de conexión del driver. Fuente potencial: observational.v_conversion_metrics.first_connection_date. Por ahora siempre NULL.';

-- Milestone M1
COMMENT ON COLUMN ops.v_payments_driver_matrix_cabinet.m1_achieved_flag IS 
'Flag indicando si el driver alcanzó el milestone M1 (milestone_value=1). Fuente: ops.v_claims_payment_status_cabinet.';

COMMENT ON COLUMN ops.v_payments_driver_matrix_cabinet.m1_achieved_date IS 
'Fecha en que el driver alcanzó el milestone M1. Fuente: ops.v_claims_payment_status_cabinet.lead_date.';

COMMENT ON COLUMN ops.v_payments_driver_matrix_cabinet.m1_expected_amount_yango IS 
'Monto esperado para milestone M1 según reglas de negocio (milestone 1=25). Fuente: ops.v_claims_payment_status_cabinet.expected_amount.';

COMMENT ON COLUMN ops.v_payments_driver_matrix_cabinet.m1_yango_payment_status IS 
'Estado de pago Yango para milestone M1: PAID, PAID_MISAPPLIED, UNPAID. Fuente: ops.v_yango_cabinet_claims_for_collection.yango_payment_status.';

COMMENT ON COLUMN ops.v_payments_driver_matrix_cabinet.m1_window_status IS 
'Estado de ventana para milestone M1: ''in_window'' (dentro de ventana) o ''expired'' (fuera de ventana). Fuente: ops.v_yango_payments_claims_cabinet_14d.window_status.';

COMMENT ON COLUMN ops.v_payments_driver_matrix_cabinet.m1_overdue_days IS 
'Días vencidos para milestone M1. 0 si no está vencido. Fuente: ops.v_claims_payment_status_cabinet.days_overdue.';

-- Milestone M5
COMMENT ON COLUMN ops.v_payments_driver_matrix_cabinet.m5_achieved_flag IS 
'Flag indicando si el driver alcanzó el milestone M5 (milestone_value=5). Fuente: ops.v_claims_payment_status_cabinet.';

COMMENT ON COLUMN ops.v_payments_driver_matrix_cabinet.m5_achieved_date IS 
'Fecha en que el driver alcanzó el milestone M5. Fuente: ops.v_claims_payment_status_cabinet.lead_date.';

COMMENT ON COLUMN ops.v_payments_driver_matrix_cabinet.m5_expected_amount_yango IS 
'Monto esperado para milestone M5 según reglas de negocio (milestone 5=35). Fuente: ops.v_claims_payment_status_cabinet.expected_amount.';

COMMENT ON COLUMN ops.v_payments_driver_matrix_cabinet.m5_yango_payment_status IS 
'Estado de pago Yango para milestone M5: PAID, PAID_MISAPPLIED, UNPAID. Fuente: ops.v_yango_cabinet_claims_for_collection.yango_payment_status.';

COMMENT ON COLUMN ops.v_payments_driver_matrix_cabinet.m5_window_status IS 
'Estado de ventana para milestone M5: ''in_window'' (dentro de ventana) o ''expired'' (fuera de ventana). Fuente: ops.v_yango_payments_claims_cabinet_14d.window_status.';

COMMENT ON COLUMN ops.v_payments_driver_matrix_cabinet.m5_overdue_days IS 
'Días vencidos para milestone M5. 0 si no está vencido. Fuente: ops.v_claims_payment_status_cabinet.days_overdue.';

-- Milestone M25
COMMENT ON COLUMN ops.v_payments_driver_matrix_cabinet.m25_achieved_flag IS 
'Flag indicando si el driver alcanzó el milestone M25 (milestone_value=25). Fuente: ops.v_claims_payment_status_cabinet.';

COMMENT ON COLUMN ops.v_payments_driver_matrix_cabinet.m25_achieved_date IS 
'Fecha en que el driver alcanzó el milestone M25. Fuente: ops.v_claims_payment_status_cabinet.lead_date.';

COMMENT ON COLUMN ops.v_payments_driver_matrix_cabinet.m25_expected_amount_yango IS 
'Monto esperado para milestone M25 según reglas de negocio (milestone 25=100). Fuente: ops.v_claims_payment_status_cabinet.expected_amount.';

COMMENT ON COLUMN ops.v_payments_driver_matrix_cabinet.m25_yango_payment_status IS 
'Estado de pago Yango para milestone M25: PAID, PAID_MISAPPLIED, UNPAID. Fuente: ops.v_yango_cabinet_claims_for_collection.yango_payment_status.';

COMMENT ON COLUMN ops.v_payments_driver_matrix_cabinet.m25_window_status IS 
'Estado de ventana para milestone M25: ''in_window'' (dentro de ventana) o ''expired'' (fuera de ventana). Fuente: ops.v_yango_payments_claims_cabinet_14d.window_status.';

COMMENT ON COLUMN ops.v_payments_driver_matrix_cabinet.m25_overdue_days IS 
'Días vencidos para milestone M25. 0 si no está vencido. Fuente: ops.v_claims_payment_status_cabinet.days_overdue.';

-- Scout
COMMENT ON COLUMN ops.v_payments_driver_matrix_cabinet.scout_due_flag IS 
'TODO: Flag indicando si el driver tiene pagos scout vencidos. Fuente potencial: ops.scout_payment_rules + ops.v_scout_liquidation_paid_items. Si no existe, dejar NULL y documentar con TODO.';

COMMENT ON COLUMN ops.v_payments_driver_matrix_cabinet.scout_paid_flag IS 
'TODO: Flag indicando si el driver tiene pagos scout pagados. Fuente potencial: ops.scout_payment_rules + ops.v_scout_liquidation_paid_items. Si no existe, dejar NULL y documentar con TODO.';

COMMENT ON COLUMN ops.v_payments_driver_matrix_cabinet.scout_amount IS 
'TODO: Monto de pagos scout para el driver. Fuente potencial: ops.scout_payment_rules + ops.v_scout_liquidation_paid_items. Si no existe, dejar NULL y documentar con TODO.';

-- Flags de inconsistencia de milestones
COMMENT ON COLUMN ops.v_payments_driver_matrix_cabinet.m5_without_m1_flag IS 
'Flag indicando inconsistencia: M5 tiene achieved_flag=true pero M1 no tiene achieved_flag=true. Indica que existe claim/status para M5 pero falta evidencia del milestone anterior (M1) en claims base. Esto es esperado y no es un bug.';

COMMENT ON COLUMN ops.v_payments_driver_matrix_cabinet.m25_without_m5_flag IS 
'Flag indicando inconsistencia: M25 tiene achieved_flag=true pero M5 no tiene achieved_flag=true. Indica que existe claim/status para M25 pero falta evidencia del milestone anterior (M5) en claims base. Esto es esperado y no es un bug.';

COMMENT ON COLUMN ops.v_payments_driver_matrix_cabinet.milestone_inconsistency_notes IS 
'Notas de texto corto describiendo las inconsistencias detectadas. Valores posibles: "M5 sin M1", "M25 sin M5", "M5 sin M1, M25 sin M5", o NULL si no hay inconsistencias.';
