-- ============================================================================
-- Script de Verificación: Grano 1 Fila por Driver + Achieved Flags Cumulativos
-- ============================================================================
-- PROPÓSITO:
-- Verificar que después del fix:
-- 1. La vista tiene EXACTAMENTE 1 fila por driver_id (sin duplicados)
-- 2. Los achieved flags son cumulativos (si alguna vez alcanzó, siempre true)
-- 3. No hay inconsistencias M5 sin M1
-- ============================================================================

-- VERIFICACION 1: Duplicados por driver_id (debe ser 0 filas)
SELECT 
    'VERIFICACION 1: DUPLICADOS' AS status,
    driver_id,
    COUNT(*) AS count_duplicates
FROM ops.v_payments_driver_matrix_cabinet
GROUP BY driver_id
HAVING COUNT(*) > 1
ORDER BY count_duplicates DESC
LIMIT 10;

-- VERIFICACION 2: Coherencia cumulativa (debe ser 0 filas)
-- Filas donde m5_achieved_flag=true y m1_achieved_flag=false
-- Esto NO debería ocurrir porque M5 implica M1 en la vista determinística
SELECT 
    'VERIFICACION 2: INCONSISTENCIA M5 sin M1' AS status,
    COUNT(*) AS count_inconsistencies
FROM ops.v_payments_driver_matrix_cabinet
WHERE m5_achieved_flag = true
    AND COALESCE(m1_achieved_flag, false) = false;

-- VERIFICACION 3: Spot check de un driver específico
-- Comparar matrix vs vista determinística
-- EJECUTAR DESPUÉS DE ENCONTRAR UN DRIVER CON EL PROBLEMA, reemplazar 'DRIVER_ID_AQUI'
-- SELECT 
--     'VERIFICACION 3: SPOT CHECK DRIVER' AS status,
--     'MATRIX' AS fuente,
--     m.driver_id,
--     m.m1_achieved_flag AS matrix_m1_flag,
--     m.m1_achieved_date AS matrix_m1_date,
--     m.m5_achieved_flag AS matrix_m5_flag,
--     m.m5_achieved_date AS matrix_m5_date
-- FROM ops.v_payments_driver_matrix_cabinet m
-- WHERE m.driver_id = 'DRIVER_ID_AQUI'
-- UNION ALL
-- SELECT 
--     'VERIFICACION 3: SPOT CHECK DRIVER' AS status,
--     'DETERMINISTICO' AS fuente,
--     dm.driver_id,
--     BOOL_OR(dm.milestone_value = 1) AS matrix_m1_flag,
--     MIN(CASE WHEN dm.milestone_value = 1 THEN dm.achieved_date END) AS matrix_m1_date,
--     BOOL_OR(dm.milestone_value = 5) AS matrix_m5_flag,
--     MIN(CASE WHEN dm.milestone_value = 5 THEN dm.achieved_date END) AS matrix_m5_date
-- FROM ops.v_cabinet_milestones_achieved_from_trips dm
-- WHERE dm.driver_id = 'DRIVER_ID_AQUI'
-- GROUP BY dm.driver_id;

-- VERIFICACION 4: Verificar que achieved_date es MIN (primera fecha real)
SELECT 
    'VERIFICACION 4: ACHIEVED_DATE ES MIN' AS status,
    m.driver_id,
    m.m1_achieved_date AS matrix_m1_date,
    dm_min.m1_min_date AS deterministic_m1_min_date,
    CASE 
        WHEN m.m1_achieved_date = dm_min.m1_min_date THEN 'OK'
        WHEN m.m1_achieved_date IS NULL AND dm_min.m1_min_date IS NULL THEN 'OK (ambos NULL)'
        ELSE 'ERROR: Fechas no coinciden'
    END AS m1_date_check,
    m.m5_achieved_date AS matrix_m5_date,
    dm_min.m5_min_date AS deterministic_m5_min_date,
    CASE 
        WHEN m.m5_achieved_date = dm_min.m5_min_date THEN 'OK'
        WHEN m.m5_achieved_date IS NULL AND dm_min.m5_min_date IS NULL THEN 'OK (ambos NULL)'
        ELSE 'ERROR: Fechas no coinciden'
    END AS m5_date_check
FROM ops.v_payments_driver_matrix_cabinet m
INNER JOIN (
    SELECT 
        driver_id,
        MIN(CASE WHEN milestone_value = 1 THEN achieved_date END) AS m1_min_date,
        MIN(CASE WHEN milestone_value = 5 THEN achieved_date END) AS m5_min_date,
        MIN(CASE WHEN milestone_value = 25 THEN achieved_date END) AS m25_min_date
    FROM ops.v_cabinet_milestones_achieved_from_trips
    GROUP BY driver_id
) dm_min ON dm_min.driver_id = m.driver_id
WHERE (m.m1_achieved_flag = true OR m.m5_achieved_flag = true OR m.m25_achieved_flag = true)
    AND (m.m1_achieved_date != dm_min.m1_min_date 
         OR m.m5_achieved_date != dm_min.m5_min_date
         OR (m.m1_achieved_date IS NULL AND dm_min.m1_min_date IS NOT NULL)
         OR (m.m5_achieved_date IS NULL AND dm_min.m5_min_date IS NOT NULL))
LIMIT 20;

-- VERIFICACION 5: Resumen de grano
SELECT 
    'VERIFICACION 5: RESUMEN GRANO' AS status,
    COUNT(*) AS total_filas,
    COUNT(DISTINCT driver_id) AS total_drivers,
    COUNT(*) - COUNT(DISTINCT driver_id) AS filas_duplicadas,
    CASE 
        WHEN COUNT(*) = COUNT(DISTINCT driver_id) THEN 'OK: 1 fila por driver'
        ELSE 'ERROR: Hay duplicados'
    END AS grano_status
FROM ops.v_payments_driver_matrix_cabinet;

