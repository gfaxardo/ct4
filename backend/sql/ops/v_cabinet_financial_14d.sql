-- ============================================================================
-- Vista: ops.v_cabinet_financial_14d
-- ============================================================================
-- PROPÓSITO:
-- Fuente de verdad financiera para CABINET que permite determinar con exactitud
-- qué conductores generan pago de Yango y detectar deudas por milestones no pagados.
-- 
-- Esta vista responde sin ambigüedad: "Yango nos debe X soles por estos drivers y estos hitos".
-- ============================================================================
-- REGLAS DE NEGOCIO:
-- 1. Origen: cabinet (origin_tag = 'cabinet')
-- 2. Ventana financiera: 14 días desde lead_date
-- 3. Fuente operativa de viajes: summary_daily (count_orders_completed)
-- 4. Reglas Yango (acumulativo):
--    - 1 viaje en 14d → S/ 25 (M1)
--    - 5 viajes en 14d → +S/ 35 (M5)
--    - 25 viajes en 14d → +S/ 100 (M25)
-- 5. Un milestone solo existe financieramente si se alcanza dentro de los 14 días.
-- 6. NO usar achieved histórico sin ventana.
-- 7. summary_daily es la única fuente de viajes.
-- ============================================================================
-- GRANO:
-- 1 fila por driver_id (GARANTIZADO)
-- ============================================================================
-- FUENTES:
-- - lead_date, connected_date: observational.v_conversion_metrics
-- - Viajes: public.summary_daily (count_orders_completed)
-- - Claims/pagos: ops.v_claims_payment_status_cabinet
-- ============================================================================

-- DROP VIEW si existe para permitir cambios en el orden de columnas
DROP VIEW IF EXISTS ops.v_cabinet_financial_14d CASCADE;

