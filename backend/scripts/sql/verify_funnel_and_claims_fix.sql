-- ============================================================================
-- Script de Verificación: Funnel C1 + Claims Fix + Origin Tag
-- ============================================================================
-- PROPÓSITO:
-- Verificar que todas las correcciones están aplicadas correctamente
-- ============================================================================

-- VERIFICACION 1: Duplicados de matrix (debe ser 0)
SELECT 
    'VERIFICACION 1: DUPLICADOS EN DRIVER MATRIX' AS status,
    COUNT(*) AS count_duplicates
FROM (
    SELECT driver_id, COUNT(*) AS cnt
    FROM ops.v_payments_driver_matrix_cabinet
    GROUP BY driver_id
    HAVING COUNT(*) > 1
) dup;

-- VERIFICACION 2: Claims inválidos (debe ser 0)
SELECT 
    'VERIFICACION 2: CLAIMS SIN MILESTONE ACHIEVED' AS status,
    COUNT(*) AS count_invalid_claims
FROM ops.v_claims_payment_status_cabinet c
WHERE NOT EXISTS (
    SELECT 1
    FROM ops.v_cabinet_milestones_achieved_from_trips m
    WHERE m.driver_id = c.driver_id
        AND m.milestone_value = c.milestone_value
        AND m.achieved_flag = true
);

-- VERIFICACION 3: Consistencia M5 sin M1 (debe ser 0)
SELECT 
    'VERIFICACION 3: M5 SIN M1' AS status,
    COUNT(*) AS count_inconsistencies
FROM ops.v_payments_driver_matrix_cabinet
WHERE m5_achieved_flag = true
    AND COALESCE(m1_achieved_flag, false) = false;

-- VERIFICACION 4: Origin_tag null (debe ser 0)
SELECT 
    'VERIFICACION 4: ORIGIN_TAG NULL' AS status,
    COUNT(*) AS count_null_origin
FROM ops.v_payments_driver_matrix_cabinet
WHERE origin_tag IS NULL;

-- VERIFICACION 5: Payment status sin achieved_flag (debe ser 0)
SELECT 
    'VERIFICACION 5: PAYMENT STATUS SIN ACHIEVED' AS status,
    COUNT(*) AS count_violations
FROM ops.v_payments_driver_matrix_cabinet
WHERE (
    (m1_yango_payment_status IS NOT NULL AND COALESCE(m1_achieved_flag, false) = false)
    OR (m5_yango_payment_status IS NOT NULL AND COALESCE(m5_achieved_flag, false) = false)
    OR (m25_yango_payment_status IS NOT NULL AND COALESCE(m25_achieved_flag, false) = false)
);

-- VERIFICACION 6: Distribución funnel_status
SELECT 
    'VERIFICACION 6: DISTRIBUCION FUNNEL_STATUS' AS status,
    funnel_status,
    COUNT(*) AS count_drivers
FROM ops.v_payments_driver_matrix_cabinet
GROUP BY funnel_status
ORDER BY 
    CASE funnel_status
        WHEN 'registered_incomplete' THEN 1
        WHEN 'registered_complete' THEN 2
        WHEN 'connected_no_trips' THEN 3
        WHEN 'reached_m1' THEN 4
        WHEN 'reached_m5' THEN 5
        WHEN 'reached_m25' THEN 6
        ELSE 7
    END;

-- VERIFICACION 7: Funnel status presente en todas las filas
SELECT 
    'VERIFICACION 7: FUNNEL_STATUS NULL' AS status,
    COUNT(*) AS count_null_funnel_status
FROM ops.v_payments_driver_matrix_cabinet
WHERE funnel_status IS NULL;

-- VERIFICACION 8: Highest milestone presente
SELECT 
    'VERIFICACION 8: HIGHEST_MILESTONE NULL (puede ser válido)' AS status,
    COUNT(*) AS count_null_highest_milestone
FROM ops.v_payments_driver_matrix_cabinet
WHERE highest_milestone IS NULL;

