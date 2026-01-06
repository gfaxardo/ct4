-- ============================================================================
-- Script de Verificación: Consistencia de Generación de Claims Cabinet
-- ============================================================================
-- PROPÓSITO:
-- Verificar que la generación de claims para cabinet sea consistente:
-- - M1, M5, M25 se generan independientemente cuando están achieved
-- - No existen casos de claim M5 sin claim M1 cuando M1 está achieved
-- - No hay duplicados por grano (driver_id + milestone_value)
-- - Montos esperados son correctos (M1=25, M5=35, M25=100)
-- ============================================================================
-- FIX APLICADO:
-- - v_claims_payment_status_cabinet usa v_cabinet_milestones_achieved_from_payment_calc
-- - Agregado canónico de v_payment_calculation para evitar duplicados
-- - Validación explícita de ventana de 14 días
-- - Catálogo centralizado de montos (milestone_amounts CTE)
-- ============================================================================

SET statement_timeout = '120s';

-- ============================================================================
-- CHECK 1: Drivers con M1 achieved en ventana pero sin claim M1
-- ============================================================================
WITH m1_achieved_in_window AS (
    -- M1 achieved desde payment_calc (source-of-truth)
    SELECT 
        m.driver_id,
        m.milestone_value,
        m.achieved_flag,
        m.achieved_date,
        pc.lead_date,
        (pc.lead_date + INTERVAL '14 days')::date AS due_date
    FROM ops.v_cabinet_milestones_achieved_from_payment_calc m
    INNER JOIN ops.v_payment_calculation pc
        ON pc.driver_id = m.driver_id
        AND pc.milestone_trips = m.milestone_value
        AND pc.origin_tag = 'cabinet'
        AND pc.rule_scope = 'partner'
        AND pc.milestone_achieved = true
    WHERE m.milestone_value = 1
        AND m.achieved_flag = true
        -- Ventana de 14 días: achieved_date debe estar dentro de lead_date + 14 días
        AND m.achieved_date::date <= (pc.lead_date + INTERVAL '14 days')::date
        AND m.achieved_date::date >= pc.lead_date
),
m1_claims AS (
    -- Claims M1 existentes
    SELECT DISTINCT
        driver_id,
        milestone_value
    FROM ops.v_claims_payment_status_cabinet
    WHERE milestone_value = 1
)
SELECT 
    'CHECK 1: M1 achieved en ventana sin claim M1' AS check_name,
    COUNT(*) AS count_missing_claims,
    CASE 
        WHEN COUNT(*) = 0 THEN '✓ PASS'
        ELSE '✗ FAIL'
    END AS status
FROM m1_achieved_in_window m1
LEFT JOIN m1_claims c
    ON c.driver_id = m1.driver_id
    AND c.milestone_value = m1.milestone_value
WHERE c.driver_id IS NULL;

-- ============================================================================
-- CHECK 2: Casos donde existe claim M5 pero no claim M1 (BUG)
-- ============================================================================
WITH m1_achieved_in_window AS (
    -- M1 achieved desde payment_calc
    SELECT DISTINCT
        m.driver_id
    FROM ops.v_cabinet_milestones_achieved_from_payment_calc m
    INNER JOIN ops.v_payment_calculation pc
        ON pc.driver_id = m.driver_id
        AND pc.milestone_trips = m.milestone_value
        AND pc.origin_tag = 'cabinet'
        AND pc.rule_scope = 'partner'
        AND pc.milestone_achieved = true
    WHERE m.milestone_value = 1
        AND m.achieved_flag = true
        AND m.achieved_date::date <= (pc.lead_date + INTERVAL '14 days')::date
        AND m.achieved_date::date >= pc.lead_date
),
m5_claims AS (
    -- Claims M5 existentes
    SELECT DISTINCT
        driver_id
    FROM ops.v_claims_payment_status_cabinet
    WHERE milestone_value = 5
),
m1_claims AS (
    -- Claims M1 existentes
    SELECT DISTINCT
        driver_id
    FROM ops.v_claims_payment_status_cabinet
    WHERE milestone_value = 1
)
SELECT 
    'CHECK 2: Claim M5 sin claim M1 (cuando M1 achieved)' AS check_name,
    COUNT(*) AS count_inconsistencies,
    CASE 
        WHEN COUNT(*) = 0 THEN '✓ PASS'
        ELSE '✗ FAIL'
    END AS status
FROM m5_claims m5
INNER JOIN m1_achieved_in_window m1_achieved
    ON m1_achieved.driver_id = m5.driver_id
LEFT JOIN m1_claims m1
    ON m1.driver_id = m5.driver_id
WHERE m1.driver_id IS NULL;

-- ============================================================================
-- CHECK 3: Duplicados por grano (driver_id + milestone_value)
-- ============================================================================
SELECT 
    'CHECK 3: Duplicados por (driver_id + milestone_value)' AS check_name,
    COUNT(*) AS count_duplicates,
    CASE 
        WHEN COUNT(*) = 0 THEN '✓ PASS'
        ELSE '✗ FAIL'
    END AS status