CREATE VIEW ops.v_cabinet_financial_14d AS
WITH conversion_base AS (
    -- Base: lead_date y first_connection_date desde v_conversion_metrics (cabinet)
    SELECT DISTINCT ON (driver_id)
        driver_id,
        lead_date,
        first_connection_date
    FROM observational.v_conversion_metrics
    WHERE origin_tag = 'cabinet'
        AND driver_id IS NOT NULL
        AND lead_date IS NOT NULL
    ORDER BY driver_id, lead_date DESC
),
-- Agregar drivers desde v_payment_calculation que tienen lead_date pero no están en conversion_metrics
-- Usamos v_payment_calculation directamente (más eficiente que v_claims_payment_status_cabinet)
payment_calc_base AS (
    -- Drivers con lead_date desde v_payment_calculation (cabinet) que pueden no estar en conversion_metrics
    SELECT DISTINCT ON (driver_id)
        driver_id,
        lead_date,
        NULL::date AS first_connection_date
    FROM ops.v_payment_calculation
    WHERE origin_tag = 'cabinet'
        AND driver_id IS NOT NULL
        AND lead_date IS NOT NULL
    ORDER BY driver_id, lead_date DESC
),
-- Combinar conversion_base con payment_calc_base (drivers con lead_date desde payment_calc pero no en conversion_metrics)
all_drivers_base AS (
    SELECT 
        cb.driver_id,
        cb.lead_date,
        cb.first_connection_date
    FROM conversion_base cb
    
    UNION
    
    -- Agregar drivers desde payment_calc que no están en conversion_base pero tienen lead_date
    SELECT 
        pc.driver_id,
        pc.lead_date,
        pc.first_connection_date
    FROM payment_calc_base pc
    WHERE NOT EXISTS (
        SELECT 1 
        FROM conversion_base cb2 
        WHERE cb2.driver_id = pc.driver_id
    )
),
summary_daily_normalized AS (
    -- Normalizar summary_daily con fecha convertida
    SELECT 
        driver_id,
        to_date(date_file, 'DD-MM-YYYY') AS prod_date,
        count_orders_completed
    FROM public.summary_daily
    WHERE driver_id IS NOT NULL
        AND date_file IS NOT NULL
        AND date_file ~ '^\d{2}-\d{2}-\d{4}$'  -- Validar formato DD-MM-YYYY
),
trips_14d AS (
    -- Viajes dentro de ventana de 14 días desde lead_date
    SELECT 
        adb.driver_id,
        adb.lead_date,
        adb.first_connection_date,
        -- Ventana de 14 días: desde lead_date hasta lead_date + 14 días
        adb.lead_date + INTERVAL '14 days' AS window_end_date,
        -- Viajes completados dentro de ventana
        COALESCE(SUM(sd.count_orders_completed), 0) AS total_trips_14d
    FROM all_drivers_base adb
    LEFT JOIN summary_daily_normalized sd
        ON sd.driver_id = adb.driver_id
        AND sd.prod_date >= adb.lead_date
        AND sd.prod_date < adb.lead_date + INTERVAL '14 days'
    GROUP BY adb.driver_id, adb.lead_date, adb.first_connection_date
),
milestones_14d AS (
    -- Milestones alcanzados dentro de ventana de 14 días
    SELECT 
        t.driver_id,
        t.lead_date,
        t.first_connection_date,
        t.total_trips_14d,
        -- Flags de milestones alcanzados dentro de ventana
        CASE WHEN t.total_trips_14d >= 1 THEN true ELSE false END AS reached_m1_14d,
        CASE WHEN t.total_trips_14d >= 5 THEN true ELSE false END AS reached_m5_14d,
        CASE WHEN t.total_trips_14d >= 25 THEN true ELSE false END AS reached_m25_14d,
        -- Montos esperados (acumulativo)
        CASE WHEN t.total_trips_14d >= 1 THEN 25::numeric(12,2) ELSE 0::numeric(12,2) END AS expected_amount_m1,
        CASE WHEN t.total_trips_14d >= 5 THEN 35::numeric(12,2) ELSE 0::numeric(12,2) END AS expected_amount_m5,
        CASE WHEN t.total_trips_14d >= 25 THEN 100::numeric(12,2) ELSE 0::numeric(12,2) END AS expected_amount_m25,
        -- Total esperado acumulativo
        CASE 
            WHEN t.total_trips_14d >= 25 THEN (25 + 35 + 100)::numeric(12,2)
            WHEN t.total_trips_14d >= 5 THEN (25 + 35)::numeric(12,2)
            WHEN t.total_trips_14d >= 1 THEN 25::numeric(12,2)
            ELSE 0::numeric(12,2)
        END AS expected_total_yango
    FROM trips_14d t
),
claims_status AS (
    -- Estado real de claims por milestone desde v_claims_payment_status_cabinet
    SELECT 
        driver_id,
        milestone_value,
        paid_flag,
        payment_status,
        expected_amount,
        -- Monto pagado (0 si no pagado)
        CASE WHEN paid_flag = true THEN expected_amount ELSE 0::numeric(12,2) END AS paid_amount
    FROM ops.v_claims_payment_status_cabinet
    WHERE driver_id IS NOT NULL
        AND milestone_value IN (1, 5, 25)
),
claims_aggregated AS (
    -- Agregar claims por driver
    SELECT 
        driver_id,
        -- Flags de claims por milestone
        BOOL_OR(milestone_value = 1 AND paid_flag = true) AS claim_m1_paid,
        BOOL_OR(milestone_value = 1) AS claim_m1_exists,
        BOOL_OR(milestone_value = 5 AND paid_flag = true) AS claim_m5_paid,
        BOOL_OR(milestone_value = 5) AS claim_m5_exists,
        BOOL_OR(milestone_value = 25 AND paid_flag = true) AS claim_m25_paid,
        BOOL_OR(milestone_value = 25) AS claim_m25_exists,
        -- Montos pagados
        SUM(CASE WHEN milestone_value = 1 AND paid_flag = true THEN paid_amount ELSE 0 END) AS paid_amount_m1,
        SUM(CASE WHEN milestone_value = 5 AND paid_flag = true THEN paid_amount ELSE 0 END) AS paid_amount_m5,
        SUM(CASE WHEN milestone_value = 25 AND paid_flag = true THEN paid_amount ELSE 0 END) AS paid_amount_m25,
        -- Total pagado
        SUM(paid_amount) AS total_paid_yango
    FROM claims_status
    GROUP BY driver_id
),
driver_info AS (
    -- Obtener nombre del driver desde public.drivers
    SELECT 
        d.driver_id,
        d.full_name AS driver_name
    FROM public.drivers d
)
SELECT 
    m.driver_id,
    -- 1) lead_date
    m.lead_date,
    -- Nombre del driver
    COALESCE(di.driver_name, 'N/A') AS driver_name,
    -- Semana ISO (formato: YYYY-WW)
    CASE 
        WHEN m.lead_date IS NOT NULL 
        THEN TO_CHAR(m.lead_date, 'IYYY-IW')
        ELSE NULL
    END AS iso_week,
    -- 2) connected_flag y connected_date
    (m.first_connection_date IS NOT NULL) AS connected_flag,
    m.first_connection_date AS connected_date,
    -- 3) total_trips_14d
    m.total_trips_14d,
    -- 4) reached_m1_14d / reached_m5_14d / reached_m25_14d
    m.reached_m1_14d,
    m.reached_m5_14d,
    m.reached_m25_14d,
    -- 5) expected_amount_m1 / m5 / m25
    m.expected_amount_m1,
    m.expected_amount_m5,
    m.expected_amount_m25,
    -- 6) expected_total_yango
    m.expected_total_yango,
    -- 7) estado real de claims por milestone
    COALESCE(c.claim_m1_exists, false) AS claim_m1_exists,
    COALESCE(c.claim_m1_paid, false) AS claim_m1_paid,
    COALESCE(c.claim_m5_exists, false) AS claim_m5_exists,
    COALESCE(c.claim_m5_paid, false) AS claim_m5_paid,
    COALESCE(c.claim_m25_exists, false) AS claim_m25_exists,
    COALESCE(c.claim_m25_paid, false) AS claim_m25_paid,
    -- Montos pagados
    COALESCE(c.paid_amount_m1, 0::numeric(12,2)) AS paid_amount_m1,
    COALESCE(c.paid_amount_m5, 0::numeric(12,2)) AS paid_amount_m5,
    COALESCE(c.paid_amount_m25, 0::numeric(12,2)) AS paid_amount_m25,
    COALESCE(c.total_paid_yango, 0::numeric(12,2)) AS total_paid_yango,
    -- 8) monto faltante por cobrar a Yango
    (m.expected_total_yango - COALESCE(c.total_paid_yango, 0::numeric(12,2))) AS amount_due_yango
