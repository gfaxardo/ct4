-- ============================================================================
-- Script de Verificación: Flags Achieved Cumulativos por Semana
-- ============================================================================
-- PROPÓSITO:
-- Verificar que después del fix, los achieved flags son cumulativos por semana
-- y que no hay inconsistencias M5 sin M1 en la misma semana.
-- ============================================================================

-- QUERY 1: Verificar que no hay filas donde m5_achieved_flag=true y m1_achieved_flag=false
-- en la MISMA semana (esto debería ser 0 tras el fix porque M5 implica M1 en acumulado)
SELECT 
    'INCONSISTENCIA M5 sin M1 (misma semana)' AS status,
    COUNT(*) AS count_inconsistencies
FROM ops.v_payments_driver_matrix_cabinet
WHERE m5_achieved_flag = true
    AND COALESCE(m1_achieved_flag, false) = false;

-- QUERY 2: Verificar que no hay duplicados por (driver_id, week_start, origin_tag)
SELECT 
    'DUPLICADOS POR GRANO' AS status,
    driver_id,
    week_start,
    origin_tag,
    COUNT(*) AS count_duplicates
FROM ops.v_payments_driver_matrix_cabinet
GROUP BY driver_id, week_start, origin_tag
HAVING COUNT(*) > 1
ORDER BY count_duplicates DESC
LIMIT 10;

-- QUERY 3: Verificar carry-forward: drivers con M1 en semana anterior y M5 en semana posterior
-- Debe mostrar que M1 aparece como true en la semana de M5 también
SELECT 
    'CARRY-FORWARD M1 A SEMANA POSTERIOR' AS status,
    driver_id,
    week_start,
    m1_achieved_flag,
    m1_achieved_date,
    m5_achieved_flag,
    m5_achieved_date,
    CASE 
        WHEN m1_achieved_date IS NOT NULL 
            AND m5_achieved_date IS NOT NULL
            AND DATE_TRUNC('week', m1_achieved_date)::date < DATE_TRUNC('week', m5_achieved_date)::date
            AND m1_achieved_flag = true
        THEN 'OK: M1 carry-forward correcto'
        WHEN m1_achieved_flag = false 
            AND m5_achieved_flag = true
        THEN 'ERROR: M1 no aparece aunque M5 sí'
        ELSE 'OK'
    END AS carry_forward_status
FROM ops.v_payments_driver_matrix_cabinet
WHERE m5_achieved_flag = true
    AND m1_achieved_date IS NOT NULL
    AND m5_achieved_date IS NOT NULL
    AND DATE_TRUNC('week', m1_achieved_date)::date < DATE_TRUNC('week', m5_achieved_date)::date
ORDER BY driver_id, week_start
LIMIT 20;

-- QUERY 4: Verificar que hay múltiples filas por driver cuando hay múltiples semanas
SELECT 
    'DRIVERS CON MULTIPLES SEMANAS' AS status,
    driver_id,
    COUNT(*) AS filas_por_driver,
    COUNT(DISTINCT week_start) AS semanas_distintas,
    array_agg(DISTINCT week_start ORDER BY week_start) AS semanas,
    MIN(week_start) AS primera_semana,
    MAX(week_start) AS ultima_semana
FROM ops.v_payments_driver_matrix_cabinet
GROUP BY driver_id
HAVING COUNT(DISTINCT week_start) > 1
ORDER BY semanas_distintas DESC
LIMIT 10;

-- QUERY 5: Verificar que achieved_date es la primera fecha real (mínima)
-- Comparar con v_cabinet_milestones_achieved_from_trips
SELECT 
    'VERIFICACION ACHIEVED_DATE (MINIMA)' AS status,
    m.driver_id,
    m.week_start,
    m.m1_achieved_date AS matrix_m1_date,
    dm_min.m1_min_date AS milestones_m1_min_date,
    CASE 
        WHEN m.m1_achieved_date = dm_min.m1_min_date THEN 'OK'
        ELSE 'ERROR: Fechas no coinciden'
    END AS m1_date_check,
    m.m5_achieved_date AS matrix_m5_date,
    dm_min.m5_min_date AS milestones_m5_min_date,
    CASE 
        WHEN m.m5_achieved_date = dm_min.m5_min_date THEN 'OK'
        ELSE 'ERROR: Fechas no coinciden'
    END AS m5_date_check
FROM ops.v_payments_driver_matrix_cabinet m
INNER JOIN (
    SELECT 
        driver_id,
        MIN(CASE WHEN milestone_value = 1 THEN achieved_date END) AS m1_min_date,
        MIN(CASE WHEN milestone_value = 5 THEN achieved_date END) AS m5_min_date
    FROM ops.v_cabinet_milestones_achieved_from_trips
    GROUP BY driver_id
) dm_min ON dm_min.driver_id = m.driver_id
WHERE m.m1_achieved_flag = true OR m.m5_achieved_flag = true
LIMIT 20;