FROM (
    SELECT 
        driver_id,
        milestone_value,
        COUNT(*) AS cnt
    FROM ops.v_claims_payment_status_cabinet
    WHERE milestone_value IN (1, 5, 25)
    GROUP BY driver_id, milestone_value
    HAVING COUNT(*) > 1
) dupes;

-- ============================================================================
-- CHECK 4: Validación de montos esperados
-- ============================================================================
SELECT 
    'CHECK 4: Expected amount por milestone' AS check_name,
    milestone_value,
    COUNT(*) AS count_claims,
    COUNT(DISTINCT expected_amount) AS distinct_amounts,
    MIN(expected_amount) AS min_amount,
    MAX(expected_amount) AS max_amount,
    CASE 
        WHEN milestone_value = 1 AND MIN(expected_amount) = 25 AND MAX(expected_amount) = 25 THEN '✓ PASS'
        WHEN milestone_value = 5 AND MIN(expected_amount) = 35 AND MAX(expected_amount) = 35 THEN '✓ PASS'
        WHEN milestone_value = 25 AND MIN(expected_amount) = 100 AND MAX(expected_amount) = 100 THEN '✓ PASS'
        ELSE '✗ FAIL'
    END AS status
FROM ops.v_claims_payment_status_cabinet
WHERE milestone_value IN (1, 5, 25)
GROUP BY milestone_value
ORDER BY milestone_value;

-- ============================================================================
-- CHECK 5: Spot-check de 20 drivers con detalles completos
-- ============================================================================
WITH m1_achieved_in_window AS (
    SELECT 
        m.driver_id,
        m.milestone_value,
        m.achieved_flag,
        m.achieved_date,
        pc.lead_date,
        (pc.lead_date + INTERVAL '14 days')::date AS due_date
    FROM ops.v_cabinet_milestones_achieved_from_payment_calc m
    INNER JOIN ops.v_payment_calculation pc
        ON pc.driver_id = m.driver_id
        AND pc.milestone_trips = m.milestone_value
        AND pc.origin_tag = 'cabinet'
        AND pc.rule_scope = 'partner'
        AND pc.milestone_achieved = true
    WHERE m.milestone_value = 1
        AND m.achieved_flag = true
        AND m.achieved_date::date <= (pc.lead_date + INTERVAL '14 days')::date
        AND m.achieved_date::date >= pc.lead_date
)
SELECT 
    'CHECK 5: Spot-check M1 achieved vs claims' AS check_name,
    m1.driver_id,
    m1.milestone_value,
    m1.achieved_flag,
    m1.achieved_date,
    m1.lead_date,
    m1.due_date,
    COALESCE(c.expected_amount::text, 'NO CLAIM') AS expected_amount,
    COALESCE(c.payment_status, 'NO CLAIM') AS yango_payment_status,
    COALESCE(c.milestone_value::text, 'NO CLAIM') AS claim_exists
FROM m1_achieved_in_window m1
LEFT JOIN ops.v_claims_payment_status_cabinet c
    ON c.driver_id = m1.driver_id
    AND c.milestone_value = m1.milestone_value
ORDER BY m1.driver_id
LIMIT 20;

-- ============================================================================
-- RESUMEN: Distribución de achieved vs claims por milestone
-- ============================================================================
WITH achieved_agg AS (
    SELECT 
        m.milestone_value,
        COUNT(DISTINCT m.driver_id) AS total_achieved
    FROM ops.v_cabinet_milestones_achieved_from_payment_calc m
    INNER JOIN ops.v_payment_calculation pc
        ON pc.driver_id = m.driver_id
        AND pc.milestone_trips = m.milestone_value
        AND pc.origin_tag = 'cabinet'
        AND pc.rule_scope = 'partner'
        AND pc.milestone_achieved = true
    WHERE m.achieved_flag = true
        AND m.milestone_value IN (1, 5, 25)
        AND m.achieved_date::date <= (pc.lead_date + INTERVAL '14 days')::date
        AND m.achieved_date::date >= pc.lead_date
    GROUP BY m.milestone_value
),
claims_agg AS (
    SELECT 
        milestone_value,
        COUNT(DISTINCT driver_id) AS total_claims
    FROM ops.v_claims_payment_status_cabinet
    WHERE milestone_value IN (1, 5, 25)
    GROUP BY milestone_value
)
SELECT 
    'RESUMEN: Achieved vs Claims por milestone' AS check_name,
    COALESCE(a.milestone_value, c.milestone_value) AS milestone_value,
    COALESCE(a.total_achieved, 0) AS total_achieved_in_window,
    COALESCE(c.total_claims, 0) AS total_claims,
    COALESCE(a.total_achieved, 0) - COALESCE(c.total_claims, 0) AS missing_claims,
    CASE 
        WHEN COALESCE(a.total_achieved, 0) = COALESCE(c.total_claims, 0) THEN '✓ PASS'
        ELSE '✗ FAIL'
    END AS status
FROM achieved_agg a
FULL OUTER JOIN claims_agg c
    ON a.milestone_value = c.milestone_value
ORDER BY COALESCE(a.milestone_value, c.milestone_value);

