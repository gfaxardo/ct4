-- ============================================================================
-- Script de Diagnóstico: Gap entre Claims M1 y UI
-- ============================================================================
-- PROPÓSITO:
-- Diagnosticar por qué la UI no refleja los claims M1 generados por el fix.
-- Verificar discrepancias entre fuentes de achieved y claims.
-- ============================================================================

SET statement_timeout = '120s';

-- ============================================================================
-- DIAGNÓSTICO 1: Comparar achieved flags entre fuentes
-- ============================================================================
WITH achieved_from_trips AS (
    SELECT DISTINCT driver_id
    FROM ops.v_cabinet_milestones_achieved_from_trips
    WHERE milestone_value = 1 AND achieved_flag = true
),
achieved_from_payment_calc AS (
    SELECT DISTINCT driver_id
    FROM ops.v_cabinet_milestones_achieved_from_payment_calc
    WHERE milestone_value = 1 AND achieved_flag = true
)
SELECT 
    'DIAG 1: M1 en trips pero NO en payment_calc' AS check_name,
    COUNT(*) AS count
FROM achieved_from_trips t
LEFT JOIN achieved_from_payment_calc p ON p.driver_id = t.driver_id
WHERE p.driver_id IS NULL

UNION ALL

SELECT 
    'DIAG 1: M1 en payment_calc pero NO en trips' AS check_name,
    COUNT(*) AS count
FROM achieved_from_payment_calc p
LEFT JOIN achieved_from_trips t ON t.driver_id = p.driver_id
WHERE t.driver_id IS NULL;

-- ============================================================================
-- DIAGNÓSTICO 2: Claims M1 generados vs achieved flags en driver_matrix
-- ============================================================================
WITH claims_m1 AS (
    SELECT DISTINCT driver_id
    FROM ops.v_claims_payment_status_cabinet
    WHERE milestone_value = 1
),
driver_matrix_m1 AS (
    SELECT 
        driver_id,
        m1_achieved_flag,
        m1_expected_amount_yango
    FROM ops.v_payments_driver_matrix_cabinet
    WHERE origin_tag = 'cabinet'
)
SELECT 
    'DIAG 2: Claims M1 generados' AS check_name,
    COUNT(*) AS total_claims_m1
FROM claims_m1

UNION ALL

SELECT 
    'DIAG 2: Drivers con m1_achieved_flag=true en driver_matrix' AS check_name,
    COUNT(*) AS count
FROM driver_matrix_m1
WHERE m1_achieved_flag = true

UNION ALL

SELECT 
    'DIAG 2: Drivers con m1_expected_amount_yango IS NOT NULL' AS check_name,
    COUNT(*) AS count
FROM driver_matrix_m1
WHERE m1_expected_amount_yango IS NOT NULL

UNION ALL

SELECT 
    'DIAG 2: Gap: claim M1 existe pero m1_achieved_flag=false' AS check_name,
    COUNT(*) AS count
FROM claims_m1 c
INNER JOIN driver_matrix_m1 dm ON dm.driver_id = c.driver_id
WHERE dm.m1_achieved_flag = false;

-- ============================================================================
-- DIAGNÓSTICO 3: Spot-check de drivers con claim M1 pero flag false
-- ============================================================================
WITH claims_m1 AS (
    SELECT DISTINCT driver_id
    FROM ops.v_claims_payment_status_cabinet
    WHERE milestone_value = 1
),
driver_matrix_m1 AS (
    SELECT 
        driver_id,
        m1_achieved_flag,
        m1_expected_amount_yango,
        m1_yango_payment_status
    FROM ops.v_payments_driver_matrix_cabinet
    WHERE origin_tag = 'cabinet'
),
achieved_from_trips AS (
    SELECT DISTINCT driver_id
    FROM ops.v_cabinet_milestones_achieved_from_trips
    WHERE milestone_value = 1 AND achieved_flag = true
),
achieved_from_payment_calc AS (
    SELECT DISTINCT driver_id
    FROM ops.v_cabinet_milestones_achieved_from_payment_calc
    WHERE milestone_value = 1 AND achieved_flag = true
)
SELECT 
    'DIAG 3: Spot-check gap M1' AS check_name,
    c.driver_id,
    dm.m1_achieved_flag AS driver_matrix_achieved_flag,
    dm.m1_expected_amount_yango,
    dm.m1_yango_payment_status,
    CASE WHEN t.driver_id IS NOT NULL THEN 'YES' ELSE 'NO' END AS in_trips,
    CASE WHEN p.driver_id IS NOT NULL THEN 'YES' ELSE 'NO' END AS in_payment_calc
FROM claims_m1 c
INNER JOIN driver_matrix_m1 dm ON dm.driver_id = c.driver_id
LEFT JOIN achieved_from_trips t ON t.driver_id = c.driver_id
LEFT JOIN achieved_from_payment_calc p ON p.driver_id = c.driver_id
WHERE dm.m1_achieved_flag = false
LIMIT 20;

-- ============================================================================
-- DIAGNÓSTICO 4: Resumen de fuentes de achieved
-- ============================================================================
SELECT 
    'DIAG 4: Resumen achieved M1 por fuente' AS check_name,
    'v_cabinet_milestones_achieved_from_trips' AS source,
    COUNT(DISTINCT driver_id) AS unique_drivers
FROM ops.v_cabinet_milestones_achieved_from_trips
WHERE milestone_value = 1 AND achieved_flag = true

UNION ALL

SELECT 
    'DIAG 4: Resumen achieved M1 por fuente' AS check_name,
    'v_cabinet_milestones_achieved_from_payment_calc' AS source,
    COUNT(DISTINCT driver_id) AS unique_drivers
FROM ops.v_cabinet_milestones_achieved_from_payment_calc
WHERE milestone_value = 1 AND achieved_flag = true

UNION ALL

SELECT 
    'DIAG 4: Resumen achieved M1 por fuente' AS check_name,
    'v_claims_payment_status_cabinet (claims generados)' AS source,
    COUNT(DISTINCT driver_id) AS unique_drivers
FROM ops.v_claims_payment_status_cabinet
WHERE milestone_value = 1

UNION ALL

SELECT 
    'DIAG 4: Resumen achieved M1 por fuente' AS check_name,
    'v_payments_driver_matrix_cabinet (m1_achieved_flag=true)' AS source,
    COUNT(DISTINCT driver_id) AS unique_drivers
FROM ops.v_payments_driver_matrix_cabinet
WHERE origin_tag = 'cabinet' AND m1_achieved_flag = true;

