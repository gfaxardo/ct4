-- ============================================================================
-- Vista: ops.v_payments_driver_matrix_cabinet
-- ============================================================================
-- PROPÓSITO DE NEGOCIO:
-- Vista de PRESENTACIÓN (no recalcula reglas) que muestra 1 fila por driver
-- con columnas por milestones M1/M5/M25 y estados Yango/Scout. Diseñada para
-- visualización en dashboards y reportes operativos.
-- ============================================================================
-- REGLAS DE NEGOCIO:
-- 1. Grano: driver_id (y person_key si aplica) - 1 fila por driver
-- 2. Milestones: M1 (milestone_value=1), M5 (milestone_value=5), M25 (milestone_value=25)
-- 3. Fuente base: ops.v_claims_payment_status_cabinet (garantiza 1 fila por claim)
-- 4. NO recalcula reglas: usa datos de vistas existentes directamente
-- 5. Pivotea milestones en columnas usando agregación condicional
-- ============================================================================
-- DEPENDENCIAS:
-- - ops.v_claims_payment_status_cabinet: claims base con milestones
-- - ops.v_yango_cabinet_claims_for_collection: yango_payment_status
-- - ops.v_yango_payments_claims_cabinet_14d: window_status
-- - public.drivers: driver_name
-- - ops.v_payment_calculation: origin_tag (si existe)
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
-- Usa v_payment_calculation como fuente principal (más común)
-- Si v_payment_calculation_updated existe, se puede actualizar después
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
        MAX(bc.person_key) AS person_key,
        -- Información base del driver
        MAX(di.driver_name) AS driver_name,
        MIN(bc.lead_date) AS lead_date,  -- Primera lead_date entre todos los milestones
        MAX(ocd.origin_tag) AS origin_tag,
        -- connected_flag y connected_date
        -- TODO: Implementar cuando exista fuente confiable de first_connection_date
        -- Por ahora, usar NULL ya que connected_date viene NULL desde origin_and_connected_data
        false AS connected_flag,
        NULL::date AS connected_date,
        -- week_start: lunes de la semana de lead_date
        DATE_TRUNC('week', MIN(bc.lead_date))::date AS week_start,
        -- Milestone M1 (milestone_value = 1)
        MAX(CASE WHEN bc.milestone_value = 1 THEN true ELSE false END) AS m1_achieved_flag,
        MAX(CASE WHEN bc.milestone_value = 1 THEN bc.lead_date END) AS m1_achieved_date,
        MAX(CASE WHEN bc.milestone_value = 1 THEN bc.expected_amount END) AS m1_expected_amount_yango,
        MAX(CASE WHEN bc.milestone_value = 1 THEN ys.yango_payment_status END) AS m1_yango_payment_status,
        MAX(CASE WHEN bc.milestone_value = 1 THEN ws.window_status END) AS m1_window_status,
        MAX(CASE WHEN bc.milestone_value = 1 THEN bc.days_overdue END) AS m1_overdue_days,
        -- Milestone M5 (milestone_value = 5)
        MAX(CASE WHEN bc.milestone_value = 5 THEN true ELSE false END) AS m5_achieved_flag,
        MAX(CASE WHEN bc.milestone_value = 5 THEN bc.lead_date END) AS m5_achieved_date,
        MAX(CASE WHEN bc.milestone_value = 5 THEN bc.expected_amount END) AS m5_expected_amount_yango,
        MAX(CASE WHEN bc.milestone_value = 5 THEN ys.yango_payment_status END) AS m5_yango_payment_status,
        MAX(CASE WHEN bc.milestone_value = 5 THEN ws.window_status END) AS m5_window_status,
        MAX(CASE WHEN bc.milestone_value = 5 THEN bc.days_overdue END) AS m5_overdue_days,
        -- Milestone M25 (milestone_value = 25)
        MAX(CASE WHEN bc.milestone_value = 25 THEN true ELSE false END) AS m25_achieved_flag,
        MAX(CASE WHEN bc.milestone_value = 25 THEN bc.lead_date END) AS m25_achieved_date,
        MAX(CASE WHEN bc.milestone_value = 25 THEN bc.expected_amount END) AS m25_expected_amount_yango,
        MAX(CASE WHEN bc.milestone_value = 25 THEN ys.yango_payment_status END) AS m25_yango_payment_status,
        MAX(CASE WHEN bc.milestone_value = 25 THEN ws.window_status END) AS m25_window_status,
        MAX(CASE WHEN bc.milestone_value = 25 THEN bc.days_overdue END) AS m25_overdue_days,
        -- TODO: Scout - dejar NULLs por ahora
        -- scout_due_flag, scout_paid_flag, scout_amount
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
    -- connected_flag y connected_date desde v_payment_calculation_updated
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
    -- Fuente potencial: ops.scout_payment_rules + ops.v_scout_liquidation_paid_items
    -- Si no existe, dejar NULL y documentar con TODO
    scout_due_flag,
    scout_paid_flag,
    scout_amount
