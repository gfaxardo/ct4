-- ============================================================================
-- Script de Verificación: No Claims sin Milestone Achieved
-- ============================================================================
-- PROPÓSITO:
-- Verificar que después del fix, NO existen claims sin milestone determinístico
-- ============================================================================

-- VERIFICACION 1: Drivers con claim M5 pero sin milestone M5 achieved (debe ser 0)
SELECT 
    'VERIFICACION 1: CLAIM M5 SIN MILESTONE M5 ACHIEVED' AS status,
    COUNT(*) AS count_violations
FROM ops.v_claims_payment_status_cabinet c
WHERE c.milestone_value = 5
    AND NOT EXISTS (
        SELECT 1
        FROM ops.v_cabinet_milestones_achieved_from_trips m
        WHERE m.driver_id = c.driver_id
            AND m.milestone_value = 5
            AND m.achieved_flag = true
    );

-- VERIFICACION 2: Drivers con claim M1 pero sin milestone M1 achieved (debe ser 0)
SELECT 
    'VERIFICACION 2: CLAIM M1 SIN MILESTONE M1 ACHIEVED' AS status,
    COUNT(*) AS count_violations
FROM ops.v_claims_payment_status_cabinet c
WHERE c.milestone_value = 1
    AND NOT EXISTS (
        SELECT 1
        FROM ops.v_cabinet_milestones_achieved_from_trips m
        WHERE m.driver_id = c.driver_id
            AND m.milestone_value = 1
            AND m.achieved_flag = true
    );

-- VERIFICACION 3: Drivers con claim M25 pero sin milestone M25 achieved (debe ser 0)
SELECT 
    'VERIFICACION 3: CLAIM M25 SIN MILESTONE M25 ACHIEVED' AS status,
    COUNT(*) AS count_violations
FROM ops.v_claims_payment_status_cabinet c
WHERE c.milestone_value = 25
    AND NOT EXISTS (
        SELECT 1
        FROM ops.v_cabinet_milestones_achieved_from_trips m
        WHERE m.driver_id = c.driver_id
            AND m.milestone_value = 25
            AND m.achieved_flag = true
    );

-- VERIFICACION 4: Resumen de violaciones por milestone (debe ser 0 para todos)
SELECT 
    'VERIFICACION 4: RESUMEN VIOLACIONES' AS status,
    c.milestone_value,
    COUNT(DISTINCT c.driver_id) AS drivers_con_violacion
FROM ops.v_claims_payment_status_cabinet c
WHERE NOT EXISTS (
    SELECT 1
    FROM ops.v_cabinet_milestones_achieved_from_trips m
    WHERE m.driver_id = c.driver_id
        AND m.milestone_value = c.milestone_value
        AND m.achieved_flag = true
)
GROUP BY c.milestone_value
ORDER BY c.milestone_value;

-- VERIFICACION 5: Drivers en Driver Matrix con payment_status pero achieved_flag = false (debe ser 0)
SELECT 
    'VERIFICACION 5: DRIVER MATRIX CON PAYMENT_STATUS SIN ACHIEVED' AS status,
    COUNT(*) AS count_violations
FROM ops.v_payments_driver_matrix_cabinet m
WHERE (
    (m.m1_yango_payment_status IS NOT NULL AND COALESCE(m.m1_achieved_flag, false) = false)
    OR (m.m5_yango_payment_status IS NOT NULL AND COALESCE(m.m5_achieved_flag, false) = false)
    OR (m.m25_yango_payment_status IS NOT NULL AND COALESCE(m.m25_achieved_flag, false) = false)
);

