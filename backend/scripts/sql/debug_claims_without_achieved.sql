-- ============================================================================
-- Script de Debug: Claims sin Milestone Achieved (Violación Canónica)
-- ============================================================================
-- OBJETIVO: Identificar drivers con claims M5 pero sin milestone M5 achieved
-- ============================================================================

-- PASO 1: Encontrar drivers con claim M5 pero sin milestone M5 achieved
SELECT 
    'DRIVERS CON CLAIM M5 SIN MILESTONE M5 ACHIEVED' AS status,
    c.driver_id,
    c.person_key,
    c.milestone_value,
    c.expected_amount,
    c.payment_status,
    c.lead_date,
    c.reason_code
FROM ops.v_claims_payment_status_cabinet c
WHERE c.milestone_value = 5
    AND NOT EXISTS (
        SELECT 1
        FROM ops.v_cabinet_milestones_achieved_from_trips m
        WHERE m.driver_id = c.driver_id
            AND m.milestone_value = 5
            AND m.achieved_flag = true
    )
ORDER BY c.driver_id
LIMIT 20;

-- PASO 2: Para un driver específico del PASO 1, mostrar milestones determinísticos
-- EJECUTAR DESPUÉS DE PASO 1, reemplazar 'DRIVER_ID_AQUI' con un driver_id del resultado
-- SELECT 
--     'MILESTONES ACHIEVED (DETERMINISTICO)' AS status,
--     driver_id,
--     milestone_value,
--     achieved_flag,
--     achieved_date,
--     trips_at_achieved
-- FROM ops.v_cabinet_milestones_achieved_from_trips
-- WHERE driver_id = 'DRIVER_ID_AQUI'
-- ORDER BY milestone_value, achieved_date;

-- PASO 3: Para ese mismo driver, mostrar claims
-- SELECT 
--     'CLAIMS' AS status,
--     driver_id,
--     person_key,
--     milestone_value,
--     expected_amount,
--     payment_status,
--     lead_date,
--     reason_code,
--     days_overdue
-- FROM ops.v_claims_payment_status_cabinet
-- WHERE driver_id = 'DRIVER_ID_AQUI'
-- ORDER BY milestone_value;

-- PASO 4: Para ese mismo driver, mostrar payment_calculation
-- SELECT 
--     'PAYMENT_CALCULATION' AS status,
--     driver_id,
--     person_key,
--     milestone_value,
--     milestone_achieved,
--     expected_amount,
--     lead_date,
--     origin_tag
-- FROM ops.v_payment_calculation
-- WHERE driver_id = 'DRIVER_ID_AQUI'
-- ORDER BY milestone_value;

-- PASO 5: Verificar en Driver Matrix
-- SELECT 
--     'DRIVER_MATRIX' AS status,
--     driver_id,
--     driver_name,
--     m5_achieved_flag,
--     m5_achieved_date,
--     m5_expected_amount_yango,
--     m5_yango_payment_status,
--     m5_window_status
-- FROM ops.v_payments_driver_matrix_cabinet
-- WHERE driver_id = 'DRIVER_ID_AQUI';

-- PASO 6: Contar total de violaciones por milestone
SELECT 
    'VIOLACIONES POR MILESTONE' AS status,
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


