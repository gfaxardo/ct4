-- ============================================================================
-- Vista: ops.v_payments_driver_matrix_cabinet
-- ============================================================================
-- PROPÓSITO:
-- Vista de PRESENTACIÓN (no recalcula reglas) que muestra 1 fila por driver
-- con columnas por milestones M1/M5/M25 y estados Yango/Scout. Diseñada para
-- visualización en dashboards y reportes operativos.
-- ============================================================================
-- GRANO:
-- 1 fila por driver_id (agregación por GROUP BY driver_id)
-- REGLA NO NEGOCIABLE: EXACTAMENTE 1 fila por driver_id
-- ============================================================================
-- FUENTES (Dependencias):
-- - ops.v_cabinet_milestones_achieved_from_trips: flags achieved determinísticos (basados en viajes reales)
-- - ops.v_claims_payment_status_cabinet: claims base con milestones (para payment status, amounts, overdue)
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
-- Los flags achieved (m1_achieved_flag, m5_achieved_flag, m25_achieved_flag) y achieved_date
-- provienen de ops.v_cabinet_milestones_achieved_from_trips (determinísticos basados en viajes reales).
-- Los flags achieved son CUMULATIVOS: si un driver alguna vez alcanzó un milestone por trips,
-- el flag será true independientemente de la semana o del estado de pago.
-- achieved_date es la primera fecha real (MIN achieved_date) en que se alcanzó el milestone.
-- La información de pagos/claims (expected_amount, payment_status, window_status, overdue_days)
-- proviene de ops.v_claims_payment_status_cabinet (reglas de negocio y ventanas de pago).
-- ============================================================================

