-- ============================================================================
-- Vista: ops.v_cabinet_claims_audit_14d
-- ============================================================================
-- PROPÓSITO:
-- Vista de auditoría que compara "debería tener claim" (C2 elegibilidad) 
-- vs "tiene claim" (C3 claims actual) para detectar drivers elegibles que 
-- NO tienen claims generados.
-- ============================================================================
-- REGLAS DE ELEGIBILIDAD (C2):
-- - Driver con origin_tag='cabinet' y rule_scope='partner'
-- - milestone_trips IN (1, 5, 25)
-- - milestone_achieved = true (dentro de ventana window_days=14)
-- - achieved_date dentro de lead_date + 14 días
-- ============================================================================
-- GRANO:
-- 1 fila por (driver_id, milestone_value) donde debería haber claim
-- ============================================================================

CREATE OR REPLACE VIEW ops.v_cabinet_claims_audit_14d AS
WITH eligible_drivers_c2 AS (
    -- C2: Drivers elegibles desde v_payment_calculation
    -- REGLA: milestone_achieved=true Y achieved_date dentro de lead_date + 14 días
    SELECT DISTINCT ON (pc.driver_id, pc.milestone_trips)
        pc.driver_id,
        pc.person_key,
        pc.lead_date,
        pc.milestone_trips AS milestone_value,
        pc.milestone_achieved,
        pc.achieved_date,
        pc.achieved_trips_in_window,
        pc.lead_date + INTERVAL '14 days' AS window_end_14d,
        -- Flags de elegibilidad por milestone
        CASE WHEN pc.milestone_trips = 1 AND pc.milestone_achieved = true 
             AND pc.achieved_date::date <= (pc.lead_date + INTERVAL '14 days')::date
             AND pc.achieved_date::date >= pc.lead_date
             THEN true ELSE false END AS should_have_claim_m1,
        CASE WHEN pc.milestone_trips = 5 AND pc.milestone_achieved = true 
             AND pc.achieved_date::date <= (pc.lead_date + INTERVAL '14 days')::date
             AND pc.achieved_date::date >= pc.lead_date
             THEN true ELSE false END AS should_have_claim_m5,
        CASE WHEN pc.milestone_trips = 25 AND pc.milestone_achieved = true 
             AND pc.achieved_date::date <= (pc.lead_date + INTERVAL '14 days')::date
             AND pc.achieved_date::date >= pc.lead_date
             THEN true ELSE false END AS should_have_claim_m25
    FROM ops.v_payment_calculation pc
    WHERE pc.origin_tag = 'cabinet'
        AND pc.rule_scope = 'partner'
        AND pc.milestone_trips IN (1, 5, 25)
        AND pc.driver_id IS NOT NULL
        AND pc.milestone_achieved = true
        -- Ventana 14d: achieved_date debe estar dentro de lead_date + 14 días
        AND pc.achieved_date::date <= (pc.lead_date + INTERVAL '14 days')::date
        AND pc.achieved_date::date >= pc.lead_date
    ORDER BY pc.driver_id, pc.milestone_trips, pc.lead_date DESC
),
actual_claims_c3 AS (
    -- C3: Claims actuales desde v_claims_payment_status_cabinet
    SELECT 
        c.driver_id,
        c.milestone_value,
        true AS has_claim
    FROM ops.v_claims_payment_status_cabinet c
),
drivers_aggregated AS (
    -- Agregar por driver_id para tener todos los milestones en una fila
    SELECT 
        e.driver_id,
        e.person_key,
        e.lead_date,
        e.window_end_14d,
        MAX(e.achieved_trips_in_window) AS trips_in_14d,
        -- Flags de elegibilidad
        BOOL_OR(e.should_have_claim_m1) AS should_have_claim_m1,
        BOOL_OR(e.should_have_claim_m5) AS should_have_claim_m5,
        BOOL_OR(e.should_have_claim_m25) AS should_have_claim_m25,
        -- Flags de claims existentes
        BOOL_OR(CASE WHEN e.milestone_value = 1 THEN a.has_claim ELSE false END) AS has_claim_m1,
        BOOL_OR(CASE WHEN e.milestone_value = 5 THEN a.has_claim ELSE false END) AS has_claim_m5,
        BOOL_OR(CASE WHEN e.milestone_value = 25 THEN a.has_claim ELSE false END) AS has_claim_m25
    FROM eligible_drivers_c2 e
    LEFT JOIN actual_claims_c3 a
        ON a.driver_id = e.driver_id
        AND a.milestone_value = e.milestone_value
    GROUP BY e.driver_id, e.person_key, e.lead_date, e.window_end_14d
)
SELECT 
    d.driver_id,
    d.person_key,
    d.lead_date,
    d.window_end_14d,
    d.trips_in_14d,
    -- Flags de elegibilidad
    COALESCE(d.should_have_claim_m1, false) AS should_have_claim_m1,
    COALESCE(d.should_have_claim_m5, false) AS should_have_claim_m5,
    COALESCE(d.should_have_claim_m25, false) AS should_have_claim_m25,
    -- Flags de claims existentes
    COALESCE(d.has_claim_m1, false) AS has_claim_m1,
    COALESCE(d.has_claim_m5, false) AS has_claim_m5,
    COALESCE(d.has_claim_m25, false) AS has_claim_m25,
    -- Missing claim bucket
    CASE 
        WHEN (COALESCE(d.should_have_claim_m1, false) AND NOT COALESCE(d.has_claim_m1, false))
             AND (COALESCE(d.should_have_claim_m5, false) AND NOT COALESCE(d.has_claim_m5, false))
             AND (COALESCE(d.should_have_claim_m25, false) AND NOT COALESCE(d.has_claim_m25, false))
             THEN 'MULTIPLE_MISSING'
        WHEN COALESCE(d.should_have_claim_m1, false) AND NOT COALESCE(d.has_claim_m1, false) THEN 'M1_MISSING'
        WHEN COALESCE(d.should_have_claim_m5, false) AND NOT COALESCE(d.has_claim_m5, false) THEN 'M5_MISSING'
        WHEN COALESCE(d.should_have_claim_m25, false) AND NOT COALESCE(d.has_claim_m25, false) THEN 'M25_MISSING'
        ELSE 'NONE'
    END AS missing_claim_bucket,
    -- Root cause analysis
    CASE 
        WHEN d.driver_id IS NULL THEN 'NO_DRIVER_ID'
        WHEN d.lead_date IS NULL THEN 'NO_LEAD_DATE'
        WHEN d.trips_in_14d IS NULL OR d.trips_in_14d = 0 THEN 'MILESTONE_SOURCE_EMPTY'
        -- Verificar si el problema está en la vista de claims (filtros indebidos)
        WHEN (COALESCE(d.should_have_claim_m1, false) AND NOT COALESCE(d.has_claim_m1, false))
             OR (COALESCE(d.should_have_claim_m5, false) AND NOT COALESCE(d.has_claim_m5, false))
             OR (COALESCE(d.should_have_claim_m25, false) AND NOT COALESCE(d.has_claim_m25, false))
             THEN 'VIEW_FILTERING_OUT'
        ELSE 'OTHER'
    END AS root_cause
