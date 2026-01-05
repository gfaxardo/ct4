-- ============================================================================
-- Queries de Auditoría: Driver Matrix Achieved vs Vista Determinística
-- ============================================================================
-- PROPÓSITO:
-- Validar inconsistencias entre achieved en Driver Matrix (v_payment_calculation)
-- y achieved determinístico (v_ct4_milestones_achieved_from_trips_eligible).
--
-- CONTEXTO:
-- Driver Matrix usa ops.v_payment_calculation que permite M5 achieved sin M1.
-- Vista determinística garantiza consistencia (M5 → M1, M25 → M5 y M1).
-- ============================================================================
-- INSTRUCCIONES DE USO:
-- 1. Ejecutar cada query por separado (Q1, Q2, Q3, Q4)
-- 2. NO ejecutar queries parciales que incluyan solo parte de un comentario /* */
-- 3. Si hay timeout, usar versión con LIMIT primero
-- ============================================================================

-- ============================================================================
-- Q1: Drivers donde Driver Matrix reporta M5=1 y M1=0
-- ============================================================================
-- Muestra driver_id y flags de achieved para drivers con inconsistencia M5 sin M1.
-- ============================================================================
SELECT 
    dm.driver_id,
    dm.person_key,
    dm.origin_tag,
    dm.driver_name,
    dm.lead_date,
    -- Flags de achieved desde Driver Matrix
    dm.m1_achieved_flag AS driver_matrix_m1_achieved,
    dm.m5_achieved_flag AS driver_matrix_m5_achieved,
    dm.m25_achieved_flag AS driver_matrix_m25_achieved,
    -- Fechas de achieved desde Driver Matrix
    dm.m1_achieved_date AS driver_matrix_m1_date,
    dm.m5_achieved_date AS driver_matrix_m5_date,
    dm.m25_achieved_date AS driver_matrix_m25_date,
    -- Flags de inconsistencia
    dm.m5_without_m1_flag,
    dm.m25_without_m5_flag,
    dm.milestone_inconsistency_notes
FROM ops.v_payments_driver_matrix_cabinet dm
WHERE dm.m5_achieved_flag = true
    AND COALESCE(dm.m1_achieved_flag, false) = false
ORDER BY dm.driver_id
LIMIT 100;

-- ============================================================================
-- Q2: Esos mismos drivers cruzados con vista determinística (OPTIMIZADO)
-- ============================================================================
-- Muestra que en la vista determinística M1 sí existe para esos drivers.
-- OPTIMIZACIÓN: Primero obtener set pequeño de driver_id inconsistentes,
-- luego cruzar solo esos driver_id contra vista determinística.
-- ============================================================================
-- Versión rápida (LIMIT 200): Para auditoría rápida
-- ============================================================================
WITH driver_matrix_inconsistencies AS (
    -- Drivers con M5=1 y M1=0 en Driver Matrix (LIMIT para evitar timeout)
    SELECT 
        dm.driver_id,
        dm.person_key,
        dm.origin_tag,
        dm.driver_name,
        dm.m1_achieved_flag AS dm_m1,
        dm.m5_achieved_flag AS dm_m5,
        dm.m25_achieved_flag AS dm_m25,
        dm.m5_without_m1_flag
    FROM ops.v_payments_driver_matrix_cabinet dm
    WHERE dm.m5_achieved_flag = true
        AND COALESCE(dm.m1_achieved_flag, false) = false
    LIMIT 200  -- Configurable: aumentar si se necesita más
),
trips_achieved_filtered AS (
    -- Solo milestones para los driver_id inconsistentes (evita scan completo)
    SELECT 
        driver_id,
        milestone_value,
        achieved_date,
        trips_at_achieved
    FROM ops.v_ct4_milestones_achieved_from_trips_eligible
    WHERE driver_id IN (SELECT driver_id FROM driver_matrix_inconsistencies)
)
SELECT 
    dmi.driver_id,
    dmi.person_key,
    dmi.origin_tag,
    dmi.driver_name,
    -- Driver Matrix
    dmi.dm_m1 AS driver_matrix_m1,
    dmi.dm_m5 AS driver_matrix_m5,
    dmi.dm_m25 AS driver_matrix_m25,
    dmi.m5_without_m1_flag AS driver_matrix_inconsistency,
    -- Vista Determinística
    CASE WHEN t1.driver_id IS NOT NULL THEN true ELSE false END AS trips_has_m1,
    CASE WHEN t5.driver_id IS NOT NULL THEN true ELSE false END AS trips_has_m5,
    CASE WHEN t25.driver_id IS NOT NULL THEN true ELSE false END AS trips_has_m25,
    -- Fechas desde vista determinística
    t1.achieved_date AS trips_m1_date,
    t1.trips_at_achieved AS trips_m1_trips,
    t5.achieved_date AS trips_m5_date,
    t5.trips_at_achieved AS trips_m5_trips,
    t25.achieved_date AS trips_m25_date,
    t25.trips_at_achieved AS trips_m25_trips