CREATE OR REPLACE VIEW ops.v_payments_driver_matrix_cabinet AS
WITH deterministic_milestones_events AS (
    -- Milestones como eventos puros (sin agregación)
    -- Fuente determinística: milestones achieved basados únicamente en viajes reales
    SELECT 
        m.driver_id,
        m.milestone_value,
        m.achieved_flag,
        m.achieved_date
    FROM ops.v_cabinet_milestones_achieved_from_trips m
    WHERE m.milestone_value IN (1, 5, 25)
),
base_claims AS (
    -- Base: claims por driver y milestone desde v_claims_payment_status_cabinet
    -- SOLO para información de pagos/claims (amounts, status, overdue)
    -- NO para flags achieved (esos vienen de deterministic_milestones_events)
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
-- Obtener funnel_status y highest_milestone desde v_cabinet_funnel_status
funnel_status_data AS (
    SELECT 
        fs.driver_id,
        fs.funnel_status,
        fs.highest_milestone,
        fs.connected_flag,
        fs.connected_date
    FROM ops.v_cabinet_funnel_status fs
),
-- Agregar milestones determinísticos por driver_id (CUMULATIVOS)
-- Si alguna vez alcanzó un milestone, el flag será true
deterministic_milestones_agg AS (
    SELECT 
        dm.driver_id,
        -- FLAGS ACHIEVED CUMULATIVOS: si alguna vez alcanzó, siempre true
        BOOL_OR(dm.milestone_value = 1 AND dm.achieved_flag = true) AS m1_achieved_flag,
        -- achieved_date: primera fecha real (MIN) en que se alcanzó
        MIN(CASE WHEN dm.milestone_value = 1 AND dm.achieved_flag = true THEN dm.achieved_date END) AS m1_achieved_date,
        BOOL_OR(dm.milestone_value = 5 AND dm.achieved_flag = true) AS m5_achieved_flag,
        MIN(CASE WHEN dm.milestone_value = 5 AND dm.achieved_flag = true THEN dm.achieved_date END) AS m5_achieved_date,
        BOOL_OR(dm.milestone_value = 25 AND dm.achieved_flag = true) AS m25_achieved_flag,
        MIN(CASE WHEN dm.milestone_value = 25 AND dm.achieved_flag = true THEN dm.achieved_date END) AS m25_achieved_date
    FROM deterministic_milestones_events dm
    GROUP BY dm.driver_id
),
-- Agregar claims por driver_id (para payment info)
claims_agg AS (
    SELECT 
        bc.driver_id,
        -- person_key: seleccionar el del milestone más reciente
        (array_agg(bc.person_key ORDER BY bc.lead_date DESC NULLS LAST))[1] AS person_key,
        MIN(bc.lead_date) AS lead_date,  -- Primera lead_date entre todos los milestones
        -- PAYMENT INFO: desde base_claims (reglas de negocio y ventanas)
        MAX(CASE WHEN bc.milestone_value = 1 THEN bc.expected_amount END) AS m1_expected_amount_yango,
        MAX(CASE WHEN bc.milestone_value = 5 THEN bc.expected_amount END) AS m5_expected_amount_yango,
        MAX(CASE WHEN bc.milestone_value = 25 THEN bc.expected_amount END) AS m25_expected_amount_yango,
        MAX(CASE WHEN bc.milestone_value = 1 THEN bc.days_overdue END) AS m1_overdue_days,
        MAX(CASE WHEN bc.milestone_value = 5 THEN bc.days_overdue END) AS m5_overdue_days,
        MAX(CASE WHEN bc.milestone_value = 25 THEN bc.days_overdue END) AS m25_overdue_days
    FROM base_claims bc
    GROUP BY bc.driver_id
),
-- Agregar por driver_id pivotando milestones (1 FILA POR DRIVER)
driver_milestones AS (
    SELECT 
        COALESCE(ca.driver_id, dma.driver_id, ocd.driver_id, fs.driver_id) AS driver_id,
        -- Información base del driver
        ca.person_key,
        MAX(di.driver_name) AS driver_name,
        ca.lead_date,
        -- origin_tag: prioridad: cabinet > fleet_migration > unknown
        -- Asegurar que nunca sea NULL (usar funnel_status como fallback)
        COALESCE(
            MAX(CASE WHEN ocd.origin_tag = 'cabinet' THEN 'cabinet' END),
            MAX(CASE WHEN ocd.origin_tag = 'fleet_migration' THEN 'fleet_migration' END),
            MAX(fs.origin_tag),
            'unknown'
        ) AS origin_tag,
        -- Funnel status y highest_milestone desde v_cabinet_funnel_status
        MAX(fs.funnel_status) AS funnel_status,
        MAX(fs.highest_milestone) AS highest_milestone,
        -- connected_flag y connected_date desde funnel_status
        MAX(fs.connected_flag) AS connected_flag,
        MAX(fs.connected_date) AS connected_date,
        -- week_start: última semana relevante (máxima entre claims y milestones achieved)
        -- week_start: última semana relevante (máxima entre claims y milestones achieved)
        -- Usar NULLIF para convertir '1900-01-01' de vuelta a NULL si todos son NULL
        NULLIF(
            GREATEST(
                COALESCE(DATE_TRUNC('week', ca.lead_date)::date, '1900-01-01'::date),
                COALESCE(DATE_TRUNC('week', dma.m1_achieved_date)::date, '1900-01-01'::date),
                COALESCE(DATE_TRUNC('week', dma.m5_achieved_date)::date, '1900-01-01'::date),
                COALESCE(DATE_TRUNC('week', dma.m25_achieved_date)::date, '1900-01-01'::date),
                COALESCE(MAX(DATE_TRUNC('week', ocd.lead_date)::date), '1900-01-01'::date)
            ),
            '1900-01-01'::date
        ) AS week_start,
        -- Milestone M1 (milestone_value = 1)
        -- FLAGS ACHIEVED CUMULATIVOS: desde deterministic_milestones_agg
        COALESCE(dma.m1_achieved_flag, false) AS m1_achieved_flag,
        dma.m1_achieved_date,
        -- PAYMENT INFO: desde claims_agg
        -- PROTECCIÓN: Solo mostrar payment info si achieved_flag = true
        CASE WHEN COALESCE(dma.m1_achieved_flag, false) = true THEN ca.m1_expected_amount_yango ELSE NULL END AS m1_expected_amount_yango,
        CASE WHEN COALESCE(dma.m1_achieved_flag, false) = true THEN MAX(CASE WHEN ys.milestone_value = 1 THEN ys.yango_payment_status END) ELSE NULL END AS m1_yango_payment_status,
        CASE WHEN COALESCE(dma.m1_achieved_flag, false) = true THEN MAX(CASE WHEN ws.milestone_value = 1 THEN ws.window_status END) ELSE NULL END AS m1_window_status,
        CASE WHEN COALESCE(dma.m1_achieved_flag, false) = true THEN ca.m1_overdue_days ELSE NULL END AS m1_overdue_days,
        -- Milestone M5 (milestone_value = 5)
        -- FLAGS ACHIEVED CUMULATIVOS: desde deterministic_milestones_agg
        COALESCE(dma.m5_achieved_flag, false) AS m5_achieved_flag,
        dma.m5_achieved_date,
        -- PAYMENT INFO: desde claims_agg
        -- PROTECCIÓN: Solo mostrar payment info si achieved_flag = true
        CASE WHEN COALESCE(dma.m5_achieved_flag, false) = true THEN ca.m5_expected_amount_yango ELSE NULL END AS m5_expected_amount_yango,
        CASE WHEN COALESCE(dma.m5_achieved_flag, false) = true THEN MAX(CASE WHEN ys.milestone_value = 5 THEN ys.yango_payment_status END) ELSE NULL END AS m5_yango_payment_status,
        CASE WHEN COALESCE(dma.m5_achieved_flag, false) = true THEN MAX(CASE WHEN ws.milestone_value = 5 THEN ws.window_status END) ELSE NULL END AS m5_window_status,
        CASE WHEN COALESCE(dma.m5_achieved_flag, false) = true THEN ca.m5_overdue_days ELSE NULL END AS m5_overdue_days,
        -- Milestone M25 (milestone_value = 25)
        -- FLAGS ACHIEVED CUMULATIVOS: desde deterministic_milestones_agg
        COALESCE(dma.m25_achieved_flag, false) AS m25_achieved_flag,
        dma.m25_achieved_date,
        -- PAYMENT INFO: desde claims_agg
        -- PROTECCIÓN: Solo mostrar payment info si achieved_flag = true
        CASE WHEN COALESCE(dma.m25_achieved_flag, false) = true THEN ca.m25_expected_amount_yango ELSE NULL END AS m25_expected_amount_yango,
        CASE WHEN COALESCE(dma.m25_achieved_flag, false) = true THEN MAX(CASE WHEN ys.milestone_value = 25 THEN ys.yango_payment_status END) ELSE NULL END AS m25_yango_payment_status,
        CASE WHEN COALESCE(dma.m25_achieved_flag, false) = true THEN MAX(CASE WHEN ws.milestone_value = 25 THEN ws.window_status END) ELSE NULL END AS m25_window_status,
        CASE WHEN COALESCE(dma.m25_achieved_flag, false) = true THEN ca.m25_overdue_days ELSE NULL END AS m25_overdue_days,
        -- TODO: Scout - dejar NULLs por ahora
        -- Fuente potencial: ops.scout_payment_rules + ops.v_scout_liquidation_paid_items
        NULL::boolean AS scout_due_flag,
        NULL::boolean AS scout_paid_flag,
        NULL::numeric(12,2) AS scout_amount,
        -- Flags de inconsistencia de milestones (basados en flags determinísticos cumulativos)
        -- M5 sin M1: M5 tiene achieved_flag pero M1 no tiene achieved_flag
        (COALESCE(dma.m5_achieved_flag, false) = true
         AND COALESCE(dma.m1_achieved_flag, false) = false) AS m5_without_m1_flag,
        -- M25 sin M5: M25 tiene achieved_flag pero M5 no tiene achieved_flag
        (COALESCE(dma.m25_achieved_flag, false) = true
         AND COALESCE(dma.m5_achieved_flag, false) = false) AS m25_without_m5_flag,
        -- Notas de inconsistencia (texto corto)
        -- NOTA: Con la vista determinística y flags cumulativos, estas inconsistencias NO deberían ocurrir
        -- porque v_cabinet_milestones_achieved_from_trips expande milestones menores.
        -- Se mantienen por compatibilidad y para detectar posibles bugs.
        CASE 
            WHEN (COALESCE(dma.m5_achieved_flag, false) = true
                  AND COALESCE(dma.m1_achieved_flag, false) = false)
                 AND (COALESCE(dma.m25_achieved_flag, false) = true
                      AND COALESCE(dma.m5_achieved_flag, false) = false)
            THEN 'M5 sin M1, M25 sin M5'
            WHEN (COALESCE(dma.m5_achieved_flag, false) = true
                  AND COALESCE(dma.m1_achieved_flag, false) = false)
            THEN 'M5 sin M1'
            WHEN (COALESCE(dma.m25_achieved_flag, false) = true
                  AND COALESCE(dma.m5_achieved_flag, false) = false)
            THEN 'M25 sin M5'
            ELSE NULL
        END AS milestone_inconsistency_notes
    FROM deterministic_milestones_agg dma
    FULL OUTER JOIN claims_agg ca
        ON ca.driver_id = dma.driver_id
    LEFT JOIN yango_status ys 
        ON ys.driver_id = COALESCE(ca.driver_id, dma.driver_id)
        AND ys.milestone_value IN (1, 5, 25)
    LEFT JOIN window_status_data ws 
        ON ws.driver_id = COALESCE(ca.driver_id, dma.driver_id)
        AND ws.milestone_value IN (1, 5, 25)
    LEFT JOIN origin_and_connected_data ocd 
        ON ocd.driver_id = COALESCE(ca.driver_id, dma.driver_id)
        AND (ocd.person_key = ca.person_key OR (ocd.person_key IS NULL AND ca.person_key IS NULL))
    LEFT JOIN driver_info di 
        ON di.driver_id = COALESCE(ca.driver_id, dma.driver_id)
    LEFT JOIN funnel_status_data fs
        ON fs.driver_id = COALESCE(ca.driver_id, dma.driver_id)
    GROUP BY 
        COALESCE(ca.driver_id, dma.driver_id, ocd.driver_id),
        ca.person_key,
        ca.lead_date,
        dma.m1_achieved_flag,
        dma.m1_achieved_date,
        dma.m5_achieved_flag,
        dma.m5_achieved_date,
        dma.m25_achieved_flag,
        dma.m25_achieved_date,
        ca.m1_expected_amount_yango,
        ca.m5_expected_amount_yango,
        ca.m25_expected_amount_yango,
        ca.m1_overdue_days,
        ca.m5_overdue_days,
        ca.m25_overdue_days
)
SELECT 
    driver_id,
    person_key,
    driver_name,
    lead_date,
    week_start,
    origin_tag,
    funnel_status,
    highest_milestone,
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
'Vista de PRESENTACIÓN (no recalcula reglas) que muestra 1 fila por driver con columnas por milestones M1/M5/M25 y estados Yango/Scout. Diseñada para visualización en dashboards y reportes operativos. Grano: driver_id (EXACTAMENTE 1 fila por driver_id). Flags achieved son CUMULATIVOS: si un driver alguna vez alcanzó un milestone por trips, el flag será true.';

COMMENT ON COLUMN ops.v_payments_driver_matrix_cabinet.driver_id IS 
'ID del conductor. Grano principal de la vista (EXACTAMENTE 1 fila por driver_id).';

COMMENT ON COLUMN ops.v_payments_driver_matrix_cabinet.person_key IS 
'Person key del conductor (identidad canónica). Seleccionado del milestone más reciente. Puede ser NULL si no existe.';

COMMENT ON COLUMN ops.v_payments_driver_matrix_cabinet.driver_name IS 
'Nombre del conductor desde public.drivers.full_name. Puede ser NULL si no existe en la tabla drivers.';

COMMENT ON COLUMN ops.v_payments_driver_matrix_cabinet.lead_date IS 
'Primera fecha de lead_date entre todos los milestones del driver. Fuente: ops.v_claims_payment_status_cabinet.lead_date.';

COMMENT ON COLUMN ops.v_payments_driver_matrix_cabinet.week_start IS 
'Última semana relevante: máxima entre week_start de claims y week_start de milestones achieved. Calculado como GREATEST(max(claim_week_start), max(achieved_week_start)).';

COMMENT ON COLUMN ops.v_payments_driver_matrix_cabinet.origin_tag IS 
'Origen del lead: ''cabinet'' o ''fleet_migration''. Fuente: ops.v_payment_calculation.origin_tag.';

COMMENT ON COLUMN ops.v_payments_driver_matrix_cabinet.connected_flag IS 
'Flag indicando si el driver se conectó (first_connection_date IS NOT NULL). Fuente: ops.v_cabinet_funnel_status.connected_flag.';

COMMENT ON COLUMN ops.v_payments_driver_matrix_cabinet.connected_date IS 
'Primera fecha de conexión del driver. Fuente: ops.v_cabinet_funnel_status.connected_date (desde observational.v_conversion_metrics.first_connection_date).';

-- Milestone M1
COMMENT ON COLUMN ops.v_payments_driver_matrix_cabinet.m1_achieved_flag IS 
'Flag indicando si el driver alguna vez alcanzó el milestone M1 (milestone_value=1) por trips (CUMULATIVO). Fuente: ops.v_cabinet_milestones_achieved_from_trips (determinístico basado en viajes reales). Si alguna vez alcanzó M1, el flag será true independientemente de la semana o del estado de pago.';

COMMENT ON COLUMN ops.v_payments_driver_matrix_cabinet.m1_achieved_date IS 
'Primera fecha real (MIN achieved_date) en que el driver alcanzó el milestone M1. Fuente: ops.v_cabinet_milestones_achieved_from_trips.achieved_date (determinístico basado en viajes reales).';

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
'Flag indicando si el driver alguna vez alcanzó el milestone M5 (milestone_value=5) por trips (CUMULATIVO). Fuente: ops.v_cabinet_milestones_achieved_from_trips (determinístico basado en viajes reales). Si alguna vez alcanzó M5, el flag será true independientemente de la semana o del estado de pago.';

COMMENT ON COLUMN ops.v_payments_driver_matrix_cabinet.m5_achieved_date IS 
'Primera fecha real (MIN achieved_date) en que el driver alcanzó el milestone M5. Fuente: ops.v_cabinet_milestones_achieved_from_trips.achieved_date (determinístico basado en viajes reales).';

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
'Flag indicando si el driver alguna vez alcanzó el milestone M25 (milestone_value=25) por trips (CUMULATIVO). Fuente: ops.v_cabinet_milestones_achieved_from_trips (determinístico basado en viajes reales). Si alguna vez alcanzó M25, el flag será true independientemente de la semana o del estado de pago.';

COMMENT ON COLUMN ops.v_payments_driver_matrix_cabinet.m25_achieved_date IS 
'Primera fecha real (MIN achieved_date) en que el driver alcanzó el milestone M25. Fuente: ops.v_cabinet_milestones_achieved_from_trips.achieved_date (determinístico basado en viajes reales).';

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
'Flag indicando inconsistencia: M5 tiene achieved_flag=true pero M1 no tiene achieved_flag=true (cumulativo). Con la vista determinística y flags cumulativos, estas inconsistencias NO deberían ocurrir porque v_cabinet_milestones_achieved_from_trips expande milestones menores. Se mantiene por compatibilidad y para detectar posibles bugs.';

COMMENT ON COLUMN ops.v_payments_driver_matrix_cabinet.m25_without_m5_flag IS 
'Flag indicando inconsistencia: M25 tiene achieved_flag=true pero M5 no tiene achieved_flag=true (cumulativo). Con la vista determinística y flags cumulativos, estas inconsistencias NO deberían ocurrir porque v_cabinet_milestones_achieved_from_trips expande milestones menores. Se mantiene por compatibilidad y para detectar posibles bugs.';

COMMENT ON COLUMN ops.v_payments_driver_matrix_cabinet.milestone_inconsistency_notes IS 
'Notas de texto corto describiendo las inconsistencias detectadas. Valores posibles: "M5 sin M1", "M25 sin M5", "M5 sin M1, M25 sin M5", o NULL si no hay inconsistencias.';
