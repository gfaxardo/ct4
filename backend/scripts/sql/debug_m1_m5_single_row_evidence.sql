-- ============================================================================
-- Script de Debug: M1/M5 con Grano 1 Fila por Driver
-- ============================================================================
-- OBJETIVO: Evidenciar el problema donde M5 aparece como achieved pero M1 no,
--          manteniendo el grano de 1 fila por driver_id.
-- ============================================================================

-- PASO 1: Encontrar drivers con M5 achieved pero M1 no achieved
SELECT 
    'INCONSISTENCIA M5 sin M1' AS status,
    driver_id,
    driver_name,
    week_start,
    origin_tag,
    m1_achieved_flag,
    m1_achieved_date,
    m5_achieved_flag,
    m5_achieved_date,
    m1_yango_payment_status,
    m5_yango_payment_status
FROM ops.v_payments_driver_matrix_cabinet
WHERE m5_achieved_flag = true
    AND COALESCE(m1_achieved_flag, false) = false
ORDER BY week_start DESC, driver_id
LIMIT 10;

-- PASO 2: Para un driver específico del PASO 1, mostrar milestones achieved (determinístico)
-- EJECUTAR DESPUÉS DE PASO 1, reemplazar 'DRIVER_ID_AQUI' con un driver_id del resultado
-- SELECT 
--     'MILESTONES ACHIEVED (DETERMINISTICO)' AS status,
--     driver_id,
--     milestone_value,
--     achieved_flag,
--     achieved_date,
--     trips_at_achieved
-- FROM ops.v_cabinet_milestones_achieved_from_trips
-- WHERE driver_id = 'DRIVER_ID_AQUI'
-- ORDER BY milestone_value, achieved_date;

-- PASO 3: Para ese mismo driver, mostrar la fila en la vista matrix actual
-- SELECT 
--     'FILA EN MATRIX ACTUAL' AS status,
--     driver_id,
--     driver_name,
--     week_start,
--     origin_tag,
--     m1_achieved_flag,
--     m1_achieved_date,
--     m5_achieved_flag,
--     m5_achieved_date,
--     m25_achieved_flag,
--     m25_achieved_date,
--     m1_yango_payment_status,
--     m5_yango_payment_status,
--     m1_expected_amount_yango,
--     m5_expected_amount_yango
-- FROM ops.v_payments_driver_matrix_cabinet
-- WHERE driver_id = 'DRIVER_ID_AQUI';

-- PASO 4: Verificar grano actual (debe ser 1 fila por driver)
SELECT 
    'VERIFICACION GRANO' AS status,
    COUNT(*) AS total_filas,
    COUNT(DISTINCT driver_id) AS total_drivers,
    COUNT(*) - COUNT(DISTINCT driver_id) AS filas_duplicadas,
    CASE 
        WHEN COUNT(*) = COUNT(DISTINCT driver_id) THEN 'OK: 1 fila por driver'
        ELSE 'ERROR: Hay duplicados'
    END AS grano_status
FROM ops.v_payments_driver_matrix_cabinet;

-- PASO 5: Drivers con múltiples filas (no debería haber)
SELECT 
    'DRIVERS CON MULTIPLES FILAS' AS status,
    driver_id,
    COUNT(*) AS count_filas,
    array_agg(DISTINCT week_start ORDER BY week_start) AS semanas
FROM ops.v_payments_driver_matrix_cabinet
GROUP BY driver_id
HAVING COUNT(*) > 1
ORDER BY count_filas DESC
LIMIT 10;

