-- ============================================================================
-- Script de Verificación: Claims Achieved Source Fix
-- ============================================================================
-- PROPÓSITO:
-- Verificar que el fix de source-of-truth para achieved de claims funciona
-- correctamente. Valida que:
-- (A) Claims inválidos (m5/m25 sin achieved en nueva vista) bajan a ~0
-- (B) No hay discrepancias entre claims y v_payment_calculation
-- (C) No hay duplicados en v_payments_driver_matrix_cabinet
-- (D) Spot-check de 20 drivers para auditoría
-- ============================================================================
-- INSTRUCCIONES:
-- Ejecutar después de aplicar:
-- 1. backend/sql/ops/v_cabinet_milestones_achieved_from_payment_calc.sql
-- 2. backend/sql/ops/v_claims_payment_status_cabinet.sql (si se modificó)
-- ============================================================================
-- NOTA: Si el entorno no permite SET statement_timeout, comentar la línea siguiente
-- y ejecutar con: psql ... -v statement_timeout=120000 ...
-- ============================================================================

SET statement_timeout = '120s';

-- ============================================================================
-- CHECK A: Conteo de "claims inválidos" (claims m5/m25 cuyo driver no aparece 
--          achieved en la nueva vista) -> esperado ~0
-- ============================================================================
-- NOTA: Antes no retornaba filas cuando count=0 porque GROUP BY solo devuelve
-- filas cuando hay matches. Ahora usamos CTE milestones + LEFT JOIN para
-- garantizar siempre 2 filas (milestone_value 5 y 25).
-- ============================================================================
WITH milestones AS (
    SELECT 5 AS milestone_value
    UNION ALL
    SELECT 25 AS milestone_value
),
invalid_counts AS (
    SELECT 
        c.milestone_value,
        COUNT(*) AS invalid_claims_count
    FROM ops.v_claims_payment_status_cabinet c
    LEFT JOIN ops.v_cabinet_milestones_achieved_from_payment_calc m
        ON m.driver_id = c.driver_id
        AND m.milestone_value = c.milestone_value
        AND m.achieved_flag = true
    WHERE c.milestone_value IN (5, 25)
        AND m.driver_id IS NULL
    GROUP BY c.milestone_value
)
SELECT 
    'CHECK A: Claims inválidos (m5/m25 sin achieved en nueva vista)' AS check_name,
    ms.milestone_value,
    COALESCE(ic.invalid_claims_count, 0) AS invalid_claims_count,
    CASE 
        WHEN COALESCE(ic.invalid_claims_count, 0) <= 5 THEN '✓ PASS (<= 5 inválidos, esperado ~0)'
        ELSE '✗ FAIL (> 5 inválidos)'
    END AS status
FROM milestones ms
LEFT JOIN invalid_counts ic ON ic.milestone_value = ms.milestone_value
ORDER BY ms.milestone_value;

-- ============================================================================
-- CHECK B: Conteo de discrepancias: drivers/milestones que están achieved 
--          en pc_agg (agregado) pero NO aparecen achieved en m (nueva vista)
--          -> esperado 0
-- ============================================================================
-- NOTA: Antes no retornaba filas cuando count=0 por GROUP BY. Ahora usamos
-- CTE milestones + LEFT JOIN para garantizar siempre 2 filas.
-- Comparación: pc_agg (agregado) vs m (nueva vista agregada) - apples-to-apples.
-- ============================================================================
WITH milestones AS (
    SELECT 5 AS milestone_value
    UNION ALL
    SELECT 25 AS milestone_value
),
pc_agg AS (
    -- Agregado de v_payment_calculation por driver_id + milestone_value
    SELECT
        driver_id,
        milestone_trips AS milestone_value,
        bool_or(milestone_achieved) AS achieved_flag
    FROM ops.v_payment_calculation
    WHERE origin_tag = 'cabinet'
        AND milestone_trips IN (5, 25)
        AND driver_id IS NOT NULL
    GROUP BY driver_id, milestone_trips
),
discrepancy_counts AS (
    SELECT 
        pc.milestone_value,
        COUNT(*) AS discrepancy_count
    FROM pc_agg pc
    WHERE pc.achieved_flag = true
        AND NOT EXISTS (
            SELECT 1
            FROM ops.v_cabinet_milestones_achieved_from_payment_calc m
            WHERE m.driver_id = pc.driver_id
                AND m.milestone_value = pc.milestone_value
                AND m.achieved_flag = true
        )
    GROUP BY pc.milestone_value
)
SELECT 
    'CHECK B: Discrepancias claims vs payment_calc' AS check_name,
    ms.milestone_value,
    COALESCE(dc.discrepancy_count, 0) AS discrepancy_count,
    CASE 
        WHEN COALESCE(dc.discrepancy_count, 0) = 0 THEN '✓ PASS (0 discrepancias)'
        ELSE '✗ FAIL (existen discrepancias)'
    END AS status