FROM driver_matrix_inconsistencies dmi
LEFT JOIN trips_achieved_filtered t1 
    ON t1.driver_id = dmi.driver_id AND t1.milestone_value = 1
LEFT JOIN trips_achieved_filtered t5 
    ON t5.driver_id = dmi.driver_id AND t5.milestone_value = 5
LEFT JOIN trips_achieved_filtered t25 
    ON t25.driver_id = dmi.driver_id AND t25.milestone_value = 25
ORDER BY dmi.driver_id;

/*
-- ============================================================================
-- Q2 SIN LIMIT (para análisis completo - puede ser lento)
-- ============================================================================
-- Descomentar y ejecutar solo si se necesita análisis completo.
-- Puede requerir aumentar statement_timeout.
-- ============================================================================
WITH driver_matrix_inconsistencies AS (
    SELECT 
        dm.driver_id,
        dm.person_key,
        dm.origin_tag,
        dm.driver_name,
        dm.m1_achieved_flag AS dm_m1,
        dm.m5_achieved_flag AS dm_m5,
        dm.m25_achieved_flag AS dm_m25,
        dm.m5_without_m1_flag
    FROM ops.v_payments_driver_matrix_cabinet dm
    WHERE dm.m5_achieved_flag = true
        AND COALESCE(dm.m1_achieved_flag, false) = false
    -- SIN LIMIT
),
trips_achieved_filtered AS (
    SELECT 
        driver_id,
        milestone_value,
        achieved_date,
        trips_at_achieved
    FROM ops.v_ct4_milestones_achieved_from_trips_eligible
    WHERE driver_id IN (SELECT driver_id FROM driver_matrix_inconsistencies)
)
SELECT 
    dmi.driver_id,
    dmi.person_key,
    dmi.origin_tag,
    dmi.driver_name,
    dmi.dm_m1 AS driver_matrix_m1,
    dmi.dm_m5 AS driver_matrix_m5,
    dmi.dm_m25 AS driver_matrix_m25,
    dmi.m5_without_m1_flag AS driver_matrix_inconsistency,
    CASE WHEN t1.driver_id IS NOT NULL THEN true ELSE false END AS trips_has_m1,
    CASE WHEN t5.driver_id IS NOT NULL THEN true ELSE false END AS trips_has_m5,
    CASE WHEN t25.driver_id IS NOT NULL THEN true ELSE false END AS trips_has_m25,
    t1.achieved_date AS trips_m1_date,
    t1.trips_at_achieved AS trips_m1_trips,
    t5.achieved_date AS trips_m5_date,
    t5.trips_at_achieved AS trips_m5_trips,
    t25.achieved_date AS trips_m25_date,
    t25.trips_at_achieved AS trips_m25_trips
FROM driver_matrix_inconsistencies dmi
LEFT JOIN trips_achieved_filtered t1 
    ON t1.driver_id = dmi.driver_id AND t1.milestone_value = 1
LEFT JOIN trips_achieved_filtered t5 
    ON t5.driver_id = dmi.driver_id AND t5.milestone_value = 5
LEFT JOIN trips_achieved_filtered t25 
    ON t25.driver_id = dmi.driver_id AND t25.milestone_value = 25
ORDER BY dmi.driver_id;
*/