FROM driver_milestones;

-- ============================================================================
-- Comentarios de la Vista
-- ============================================================================
COMMENT ON VIEW ops.v_payments_driver_matrix_cabinet IS 
'Vista de PRESENTACIÓN (no recalcula reglas) que muestra 1 fila por driver con columnas por milestones M1/M5/M25 y estados Yango/Scout. Diseñada para visualización en dashboards y reportes operativos. Grano: driver_id (y person_key si aplica).';

COMMENT ON COLUMN ops.v_payments_driver_matrix_cabinet.driver_id IS 
'ID del conductor. Grano principal de la vista (1 fila por driver_id).';

COMMENT ON COLUMN ops.v_payments_driver_matrix_cabinet.person_key IS 
'Person key del conductor (identidad canónica). Puede ser NULL si no existe.';

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

-- ============================================================================
-- QUERIES DE VERIFICACIÓN
-- ============================================================================

-- 1. Verificación básica: COUNT y sample de 20 filas
/*
SELECT 
    '=== VERIFICACIÓN BÁSICA ===' AS seccion,
    COUNT(*) AS total_drivers,
    COUNT(*) FILTER (WHERE m1_achieved_flag = true) AS drivers_with_m1,
    COUNT(*) FILTER (WHERE m5_achieved_flag = true) AS drivers_with_m5,
    COUNT(*) FILTER (WHERE m25_achieved_flag = true) AS drivers_with_m25,
    COUNT(*) FILTER (WHERE connected_flag = true) AS drivers_connected,
    COUNT(*) FILTER (WHERE origin_tag IS NOT NULL) AS drivers_with_origin_tag
FROM ops.v_payments_driver_matrix_cabinet;

-- 2. Sample de 20 filas
SELECT 
    '=== SAMPLE 20 FILAS ===' AS seccion,
    driver_id,
    person_key,
    driver_name,
    lead_date,
    week_start,
    origin_tag,
    connected_flag,
    connected_date,
    m1_achieved_flag,
    m1_yango_payment_status,
    m5_achieved_flag,
    m5_yango_payment_status,
    m25_achieved_flag,
    m25_yango_payment_status
FROM ops.v_payments_driver_matrix_cabinet
ORDER BY lead_date DESC
LIMIT 20;

-- 3. Sanity checks: verificar que no hay duplicados por driver_id
SELECT 
    '=== SANITY CHECK: DUPLICADOS ===' AS seccion,
    driver_id,
    COUNT(*) AS count_rows
FROM ops.v_payments_driver_matrix_cabinet
GROUP BY driver_id
HAVING COUNT(*) > 1;

-- 4. Sanity checks: verificar distribución de milestones
SELECT 
    '=== SANITY CHECK: DISTRIBUCIÓN MILESTONES ===' AS seccion,
    COUNT(*) AS total_drivers,
    COUNT(*) FILTER (WHERE m1_achieved_flag = true) AS count_m1,
    COUNT(*) FILTER (WHERE m5_achieved_flag = true) AS count_m5,
    COUNT(*) FILTER (WHERE m25_achieved_flag = true) AS count_m25,
    COUNT(*) FILTER (WHERE m1_achieved_flag = true AND m5_achieved_flag = true) AS count_m1_and_m5,
    COUNT(*) FILTER (WHERE m1_achieved_flag = true AND m5_achieved_flag = true AND m25_achieved_flag = true) AS count_all_milestones
FROM ops.v_payments_driver_matrix_cabinet;

-- 5. Sanity checks: verificar distribución de yango_payment_status
SELECT 
    '=== SANITY CHECK: DISTRIBUCIÓN YANGO PAYMENT STATUS ===' AS seccion,
    'M1' AS milestone,
    m1_yango_payment_status AS payment_status,
    COUNT(*) AS count_rows
FROM ops.v_payments_driver_matrix_cabinet
WHERE m1_achieved_flag = true
GROUP BY m1_yango_payment_status
UNION ALL
SELECT 
    'M5' AS milestone,
    m5_yango_payment_status AS payment_status,
    COUNT(*) AS count_rows
FROM ops.v_payments_driver_matrix_cabinet
WHERE m5_achieved_flag = true
GROUP BY m5_yango_payment_status
UNION ALL
SELECT 
    'M25' AS milestone,
    m25_yango_payment_status AS payment_status,
    COUNT(*) AS count_rows
FROM ops.v_payments_driver_matrix_cabinet
WHERE m25_achieved_flag = true
GROUP BY m25_yango_payment_status
ORDER BY milestone, payment_status;

-- 6. Sanity checks: verificar distribución de window_status
SELECT 
    '=== SANITY CHECK: DISTRIBUCIÓN WINDOW STATUS ===' AS seccion,
    'M1' AS milestone,
    m1_window_status AS window_status,
    COUNT(*) AS count_rows
FROM ops.v_payments_driver_matrix_cabinet
WHERE m1_achieved_flag = true
GROUP BY m1_window_status
UNION ALL
SELECT 
    'M5' AS milestone,
    m5_window_status AS window_status,
    COUNT(*) AS count_rows
FROM ops.v_payments_driver_matrix_cabinet
WHERE m5_achieved_flag = true
GROUP BY m5_window_status
UNION ALL
SELECT 
    'M25' AS milestone,
    m25_window_status AS window_status,
    COUNT(*) AS count_rows
FROM ops.v_payments_driver_matrix_cabinet
WHERE m25_achieved_flag = true
GROUP BY m25_window_status
ORDER BY milestone, window_status;

-- 7. Sanity checks: verificar expected_amounts
SELECT 
    '=== SANITY CHECK: EXPECTED AMOUNTS ===' AS seccion,
    'M1' AS milestone,
    COUNT(*) AS count_rows,
    COUNT(*) FILTER (WHERE m1_expected_amount_yango = 25) AS count_correct_amount,
    COUNT(*) FILTER (WHERE m1_expected_amount_yango != 25 AND m1_expected_amount_yango IS NOT NULL) AS count_incorrect_amount
FROM ops.v_payments_driver_matrix_cabinet
WHERE m1_achieved_flag = true
UNION ALL
SELECT 
    'M5' AS milestone,
    COUNT(*) AS count_rows,
    COUNT(*) FILTER (WHERE m5_expected_amount_yango = 35) AS count_correct_amount,
    COUNT(*) FILTER (WHERE m5_expected_amount_yango != 35 AND m5_expected_amount_yango IS NOT NULL) AS count_incorrect_amount
FROM ops.v_payments_driver_matrix_cabinet
WHERE m5_achieved_flag = true
UNION ALL
SELECT 
    'M25' AS milestone,
    COUNT(*) AS count_rows,
    COUNT(*) FILTER (WHERE m25_expected_amount_yango = 100) AS count_correct_amount,
    COUNT(*) FILTER (WHERE m25_expected_amount_yango != 100 AND m25_expected_amount_yango IS NOT NULL) AS count_incorrect_amount
FROM ops.v_payments_driver_matrix_cabinet
WHERE m25_achieved_flag = true;
*/

