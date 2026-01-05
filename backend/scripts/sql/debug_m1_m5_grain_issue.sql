-- ============================================================================
-- Script de Debug: Problema de Grano Temporal M1/M5
-- ============================================================================
-- OBJETIVO: Evidenciar el problema donde M5 aparece como achieved pero M1 no,
--          a pesar de que M1 fue alcanzado en una semana anterior.
-- ============================================================================

-- PASO 1: Encontrar drivers con M5 achieved pero M1 no achieved en la misma fila
-- (Esto debería ser imposible si M5 implica M1, a menos que haya problema de grano)
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

-- PASO 2: Para un driver específico del PASO 1, mostrar todas las filas en la vista matrix
-- EJECUTAR DESPUÉS DE PASO 1, reemplazar 'DRIVER_ID_AQUI' con un driver_id del resultado
-- SELECT 
--     'TODAS LAS FILAS DEL DRIVER EN MATRIX' AS status,
--     driver_id,
--     week_start,
--     origin_tag,
--     m1_achieved_flag,
--     m1_achieved_date,
--     m5_achieved_flag,
--     m5_achieved_date,
--     m25_achieved_flag,
--     m25_achieved_date,
--     m1_yango_payment_status,
--     m5_yango_payment_status
-- FROM ops.v_payments_driver_matrix_cabinet
-- WHERE driver_id = 'DRIVER_ID_AQUI'
-- ORDER BY week_start DESC;

-- PASO 3: Mostrar todos los milestones achieved desde v_cabinet_milestones_achieved_from_trips
-- para ese mismo driver (eventos puros, sin semana)
-- SELECT 
--     'MILESTONES ACHIEVED (EVENTOS PUROS)' AS status,
--     driver_id,
--     milestone_value,
--     achieved_flag,
--     achieved_date,
--     DATE_TRUNC('week', achieved_date)::date AS week_start_of_achieved_date,
--     trips_at_achieved
-- FROM ops.v_cabinet_milestones_achieved_from_trips
-- WHERE driver_id = 'DRIVER_ID_AQUI'
-- ORDER BY achieved_date;

-- PASO 3B: Comparar week_start de matrix vs achieved_date de milestones
-- SELECT 
--     'COMPARACION WEEK_START vs ACHIEVED_DATE' AS status,
--     m.driver_id,
--     m.week_start AS matrix_week_start,
--     m.m1_achieved_date,
--     m.m5_achieved_date,
--     DATE_TRUNC('week', m.m1_achieved_date)::date AS m1_week_start,
--     DATE_TRUNC('week', m.m5_achieved_date)::date AS m5_week_start,
--     CASE 
--         WHEN DATE_TRUNC('week', m.m1_achieved_date)::date < m.week_start THEN 'M1 en semana anterior'
--         WHEN DATE_TRUNC('week', m.m1_achieved_date)::date = m.week_start THEN 'M1 en misma semana'
--         WHEN DATE_TRUNC('week', m.m1_achieved_date)::date > m.week_start THEN 'M1 en semana posterior'
--         ELSE 'M1 sin fecha'
--     END AS m1_week_comparison
-- FROM ops.v_payments_driver_matrix_cabinet m
-- WHERE m.driver_id = 'DRIVER_ID_AQUI';

-- PASO 4: Comparar grano de ambas vistas
-- Matrix: grano por (driver_id, week_start, origin_tag) - pero actualmente parece ser solo driver_id
-- Milestones: grano por (driver_id, milestone_value) - eventos puros
SELECT 
    'GRANO MATRIX' AS status,
    driver_id,
    COUNT(*) AS filas_por_driver,
    COUNT(DISTINCT week_start) AS semanas_distintas,
    COUNT(DISTINCT origin_tag) AS origins_distintos,
    MIN(week_start) AS primera_semana,
    MAX(week_start) AS ultima_semana
FROM ops.v_payments_driver_matrix_cabinet
GROUP BY driver_id
HAVING COUNT(*) > 1
ORDER BY filas_por_driver DESC
LIMIT 10;

-- PASO 5: Verificar si hay drivers con múltiples filas (múltiples semanas)
-- Esto confirmaría si el grano actual es realmente por semana o solo por driver
SELECT 
    'DRIVERS CON MULTIPLES SEMANAS' AS status,
    driver_id,
    array_agg(DISTINCT week_start ORDER BY week_start) AS semanas,
    array_agg(DISTINCT origin_tag) AS origins
FROM ops.v_payments_driver_matrix_cabinet
GROUP BY driver_id
HAVING COUNT(DISTINCT week_start) > 1
ORDER BY COUNT(DISTINCT week_start) DESC
LIMIT 10;