FROM drivers_aggregated d;

-- ============================================================================
-- Comentarios
-- ============================================================================
COMMENT ON VIEW ops.v_cabinet_claims_audit_14d IS 
'Vista de auditoría que compara "debería tener claim" (C2 elegibilidad) vs "tiene claim" (C3 claims actual) para detectar drivers elegibles que NO tienen claims generados. Grano: 1 fila por driver_id.';

COMMENT ON COLUMN ops.v_cabinet_claims_audit_14d.driver_id IS 
'ID del conductor elegible.';

COMMENT ON COLUMN ops.v_cabinet_claims_audit_14d.person_key IS 
'Person key del conductor.';

COMMENT ON COLUMN ops.v_cabinet_claims_audit_14d.lead_date IS 
'Fecha de lead desde v_payment_calculation.';

COMMENT ON COLUMN ops.v_cabinet_claims_audit_14d.window_end_14d IS 
'Fin de ventana de 14 días (lead_date + 14 días).';

COMMENT ON COLUMN ops.v_cabinet_claims_audit_14d.trips_in_14d IS 
'Viajes acumulados dentro de la ventana de 14 días.';

COMMENT ON COLUMN ops.v_cabinet_claims_audit_14d.should_have_claim_m1 IS 
'Flag indicando si DEBERÍA tener claim M1 según C2 (milestone_achieved=true dentro de ventana 14d).';

COMMENT ON COLUMN ops.v_cabinet_claims_audit_14d.should_have_claim_m5 IS 
'Flag indicando si DEBERÍA tener claim M5 según C2 (milestone_achieved=true dentro de ventana 14d).';

COMMENT ON COLUMN ops.v_cabinet_claims_audit_14d.should_have_claim_m25 IS 
'Flag indicando si DEBERÍA tener claim M25 según C2 (milestone_achieved=true dentro de ventana 14d).';

COMMENT ON COLUMN ops.v_cabinet_claims_audit_14d.has_claim_m1 IS 
'Flag indicando si TIENE claim M1 en C3 (v_claims_payment_status_cabinet).';

COMMENT ON COLUMN ops.v_cabinet_claims_audit_14d.has_claim_m5 IS 
'Flag indicando si TIENE claim M5 en C3 (v_claims_payment_status_cabinet).';

COMMENT ON COLUMN ops.v_cabinet_claims_audit_14d.has_claim_m25 IS 
'Flag indicando si TIENE claim M25 en C3 (v_claims_payment_status_cabinet).';

COMMENT ON COLUMN ops.v_cabinet_claims_audit_14d.missing_claim_bucket IS 
'Bucket de claims faltantes: M1_MISSING, M5_MISSING, M25_MISSING, MULTIPLE_MISSING, NONE.';

COMMENT ON COLUMN ops.v_cabinet_claims_audit_14d.root_cause IS 
'Root cause del problema: NO_DRIVER_ID, NO_LEAD_DATE, WINDOW_MISMATCH, MILESTONE_SOURCE_EMPTY, VIEW_FILTERING_OUT, DEPENDENT_ON_PAYMENT, DEPENDENT_ON_M1, JOIN_MISMATCH_PERSONKEY, OTHER.';
