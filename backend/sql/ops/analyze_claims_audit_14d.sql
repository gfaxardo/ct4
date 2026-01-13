-- ============================================================================
-- Script de Análisis: Detectar drivers elegibles sin claims
-- ============================================================================
-- Este script analiza la vista de auditoría para encontrar casos reales
-- donde drivers elegibles NO tienen claims generados.
-- ============================================================================

-- 1. RESUMEN GENERAL: Conteos de missing claims
SELECT 
    '=== RESUMEN GENERAL ===' AS seccion,
    COUNT(*) AS total_drivers_elegibles,
    COUNT(*) FILTER (WHERE should_have_claim_m1 = true) AS total_should_have_m1,
    COUNT(*) FILTER (WHERE has_claim_m1 = true) AS total_has_m1,
    COUNT(*) FILTER (WHERE should_have_claim_m1 = true AND has_claim_m1 = false) AS missing_m1,
    COUNT(*) FILTER (WHERE should_have_claim_m5 = true) AS total_should_have_m5,
    COUNT(*) FILTER (WHERE has_claim_m5 = true) AS total_has_m5,
    COUNT(*) FILTER (WHERE should_have_claim_m5 = true AND has_claim_m5 = false) AS missing_m5,
    COUNT(*) FILTER (WHERE should_have_claim_m25 = true) AS total_should_have_m25,
    COUNT(*) FILTER (WHERE has_claim_m25 = true) AS total_has_m25,
    COUNT(*) FILTER (WHERE should_have_claim_m25 = true AND has_claim_m25 = false) AS missing_m25
FROM ops.v_cabinet_claims_audit_14d;

-- 2. ROOT CAUSES: Top root causes
SELECT 
    '=== ROOT CAUSES ===' AS seccion,
    root_cause,
    COUNT(*) AS count,
    COUNT(*) FILTER (WHERE missing_claim_bucket = 'M1_MISSING') AS m1_missing,
    COUNT(*) FILTER (WHERE missing_claim_bucket = 'M5_MISSING') AS m5_missing,
    COUNT(*) FILTER (WHERE missing_claim_bucket = 'M25_MISSING') AS m25_missing,
    COUNT(*) FILTER (WHERE missing_claim_bucket = 'MULTIPLE_MISSING') AS multiple_missing
FROM ops.v_cabinet_claims_audit_14d
WHERE missing_claim_bucket != 'NONE'
GROUP BY root_cause
ORDER BY count DESC;

-- 3. CASOS REALES: 10 drivers con M1 missing
SELECT 
    '=== CASOS REALES: M1 MISSING ===' AS seccion,
    driver_id,
    person_key,
    lead_date,
    window_end_14d,
    trips_in_14d,
    should_have_claim_m1,
    has_claim_m1,
    missing_claim_bucket,
    root_cause
FROM ops.v_cabinet_claims_audit_14d
WHERE should_have_claim_m1 = true 
    AND has_claim_m1 = false
ORDER BY lead_date DESC
LIMIT 10;

-- 4. VERIFICACIÓN LINEAGE: Para un caso específico, seguir el lineage completo
-- (Reemplazar DRIVER_ID con un caso real del paso 3)
SELECT 
    '=== LINEAGE: C2 ELEGIBILIDAD ===' AS seccion,
    pc.driver_id,
    pc.person_key,
    pc.lead_date,
    pc.milestone_trips,
    pc.milestone_achieved,
    pc.achieved_date,
    pc.achieved_trips_in_window,
    pc.lead_date + INTERVAL '14 days' AS window_end_14d,
    CASE 
        WHEN pc.achieved_date::date <= (pc.lead_date + INTERVAL '14 days')::date
             AND pc.achieved_date::date >= pc.lead_date
        THEN true ELSE false 
    END AS within_14d_window
FROM ops.v_payment_calculation pc
WHERE pc.origin_tag = 'cabinet'
    AND pc.rule_scope = 'partner'
    AND pc.milestone_trips = 1
    AND pc.milestone_achieved = true
    AND pc.driver_id = (SELECT driver_id FROM ops.v_cabinet_claims_audit_14d 
                        WHERE should_have_claim_m1 = true AND has_claim_m1 = false 
                        LIMIT 1);

-- 5. VERIFICACIÓN: ¿Existe en milestones achieved?
SELECT 
    '=== LINEAGE: MILESTONES ACHIEVED ===' AS seccion,
    m.driver_id,
    m.milestone_value,
    m.achieved_flag,
    m.achieved_date
FROM ops.v_cabinet_milestones_achieved_from_payment_calc m
WHERE m.driver_id = (SELECT driver_id FROM ops.v_cabinet_claims_audit_14d 
                     WHERE should_have_claim_m1 = true AND has_claim_m1 = false 
                     LIMIT 1)
    AND m.milestone_value = 1;

-- 6. VERIFICACIÓN: ¿Por qué no aparece en claims?
SELECT 
    '=== LINEAGE: CLAIMS ACTUAL ===' AS seccion,
    c.driver_id,
    c.milestone_value,
    c.lead_date,
    c.expected_amount,
    c.paid_flag
FROM ops.v_claims_payment_status_cabinet c
WHERE c.driver_id = (SELECT driver_id FROM ops.v_cabinet_claims_audit_14d 
                     WHERE should_have_claim_m1 = true AND has_claim_m1 = false 
                     LIMIT 1);

-- 7. VERIFICACIÓN: Join en base_claims_raw de v_claims_payment_status_cabinet
-- (Simular la lógica de la vista de claims)
WITH payment_calc_agg AS (
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
        AND milestone_trips IN (1, 5, 25)
        AND driver_id IS NOT NULL
        AND milestone_achieved = true
    ORDER BY driver_id, milestone_trips, lead_date DESC, achieved_date ASC
),
milestones_achieved AS (
    SELECT
        driver_id,
        milestone_trips AS milestone_value,
        bool_or(milestone_achieved) AS achieved_flag,
        min(achieved_date) FILTER (WHERE milestone_achieved) AS achieved_date
    FROM ops.v_payment_calculation
    WHERE origin_tag = 'cabinet'
        AND milestone_trips IN (1, 5, 25)
        AND driver_id IS NOT NULL
    GROUP BY driver_id, milestone_trips
)
SELECT 
    '=== LINEAGE: JOIN BASE_CLAIMS_RAW ===' AS seccion,
    m.driver_id,
    m.milestone_value,
    m.achieved_flag,
    m.achieved_date,
    pc_agg.person_key,
    pc_agg.lead_date,
    pc_agg.milestone_trips,
    CASE 
        WHEN m.achieved_date::date <= (pc_agg.lead_date + INTERVAL '14 days')::date
             AND m.achieved_date::date >= pc_agg.lead_date
        THEN true ELSE false 
    END AS within_window,
    CASE 
        WHEN m.achieved_flag = true 
             AND m.achieved_date::date <= (pc_agg.lead_date + INTERVAL '14 days')::date
             AND m.achieved_date::date >= pc_agg.lead_date
        THEN 'SHOULD_APPEAR' ELSE 'FILTERED_OUT'
    END AS status
FROM milestones_achieved m
INNER JOIN payment_calc_agg pc_agg
    ON pc_agg.driver_id = m.driver_id
    AND pc_agg.milestone_trips = m.milestone_value
WHERE m.driver_id = (SELECT driver_id FROM ops.v_cabinet_claims_audit_14d 
                     WHERE should_have_claim_m1 = true AND has_claim_m1 = false 
                     LIMIT 1)
    AND m.milestone_value = 1;