FROM milestones ms
LEFT JOIN discrepancy_counts dc ON dc.milestone_value = ms.milestone_value
ORDER BY ms.milestone_value;

-- ============================================================================
-- CHECK C: Duplicados en v_payments_driver_matrix_cabinet -> esperado 0
-- ============================================================================
SELECT 
    'CHECK C: Duplicados en driver_matrix' AS check_name,
    COUNT(*) AS duplicate_count,
    CASE 
        WHEN COUNT(*) = 0 THEN '✓ PASS (0 duplicados)'
        ELSE '✗ FAIL (existen duplicados)'
    END AS status
FROM (
    SELECT 
        driver_id,
        COUNT(*) AS driver_count
    FROM ops.v_payments_driver_matrix_cabinet
    GROUP BY driver_id
    HAVING COUNT(*) > 1
) duplicates;

-- ============================================================================
-- CHECK D: Spot-check - 20 drivers de claims con flags achieved en 
--          claim_view vs payment_calc para auditoría
-- ============================================================================
-- NOTA: Antes comparaba con filas crudas de v_payment_calculation, lo que
-- podía dar discrepancias falsas si elegía una fila con milestone_achieved=false.
-- Ahora compara agregado vs agregado: m (nueva vista) vs pc_agg (agregado).
-- ============================================================================
WITH pc_agg_check_d AS (
    -- Agregado de v_payment_calculation para CHECK D
    SELECT
        driver_id,
        milestone_trips AS milestone_value,
        bool_or(milestone_achieved) AS achieved_flag,
        min(achieved_date) FILTER (WHERE milestone_achieved) AS achieved_date
    FROM ops.v_payment_calculation
    WHERE origin_tag = 'cabinet'
        AND milestone_trips IN (5, 25)
        AND driver_id IS NOT NULL
    GROUP BY driver_id, milestone_trips
)
SELECT 
    'CHECK D: Spot-check 20 drivers' AS check_name,
    c.driver_id,
    c.milestone_value,
    c.lead_date,
    -- Flags desde claims view
    CASE WHEN c.driver_id IS NOT NULL THEN true ELSE false END AS claim_exists,
    -- Flags desde nueva vista de achieved (agregado)
    COALESCE(m.achieved_flag, false) AS achieved_in_new_view,
    m.achieved_date AS achieved_date_new_view,
    -- Flags desde payment_calculation agregado (agregado)
    COALESCE(pc.achieved_flag, false) AS achieved_in_payment_calc,
    pc.achieved_date AS achieved_date_payment_calc,
    -- Comparación: agregado vs agregado
    CASE 
        WHEN COALESCE(m.achieved_flag, false) = COALESCE(pc.achieved_flag, false) THEN '✓ ALIGNED'
        WHEN m.achieved_flag = false AND pc.achieved_flag = true THEN '⚠ DISCREPANCY (new view missing)'
        WHEN m.achieved_flag = true AND pc.achieved_flag = false THEN '⚠ DISCREPANCY (payment_calc missing)'
        ELSE '✗ BOTH MISSING'
    END AS alignment_status
FROM ops.v_claims_payment_status_cabinet c
LEFT JOIN ops.v_cabinet_milestones_achieved_from_payment_calc m
    ON m.driver_id = c.driver_id
    AND m.milestone_value = c.milestone_value
LEFT JOIN pc_agg_check_d pc
    ON pc.driver_id = c.driver_id
    AND pc.milestone_value = c.milestone_value
WHERE c.milestone_value IN (5, 25)
ORDER BY c.driver_id, c.milestone_value
LIMIT 20;

-- ============================================================================
-- CHECK M1-A: Conteo drivers donde pc_agg_m1=true pero driver_matrix.m1_achieved_flag != true
--          -> esperado 0
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
)
SELECT 
    'CHECK M1-A: Gap m1 achieved (pc vs driver_matrix)' AS check_name,
    COUNT(*) AS gap_count,
    CASE 
        WHEN COUNT(*) = 0 THEN '✓ PASS (0 gaps)'
        ELSE '✗ FAIL (existen gaps)'
    END AS status
