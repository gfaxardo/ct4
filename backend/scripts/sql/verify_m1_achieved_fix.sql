-- ============================================================================
-- Script de Verificación: Fix de M1 Achieved Flag
-- ============================================================================
-- PROPÓSITO:
-- Verificar que después del fix, no existan drivers donde:
-- - ops.v_cabinet_milestones_achieved_from_trips dice M1 = true
-- - ops.v_payments_driver_matrix_cabinet dice M1 = false
--
-- RESULTADO ESPERADO:
-- Query 1: Debe retornar 0 filas (no hay inconsistencias)
-- Query 2: Muestra ejemplos de drivers con M1 achieved para validación manual
-- ============================================================================

-- ============================================================================
-- QUERY 1: Detectar inconsistencias M1 (debe retornar 0 filas)
-- ============================================================================
SELECT 
    'INCONSISTENCIA DETECTADA' AS status,
    dm.driver_id,
    dm.m1_achieved_flag AS deterministic_m1_achieved,
    vdm.m1_achieved_flag AS matrix_m1_achieved,
    dm.m1_achieved_date AS deterministic_m1_date,
    vdm.m1_achieved_date AS matrix_m1_date,
    vdm.driver_name
FROM (
    SELECT 
        driver_id,
        BOOL_OR(milestone_value = 1 AND achieved_flag = true) AS m1_achieved_flag,
        MAX(CASE WHEN milestone_value = 1 THEN achieved_date END) AS m1_achieved_date
    FROM ops.v_cabinet_milestones_achieved_from_trips
    GROUP BY driver_id
) dm
INNER JOIN ops.v_payments_driver_matrix_cabinet vdm
    ON vdm.driver_id = dm.driver_id
WHERE dm.m1_achieved_flag = true
    AND COALESCE(vdm.m1_achieved_flag, false) = false;

-- ============================================================================
-- QUERY 2: Ejemplos de drivers con M1 achieved (para validación manual)
-- ============================================================================
SELECT 
    'EJEMPLO M1 ACHIEVED' AS status,
    dm.driver_id,
    dm.m1_achieved_flag AS deterministic_m1_achieved,
    vdm.m1_achieved_flag AS matrix_m1_achieved,
    dm.m1_achieved_date AS deterministic_m1_date,
    vdm.m1_achieved_date AS matrix_m1_date,
    vdm.driver_name,
    vdm.m1_expected_amount_yango,
    vdm.m1_yango_payment_status,
    vdm.m1_window_status,
    vdm.m1_overdue_days
FROM (
    SELECT 
        driver_id,
        BOOL_OR(milestone_value = 1 AND achieved_flag = true) AS m1_achieved_flag,
        MAX(CASE WHEN milestone_value = 1 THEN achieved_date END) AS m1_achieved_date
    FROM ops.v_cabinet_milestones_achieved_from_trips
    GROUP BY driver_id
) dm
INNER JOIN ops.v_payments_driver_matrix_cabinet vdm
    ON vdm.driver_id = dm.driver_id
WHERE dm.m1_achieved_flag = true
    AND COALESCE(vdm.m1_achieved_flag, false) = true
LIMIT 10;

-- ============================================================================
-- QUERY 3: Comparación M1 vs M5 (debe mostrar consistencia)
-- ============================================================================
SELECT 
    'COMPARACIÓN M1 vs M5' AS status,
    vdm.driver_id,
    vdm.driver_name,
    vdm.m1_achieved_flag,
    vdm.m5_achieved_flag,
    vdm.m1_achieved_date,
    vdm.m5_achieved_date,
    CASE 
        WHEN vdm.m5_achieved_flag = true AND vdm.m1_achieved_flag = false 
        THEN 'INCONSISTENCIA: M5 sin M1'
        WHEN vdm.m1_achieved_flag = true AND vdm.m5_achieved_flag = false
        THEN 'OK: M1 sin M5 (esperado)'
        WHEN vdm.m1_achieved_flag = true AND vdm.m5_achieved_flag = true
        THEN 'OK: Ambos achieved'
        ELSE 'OK: Ninguno achieved'
    END AS consistency_status
FROM ops.v_payments_driver_matrix_cabinet vdm
WHERE vdm.m1_achieved_flag = true OR vdm.m5_achieved_flag = true
ORDER BY vdm.m1_achieved_flag DESC, vdm.m5_achieved_flag DESC
LIMIT 20;

-- ============================================================================
-- QUERY 4: Conteo de drivers por estado M1
-- ============================================================================
SELECT 
    'RESUMEN M1' AS status,
    COUNT(*) FILTER (WHERE m1_achieved_flag = true) AS m1_achieved_count,
    COUNT(*) FILTER (WHERE m1_achieved_flag = false) AS m1_not_achieved_count,
    COUNT(*) FILTER (WHERE m1_achieved_flag IS NULL) AS m1_null_count,
    COUNT(*) AS total_drivers
FROM ops.v_payments_driver_matrix_cabinet;

-- ============================================================================
-- QUERY 5: Drivers con M5 achieved pero sin M1 (debe ser 0 o muy bajo)
-- ============================================================================
SELECT 
    'M5 SIN M1' AS status,
    COUNT(*) AS count_m5_without_m1
FROM ops.v_payments_driver_matrix_cabinet
WHERE m5_achieved_flag = true
    AND COALESCE(m1_achieved_flag, false) = false;