-- ============================================================================
-- Q3: Sample 50 drivers comparando ambas fuentes
-- ============================================================================
-- Comparación lado a lado de achieved desde Driver Matrix vs vista determinística.
-- ============================================================================
WITH driver_matrix_flags AS (
    -- Flags de achieved desde Driver Matrix
    SELECT 
        dm.driver_id,
        dm.person_key,
        dm.origin_tag,
        dm.driver_name,
        COALESCE(dm.m1_achieved_flag, false) AS driver_matrix_has_m1,
        COALESCE(dm.m5_achieved_flag, false) AS driver_matrix_has_m5,
        COALESCE(dm.m25_achieved_flag, false) AS driver_matrix_has_m25,
        dm.m1_achieved_date AS driver_matrix_m1_date,
        dm.m5_achieved_date AS driver_matrix_m5_date,
        dm.m25_achieved_date AS driver_matrix_m25_date
    FROM ops.v_payments_driver_matrix_cabinet dm
    WHERE dm.origin_tag IN ('cabinet', 'fleet_migration')
    LIMIT 50
),
trips_flags AS (
    -- Flags de achieved desde vista determinística (pivoteado)
    -- FIX: Usar BOOL_OR en lugar de MAX(boolean) para evitar errores
    SELECT 
        driver_id,
        BOOL_OR(milestone_value = 1) AS trips_has_m1,
        BOOL_OR(milestone_value = 5) AS trips_has_m5,
        BOOL_OR(milestone_value = 25) AS trips_has_m25,
        MAX(CASE WHEN milestone_value = 1 THEN achieved_date END) AS trips_m1_date,
        MAX(CASE WHEN milestone_value = 5 THEN achieved_date END) AS trips_m5_date,
        MAX(CASE WHEN milestone_value = 25 THEN achieved_date END) AS trips_m25_date,
        MAX(CASE WHEN milestone_value = 1 THEN trips_at_achieved END) AS trips_m1_trips,
        MAX(CASE WHEN milestone_value = 5 THEN trips_at_achieved END) AS trips_m5_trips,
        MAX(CASE WHEN milestone_value = 25 THEN trips_at_achieved END) AS trips_m25_trips
    FROM ops.v_ct4_milestones_achieved_from_trips_eligible
    WHERE driver_id IN (SELECT driver_id FROM driver_matrix_flags)  -- OPTIMIZACIÓN: solo drivers del sample
    GROUP BY driver_id
)
SELECT 
    dmf.driver_id,
    dmf.person_key,
    dmf.origin_tag,
    dmf.driver_name,
    -- Driver Matrix
    dmf.driver_matrix_has_m1,
    dmf.driver_matrix_has_m5,
    dmf.driver_matrix_has_m25,
    dmf.driver_matrix_m1_date,
    dmf.driver_matrix_m5_date,
    dmf.driver_matrix_m25_date,
    -- Vista Determinística
    COALESCE(tf.trips_has_m1, false) AS trips_has_m1,
    COALESCE(tf.trips_has_m5, false) AS trips_has_m5,
    COALESCE(tf.trips_has_m25, false) AS trips_has_m25,
    tf.trips_m1_date,
    tf.trips_m5_date,
    tf.trips_m25_date,
    tf.trips_m1_trips,
    tf.trips_m5_trips,
    tf.trips_m25_trips,
    -- Comparación (diferencias)
    CASE 
        WHEN dmf.driver_matrix_has_m1 != COALESCE(tf.trips_has_m1, false) THEN 'M1_DIFF'
        WHEN dmf.driver_matrix_has_m5 != COALESCE(tf.trips_has_m5, false) THEN 'M5_DIFF'
        WHEN dmf.driver_matrix_has_m25 != COALESCE(tf.trips_has_m25, false) THEN 'M25_DIFF'
        WHEN dmf.driver_matrix_has_m5 = true AND dmf.driver_matrix_has_m1 = false THEN 'M5_WITHOUT_M1'
        WHEN dmf.driver_matrix_has_m25 = true AND dmf.driver_matrix_has_m5 = false THEN 'M25_WITHOUT_M5'
        ELSE 'OK'
    END AS comparison_status
