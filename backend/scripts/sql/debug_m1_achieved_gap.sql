-- ============================================================================
-- Script de Debug: Gap M1 Achieved
-- ============================================================================
-- PROPÓSITO:
-- Identificar drivers donde payment_calculation indica milestone_trips=1 achieved=true
-- pero driver_matrix muestra m1_achieved_flag=false/null.
-- ============================================================================
-- Esto confirma si el bug está en SQL/view o solo en UI.
-- ============================================================================
-- NOTA: Si hay timeout, usar la vista canónica en lugar de agregar payment_calculation
-- ============================================================================

SET statement_timeout = '300s';

-- ============================================================================
-- Query 1: Drivers con m1 achieved en payment_calc pero NO en driver_matrix
-- ============================================================================
-- OPTIMIZADO: Usa la vista canónica en lugar de agregar payment_calculation
-- ============================================================================
SELECT 
    'GAP M1: pc_agg_m1=true pero driver_matrix.m1_achieved_flag != true' AS check_name,
    m.driver_id,
    m.achieved_flag AS pc_m1_achieved,
    m.achieved_date AS pc_m1_date,
    dm.m1_achieved_flag AS driver_matrix_m1_achieved,
    dm.m1_achieved_date AS driver_matrix_m1_date,
    dm.m5_achieved_flag AS driver_matrix_m5_achieved,
    dm.m25_achieved_flag AS driver_matrix_m25_achieved,
    -- Verificar si m1 existe en claims
    CASE WHEN c.driver_id IS NOT NULL THEN true ELSE false END AS exists_in_claims,
    c.milestone_value AS claim_milestone_value,
    c.paid_flag AS claim_paid_flag
FROM ops.v_cabinet_milestones_achieved_from_payment_calc m
INNER JOIN ops.v_payments_driver_matrix_cabinet dm
    ON dm.driver_id = m.driver_id
LEFT JOIN ops.v_claims_payment_status_cabinet c
    ON c.driver_id = m.driver_id
    AND c.milestone_value = 1
WHERE m.milestone_value = 1
    AND m.achieved_flag = true
    AND COALESCE(dm.m1_achieved_flag, false) != true
ORDER BY m.driver_id
LIMIT 10;

-- ============================================================================
-- Query 2: Conteo total del gap
-- ============================================================================
-- OPTIMIZADO: Usa la vista canónica
-- ============================================================================
SELECT 
    'TOTAL GAP M1' AS metric,
    COUNT(*) AS gap_count
FROM ops.v_cabinet_milestones_achieved_from_payment_calc m
INNER JOIN ops.v_payments_driver_matrix_cabinet dm
    ON dm.driver_id = m.driver_id
WHERE m.milestone_value = 1
    AND m.achieved_flag = true
    AND COALESCE(dm.m1_achieved_flag, false) != true;

-- ============================================================================
-- Query 3: Verificar si m1 está en claims cuando debería estar
-- ============================================================================
-- OPTIMIZADO: Usa DISTINCT en claims_m1 para mejor performance
-- ============================================================================
WITH pc_agg_m1 AS (
    SELECT
        driver_id,
        bool_or(milestone_achieved) AS m1_achieved_flag
    FROM ops.v_payment_calculation
    WHERE origin_tag = 'cabinet'
      AND milestone_trips = 1
      AND driver_id IS NOT NULL
    GROUP BY driver_id
),
claims_m1 AS (
    SELECT DISTINCT driver_id
    FROM ops.v_claims_payment_status_cabinet
    WHERE milestone_value = 1
)
SELECT
    'M1 en claims vs payment_calc' AS check_name,
    COUNT(*) FILTER (
        WHERE pc.m1_achieved_flag = true AND c.driver_id IS NULL
    ) AS m1_achieved_not_in_claims,
    COUNT(*) FILTER (
        WHERE pc.m1_achieved_flag = true AND c.driver_id IS NOT NULL
    ) AS m1_achieved_in_claims,
    COUNT(*) FILTER (
        WHERE pc.m1_achieved_flag = true
    ) AS total_m1_achieved
FROM pc_agg_m1 pc
LEFT JOIN claims_m1 c
  ON c.driver_id = pc.driver_id;