FROM milestones_14d m
LEFT JOIN claims_aggregated c ON c.driver_id = m.driver_id
LEFT JOIN driver_info di ON di.driver_id = m.driver_id;

-- ============================================================================
-- Comentarios de la Vista
-- ============================================================================
COMMENT ON VIEW ops.v_cabinet_financial_14d IS 
'Fuente de verdad financiera para CABINET que permite determinar con exactitud qué conductores generan pago de Yango y detectar deudas por milestones no pagados. Responde sin ambigüedad: "Yango nos debe X soles por estos drivers y estos hitos". Grano: 1 fila por driver_id.';

COMMENT ON COLUMN ops.v_cabinet_financial_14d.driver_id IS 
'ID del conductor que entró por cabinet. Grano principal de la vista (1 fila por driver_id).';

COMMENT ON COLUMN ops.v_cabinet_financial_14d.driver_name IS 
'Nombre completo del conductor desde public.drivers.full_name. NULL si no existe en drivers.';

COMMENT ON COLUMN ops.v_cabinet_financial_14d.lead_date IS 
'Fecha de lead desde observational.v_conversion_metrics (origen del driver en cabinet).';

COMMENT ON COLUMN ops.v_cabinet_financial_14d.iso_week IS 
'Semana ISO en formato YYYY-WW calculada desde lead_date. NULL si lead_date es NULL.';

COMMENT ON COLUMN ops.v_cabinet_financial_14d.connected_flag IS 
'Flag indicando si el driver se conectó (first_connection_date IS NOT NULL). Fuente: observational.v_conversion_metrics.';

COMMENT ON COLUMN ops.v_cabinet_financial_14d.connected_date IS 
'Primera fecha de conexión del driver. Fuente: observational.v_conversion_metrics.first_connection_date.';