FROM pc_agg_m1 pc
INNER JOIN ops.v_payments_driver_matrix_cabinet dm
    ON dm.driver_id = pc.driver_id
WHERE pc.m1_achieved_flag = true
    AND COALESCE(dm.m1_achieved_flag, false) != true;

-- ============================================================================
-- CHECK M1-B: Spot-check 20 drivers para m1 comparando pc_agg_m1 vs driver_matrix.m1_achieved_flag
-- ============================================================================
WITH pc_agg_m1 AS (
    SELECT
        driver_id,
        bool_or(milestone_achieved) AS m1_achieved_flag,
        min(achieved_date) FILTER (WHERE milestone_achieved) AS m1_achieved_date
    FROM ops.v_payment_calculation
    WHERE origin_tag = 'cabinet'
        AND milestone_trips = 1
        AND driver_id IS NOT NULL
    GROUP BY driver_id
)
SELECT 
    'CHECK M1-B: Spot-check 20 drivers m1' AS check_name,
    pc.driver_id,
    pc.m1_achieved_flag AS pc_m1_achieved,
    pc.m1_achieved_date AS pc_m1_date,
    dm.m1_achieved_flag AS driver_matrix_m1_achieved,
    dm.m1_achieved_date AS driver_matrix_m1_date,
    CASE 
        WHEN COALESCE(pc.m1_achieved_flag, false) = COALESCE(dm.m1_achieved_flag, false) THEN '✓ ALIGNED'
        WHEN pc.m1_achieved_flag = true AND COALESCE(dm.m1_achieved_flag, false) = false THEN '⚠ DISCREPANCY (driver_matrix missing)'
        WHEN pc.m1_achieved_flag = false AND dm.m1_achieved_flag = true THEN '⚠ DISCREPANCY (pc missing)'
        ELSE '✗ BOTH MISSING'
    END AS alignment_status
FROM pc_agg_m1 pc
LEFT JOIN ops.v_payments_driver_matrix_cabinet dm
    ON dm.driver_id = pc.driver_id
WHERE pc.m1_achieved_flag = true
ORDER BY pc.driver_id
LIMIT 20;

-- ============================================================================
-- RESUMEN: Conteos totales para contexto (versión ligera)
-- ============================================================================
-- NOTA: Antes hacía COUNT(*) sobre v_claims_payment_status_cabinet sin filtros
-- fuertes, lo que causaba timeout. Ahora usa CTEs agregados ya calculados
-- (m y pc_agg) que son más eficientes.
-- ============================================================================
WITH pc_agg_resumen AS (
    -- Agregado de v_payment_calculation para RESUMEN
    SELECT
        milestone_trips AS milestone_value,
        driver_id,
        bool_or(milestone_achieved) AS achieved_flag
    FROM ops.v_payment_calculation
    WHERE origin_tag = 'cabinet'
        AND milestone_trips IN (5, 25)
        AND driver_id IS NOT NULL
    GROUP BY milestone_trips, driver_id
),
pc_agg_summary AS (
    SELECT
        milestone_value,
        COUNT(*) AS achieved_count
    FROM pc_agg_resumen
    WHERE achieved_flag = true
    GROUP BY milestone_value
)
SELECT 
    'RESUMEN: Conteos totales' AS section,
    'Total achieved m5 (nueva vista)' AS metric,
    COUNT(*) AS count_value
FROM ops.v_cabinet_milestones_achieved_from_payment_calc
WHERE milestone_value = 5 AND achieved_flag = true
UNION ALL
SELECT 
    'RESUMEN: Conteos totales' AS section,
    'Total achieved m25 (nueva vista)' AS metric,
    COUNT(*) AS count_value
FROM ops.v_cabinet_milestones_achieved_from_payment_calc
WHERE milestone_value = 25 AND achieved_flag = true
UNION ALL
SELECT 
    'RESUMEN: Conteos totales' AS section,
    'Total achieved m5 (payment_calc agregado)' AS metric,
    COALESCE((SELECT achieved_count FROM pc_agg_summary WHERE milestone_value = 5), 0) AS count_value
UNION ALL
SELECT 
    'RESUMEN: Conteos totales' AS section,
    'Total achieved m25 (payment_calc agregado)' AS metric,
    COALESCE((SELECT achieved_count FROM pc_agg_summary WHERE milestone_value = 25), 0) AS count_value;
-- NOTA: Si necesitas el conteo de drivers en driver_matrix (puede ser pesado),
-- ejecutar aparte:
-- SELECT COUNT(DISTINCT driver_id) AS total_drivers FROM ops.v_payments_driver_matrix_cabinet;