FROM driver_matrix_flags dmf
LEFT JOIN trips_flags tf ON tf.driver_id = dmf.driver_id
ORDER BY 
    CASE 
        WHEN dmf.driver_matrix_has_m1 != COALESCE(tf.trips_has_m1, false) THEN 3
        WHEN dmf.driver_matrix_has_m5 != COALESCE(tf.trips_has_m5, false) THEN 4
        WHEN dmf.driver_matrix_has_m25 != COALESCE(tf.trips_has_m25, false) THEN 5
        WHEN dmf.driver_matrix_has_m5 = true AND dmf.driver_matrix_has_m1 = false THEN 1
        WHEN dmf.driver_matrix_has_m25 = true AND dmf.driver_matrix_has_m5 = false THEN 2
        ELSE 6
    END,
    dmf.driver_id;

-- ============================================================================
-- EXPLAIN y Recomendaciones de Índices
-- ============================================================================
-- Para analizar performance, ejecutar:
-- EXPLAIN ANALYZE SELECT ... (copiar query Q2 o Q3)
--
-- Índices recomendados (si no existen):
-- CREATE INDEX IF NOT EXISTS idx_v_ct4_milestones_achieved_from_trips_eligible_driver_milestone 
--     ON ops.v_ct4_milestones_achieved_from_trips_eligible(driver_id, milestone_value);
-- CREATE INDEX IF NOT EXISTS idx_v_payments_driver_matrix_cabinet_driver_origin 
--     ON ops.v_payments_driver_matrix_cabinet(driver_id, origin_tag) 
--     WHERE m5_achieved_flag = true AND COALESCE(m1_achieved_flag, false) = false;
-- ============================================================================

-- ============================================================================
-- Query Adicional: Resumen de Inconsistencias
-- ============================================================================
-- Cuenta total de inconsistencias por tipo.
-- ============================================================================
SELECT 
    'M5 sin M1 en Driver Matrix' AS inconsistency_type,
    COUNT(*) AS count_drivers
FROM ops.v_payments_driver_matrix_cabinet
WHERE m5_achieved_flag = true
    AND COALESCE(m1_achieved_flag, false) = false
UNION ALL
SELECT 
    'M25 sin M5 en Driver Matrix' AS inconsistency_type,
    COUNT(*) AS count_drivers
FROM ops.v_payments_driver_matrix_cabinet
WHERE m25_achieved_flag = true
    AND COALESCE(m5_achieved_flag, false) = false
UNION ALL
SELECT 
    'M25 sin M1 en Driver Matrix' AS inconsistency_type,
    COUNT(*) AS count_drivers
FROM ops.v_payments_driver_matrix_cabinet
WHERE m25_achieved_flag = true
    AND COALESCE(m1_achieved_flag, false) = false
UNION ALL
SELECT 
    'Total drivers en Driver Matrix' AS inconsistency_type,
    COUNT(*) AS count_drivers
FROM ops.v_payments_driver_matrix_cabinet
WHERE origin_tag IN ('cabinet', 'fleet_migration')
UNION ALL
SELECT 
    'Total drivers en vista determinística' AS inconsistency_type,
    COUNT(DISTINCT driver_id) AS count_drivers
FROM ops.v_ct4_milestones_achieved_from_trips_eligible;

