-- ============================================================================
-- Script de Verificación: M1 Claims Generation para Cabinet
-- ============================================================================
-- PROPÓSITO:
-- Verificar que todos los drivers con M1 achieved dentro de ventana de 14 días
-- tengan un claim M1 generado en ops.v_claims_payment_status_cabinet.
-- ============================================================================
-- FIX APLICADO:
-- - v_claims_payment_status_cabinet ahora usa v_cabinet_milestones_achieved_from_payment_calc
-- - Incluye M1, M5, M25 con expected_amount correcto (M1=25, M5=35, M25=100)
-- - Ventana de 14 días aplicada correctamente: achieved_date entre lead_date y lead_date+14d
-- ============================================================================
-- CHECKS:
-- 1. Conteo de drivers con M1 achieved en ventana pero sin claim M1 (esperado: 0)
-- 2. Spot-check 20 drivers mostrando: driver_id, milestone, lead_date, achieved_date, due_date, expected_amount, claim_status
-- 3. CHECK duplicados: 0 duplicados por grano de claim (driver_id + milestone_value)
-- 4. CHECK expected_amount: verificar que M1=25, M5=35, M25=100
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
        (pc.lead_date + INTERVAL '14 days')::date AS due_date,
        CASE 
            WHEN m.milestone_value = 1 THEN 25::numeric(12,2)
            WHEN m.milestone_value = 5 THEN 35::numeric(12,2)
            WHEN m.milestone_value = 25 THEN 100::numeric(12,2)
        END AS expected_amount
    FROM ops.v_cabinet_milestones_achieved_from_payment_calc m
    INNER JOIN ops.v_payment_calculation pc
        ON pc.driver_id = m.driver_id
        AND pc.milestone_trips = m.milestone_value
        AND pc.origin_tag = 'cabinet'
        AND pc.rule_scope = 'partner'
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
    'CHECK 1: M1 achieved en ventana sin claim' AS check_name,
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
-- CHECK 2: Spot-check 20 drivers con M1 achieved
-- ============================================================================
WITH m1_achieved_in_window AS (
    SELECT 
        m.driver_id,
        m.milestone_value,
        m.achieved_flag,
        m.achieved_date,
        pc.lead_date,
        (pc.lead_date + INTERVAL '14 days')::date AS due_date,
        CASE 
            WHEN m.milestone_value = 1 THEN 25::numeric(12,2)
            WHEN m.milestone_value = 5 THEN 35::numeric(12,2)
            WHEN m.milestone_value = 25 THEN 100::numeric(12,2)
        END AS expected_amount
    FROM ops.v_cabinet_milestones_achieved_from_payment_calc m
    INNER JOIN ops.v_payment_calculation pc
        ON pc.driver_id = m.driver_id
        AND pc.milestone_trips = m.milestone_value
        AND pc.origin_tag = 'cabinet'
        AND pc.rule_scope = 'partner'
    WHERE m.milestone_value = 1
        AND m.achieved_flag = true
        AND m.achieved_date::date <= (pc.lead_date + INTERVAL '14 days')::date
        AND m.achieved_date::date >= pc.lead_date
)
SELECT 
    'CHECK 2: Spot-check M1 achieved vs claims' AS check_name,
    m1.driver_id,
    m1.milestone_value,
    m1.lead_date,
    m1.achieved_date,
    m1.due_date,
    m1.expected_amount,
    COALESCE(c.milestone_value::text, 'NO CLAIM') AS claim_exists,
    COALESCE(c.payment_status, 'NO CLAIM') AS claim_status,
    COALESCE(c.expected_amount::text, 'NO CLAIM') AS claim_expected_amount
FROM m1_achieved_in_window m1
LEFT JOIN ops.v_claims_payment_status_cabinet c
    ON c.driver_id = m1.driver_id
    AND c.milestone_value = m1.milestone_value
ORDER BY m1.driver_id
LIMIT 20;

-- ============================================================================
-- CHECK 3: Duplicados en claims (grano: driver_id + milestone_value)
-- ============================================================================
SELECT 
    'CHECK 3: Duplicados en claims' AS check_name,
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
    WHERE milestone_value = 1
    GROUP BY driver_id, milestone_value
    HAVING COUNT(*) > 1
) dupes;

-- ============================================================================
-- CHECK 4: Verificar expected_amount por milestone
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
-- RESUMEN: Distribución de M1 achieved vs claims
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
    WHERE m.milestone_value = 1
        AND m.achieved_flag = true
        AND m.achieved_date::date <= (pc.lead_date + INTERVAL '14 days')::date
        AND m.achieved_date::date >= pc.lead_date
),
m1_claims AS (
    SELECT DISTINCT
        driver_id,
        milestone_value
    FROM ops.v_claims_payment_status_cabinet
    WHERE milestone_value = 1
)
SELECT 
    'RESUMEN: M1 achieved vs claims' AS check_name,
    COUNT(DISTINCT m1.driver_id) AS total_m1_achieved_in_window,
    COUNT(DISTINCT c.driver_id) AS total_m1_claims,
    COUNT(DISTINCT m1.driver_id) - COUNT(DISTINCT c.driver_id) AS missing_claims,
    CASE 
        WHEN COUNT(DISTINCT m1.driver_id) = COUNT(DISTINCT c.driver_id) THEN '✓ PASS'
        ELSE '✗ FAIL'
    END AS status
FROM m1_achieved_in_window m1
LEFT JOIN m1_claims c
    ON c.driver_id = m1.driver_id
    AND c.milestone_value = m1.milestone_value;