COMMENT ON COLUMN ops.v_cabinet_financial_14d.total_trips_14d IS 
'Total de viajes completados (count_orders_completed) dentro de la ventana de 14 días desde lead_date. Fuente: public.summary_daily.';

COMMENT ON COLUMN ops.v_cabinet_financial_14d.reached_m1_14d IS 
'Flag indicando si el driver alcanzó M1 dentro de la ventana de 14 días (total_trips_14d >= 1).';

COMMENT ON COLUMN ops.v_cabinet_financial_14d.reached_m5_14d IS 
'Flag indicando si el driver alcanzó M5 dentro de la ventana de 14 días (total_trips_14d >= 5).';

COMMENT ON COLUMN ops.v_cabinet_financial_14d.reached_m25_14d IS 
'Flag indicando si el driver alcanzó M25 dentro de la ventana de 14 días (total_trips_14d >= 25).';

COMMENT ON COLUMN ops.v_cabinet_financial_14d.expected_amount_m1 IS 
'Monto esperado para milestone M1 según reglas de negocio (milestone 1=25). Solo > 0 si reached_m1_14d = true.';

COMMENT ON COLUMN ops.v_cabinet_financial_14d.expected_amount_m5 IS 
'Monto esperado para milestone M5 según reglas de negocio (milestone 5=35). Solo > 0 si reached_m5_14d = true.';

COMMENT ON COLUMN ops.v_cabinet_financial_14d.expected_amount_m25 IS 
'Monto esperado para milestone M25 según reglas de negocio (milestone 25=100). Solo > 0 si reached_m25_14d = true.';

COMMENT ON COLUMN ops.v_cabinet_financial_14d.expected_total_yango IS 
'Total esperado acumulativo de Yango según milestones alcanzados dentro de ventana de 14 días. Suma de expected_amount_m1 + m5 + m25.';

COMMENT ON COLUMN ops.v_cabinet_financial_14d.claim_m1_exists IS 
'Flag indicando si existe un claim M1 en ops.v_claims_payment_status_cabinet para este driver.';

COMMENT ON COLUMN ops.v_cabinet_financial_14d.claim_m1_paid IS 
'Flag indicando si el claim M1 está pagado (paid_flag = true en ops.v_claims_payment_status_cabinet).';

COMMENT ON COLUMN ops.v_cabinet_financial_14d.claim_m5_exists IS 
'Flag indicando si existe un claim M5 en ops.v_claims_payment_status_cabinet para este driver.';

COMMENT ON COLUMN ops.v_cabinet_financial_14d.claim_m5_paid IS 
'Flag indicando si el claim M5 está pagado (paid_flag = true en ops.v_claims_payment_status_cabinet).';

COMMENT ON COLUMN ops.v_cabinet_financial_14d.claim_m25_exists IS 
'Flag indicando si existe un claim M25 en ops.v_claims_payment_status_cabinet para este driver.';

COMMENT ON COLUMN ops.v_cabinet_financial_14d.claim_m25_paid IS 
'Flag indicando si el claim M25 está pagado (paid_flag = true en ops.v_claims_payment_status_cabinet).';

COMMENT ON COLUMN ops.v_cabinet_financial_14d.paid_amount_m1 IS 
'Monto pagado para milestone M1. 0 si no hay claim o no está pagado.';

COMMENT ON COLUMN ops.v_cabinet_financial_14d.paid_amount_m5 IS 
'Monto pagado para milestone M5. 0 si no hay claim o no está pagado.';

COMMENT ON COLUMN ops.v_cabinet_financial_14d.paid_amount_m25 IS 
'Monto pagado para milestone M25. 0 si no hay claim o no está pagado.';

COMMENT ON COLUMN ops.v_cabinet_financial_14d.total_paid_yango IS 
'Total pagado por Yango (suma de paid_amount_m1 + m5 + m25).';

COMMENT ON COLUMN ops.v_cabinet_financial_14d.amount_due_yango IS 
'Monto faltante por cobrar a Yango (expected_total_yango - total_paid_yango). Valor positivo indica deuda pendiente.';

