-- ============================================================================
-- Script de Diagnóstico: M1 Achieved sin Claim
-- ============================================================================
-- PROPÓSITO:
-- Identificar por qué hay 107 drivers con M1 achieved pero sin claim.
-- Verificar si es problema de ventana de 14 días o de otra validación.
-- ============================================================================

SET statement_timeout = '120s';

-- ============================================================================
-- DIAGNÓSTICO 5: Drivers con M1 achieved pero sin claim (detalle)
-- ============================================================================
WITH m1_achieved AS (
    SELECT 
        m.driver_id,
        m.milestone_value,
        m.achieved_flag,
        m.achieved_date,
        pc.lead_date,
        (pc.lead_date + INTERVAL '14 days')::date AS due_date,
        CASE 
            WHEN m.achieved_date::date <= (pc.lead_date + INTERVAL '14 days')::date 
                AND m.achieved_date::date >= pc.lead_date 
            THEN 'DENTRO_VENTANA'
            WHEN m.achieved_date::date < pc.lead_date 
            THEN 'ANTES_LEAD_DATE'
            WHEN m.achieved_date::date > (pc.lead_date + INTERVAL '14 days')::date 
            THEN 'FUERA_VENTANA'
            ELSE 'OTRO'
        END AS ventana_status
    FROM ops.v_cabinet_milestones_achieved_from_payment_calc m
    INNER JOIN ops.v_payment_calculation pc
        ON pc.driver_id = m.driver_id
        AND pc.milestone_trips = m.milestone_value
        AND pc.origin_tag = 'cabinet'
        AND pc.rule_scope = 'partner'
        AND pc.milestone_achieved = true
    WHERE m.milestone_value = 1
        AND m.achieved_flag = true
),
m1_claims AS (
    SELECT DISTINCT driver_id
    FROM ops.v_claims_payment_status_cabinet
    WHERE milestone_value = 1
)
SELECT 
    'DIAG 5: M1 achieved sin claim - Distribución por ventana' AS check_name,
    m1.ventana_status,
    COUNT(*) AS count_drivers
FROM m1_achieved m1
LEFT JOIN m1_claims c ON c.driver_id = m1.driver_id
WHERE c.driver_id IS NULL
GROUP BY m1.ventana_status
ORDER BY m1.ventana_status;

-- ============================================================================
-- DIAGNÓSTICO 6: Spot-check de drivers con M1 achieved pero sin claim
-- ============================================================================
WITH m1_achieved AS (
    SELECT 
        m.driver_id,
        m.achieved_date,
        pc.lead_date,
        (pc.lead_date + INTERVAL '14 days')::date AS due_date,
        CASE 
            WHEN m.achieved_date::date <= (pc.lead_date + INTERVAL '14 days')::date 
                AND m.achieved_date::date >= pc.lead_date 
            THEN 'DENTRO_VENTANA'
            WHEN m.achieved_date::date < pc.lead_date 
            THEN 'ANTES_LEAD_DATE'
            WHEN m.achieved_date::date > (pc.lead_date + INTERVAL '14 days')::date 
            THEN 'FUERA_VENTANA'
            ELSE 'OTRO'
        END AS ventana_status,
        (m.achieved_date::date - pc.lead_date) AS dias_desde_lead,
        ((pc.lead_date + INTERVAL '14 days')::date - m.achieved_date::date) AS dias_antes_vencimiento
    FROM ops.v_cabinet_milestones_achieved_from_payment_calc m
    INNER JOIN ops.v_payment_calculation pc
        ON pc.driver_id = m.driver_id
        AND pc.milestone_trips = m.milestone_value
        AND pc.origin_tag = 'cabinet'
        AND pc.rule_scope = 'partner'
        AND pc.milestone_achieved = true
    WHERE m.milestone_value = 1
        AND m.achieved_flag = true
),
m1_claims AS (
    SELECT DISTINCT driver_id
    FROM ops.v_claims_payment_status_cabinet
    WHERE milestone_value = 1
)
SELECT 
    'DIAG 6: Spot-check M1 achieved sin claim' AS check_name,
    m1.driver_id,
    m1.lead_date,
    m1.achieved_date,
    m1.due_date,
    m1.ventana_status,
    m1.dias_desde_lead,
    m1.dias_antes_vencimiento
FROM m1_achieved m1
LEFT JOIN m1_claims c ON c.driver_id = m1.driver_id
WHERE c.driver_id IS NULL
ORDER BY m1.ventana_status, m1.dias_desde_lead
LIMIT 20;

-- ============================================================================
-- DIAGNÓSTICO 7: Verificar si el problema es múltiples lead_date
-- ============================================================================
WITH m1_achieved_all_lead_dates AS (
    SELECT 
        m.driver_id,
        m.achieved_date,
        pc.lead_date,
        (pc.lead_date + INTERVAL '14 days')::date AS due_date,
        CASE 
            WHEN m.achieved_date::date <= (pc.lead_date + INTERVAL '14 days')::date 
                AND m.achieved_date::date >= pc.lead_date 
            THEN true
            ELSE false
        END AS dentro_ventana
    FROM ops.v_cabinet_milestones_achieved_from_payment_calc m
    INNER JOIN ops.v_payment_calculation pc
        ON pc.driver_id = m.driver_id
        AND pc.milestone_trips = m.milestone_value
        AND pc.origin_tag = 'cabinet'
        AND pc.rule_scope = 'partner'
        AND pc.milestone_achieved = true
    WHERE m.milestone_value = 1
        AND m.achieved_flag = true
),
m1_achieved_with_valid_window AS (
    SELECT DISTINCT
        driver_id,
        achieved_date
    FROM m1_achieved_all_lead_dates
    WHERE dentro_ventana = true
),
m1_claims AS (
    SELECT DISTINCT driver_id
    FROM ops.v_claims_payment_status_cabinet
    WHERE milestone_value = 1
)
SELECT 
    'DIAG 7: M1 achieved con ventana válida pero sin claim' AS check_name,
    COUNT(*) AS count_drivers
FROM m1_achieved_with_valid_window m1
LEFT JOIN m1_claims c ON c.driver_id = m1.driver_id
WHERE c.driver_id IS NULL;

-- ============================================================================
-- DIAGNÓSTICO 8: Verificar agregado canónico en v_claims_payment_status_cabinet
-- ============================================================================
WITH payment_calc_m1 AS (
    SELECT DISTINCT ON (driver_id, milestone_trips)
        driver_id,
        person_key,
        lead_date,
        milestone_trips,
        milestone_achieved,
        achieved_date
    FROM ops.v_payment_calculation
    WHERE origin_tag = 'cabinet'
        AND rule_scope = 'partner'
        AND milestone_trips = 1
        AND driver_id IS NOT NULL
        AND milestone_achieved = true
    ORDER BY driver_id, milestone_trips, lead_date DESC, achieved_date ASC
),
m1_achieved_canonical AS (
    SELECT 
        m.driver_id,
        m.achieved_date
    FROM ops.v_cabinet_milestones_achieved_from_payment_calc m
    WHERE m.milestone_value = 1
        AND m.achieved_flag = true
),
m1_claims AS (
    SELECT DISTINCT driver_id
    FROM ops.v_claims_payment_status_cabinet
    WHERE milestone_value = 1
)
SELECT 
    'DIAG 8: M1 achieved con lead_date válido pero sin claim' AS check_name,
    COUNT(*) AS count_drivers
FROM m1_achieved_canonical m1
INNER JOIN payment_calc_m1 pc ON pc.driver_id = m1.driver_id
LEFT JOIN m1_claims c ON c.driver_id = m1.driver_id
WHERE c.driver_id IS NULL
    AND m1.achieved_date::date <= (pc.lead_date + INTERVAL '14 days')::date
    AND m1.achieved_date::date >= pc.lead_date;

