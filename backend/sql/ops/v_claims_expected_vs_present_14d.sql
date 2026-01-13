-- ============================================================================
-- Vista: ops.v_claims_expected_vs_present_14d
-- ============================================================================
-- PROPÓSITO:
-- Vista LEAD-FIRST que compara claims esperados vs claims presentes
-- para detectar la "lógica que impide generar claim" con datos.
-- 
-- NO mezcla con pagos; solo compara expected vs present.
-- ============================================================================
-- GRANO:
-- 1 fila por (lead_source_pk, milestone) donde hay expected o present
-- ============================================================================
-- REGLAS:
-- - expected_claims: desde ops.v_cabinet_claims_expected_14d (claim_expected=true)
-- - present_claims: desde canon.claims_yango_cabinet_14d (status IN ('expected', 'generated', 'paid'))
-- - missing_claims = expected - present
-- ============================================================================

DROP VIEW IF EXISTS ops.v_claims_expected_vs_present_14d CASCADE;

CREATE VIEW ops.v_claims_expected_vs_present_14d AS
WITH expected_claims AS (
    -- Claims esperados desde fuente de verdad
    SELECT 
        lead_id,
        lead_source_pk,
        lead_date_canonico,
        week_start,
        person_key,
        driver_id,
        milestone,
        amount_expected,
        trips_in_window,
        milestone_reached
    FROM ops.v_cabinet_claims_expected_14d
    WHERE claim_expected = true
),
present_claims AS (
    -- Claims presentes en tabla física
    SELECT 
        person_key::uuid AS person_key_uuid,
        lead_date,
        milestone,
        status,
        amount_expected,
        generated_at,
        paid_at
    FROM canon.claims_yango_cabinet_14d
    WHERE status IN ('expected', 'generated', 'paid')
),
expected_vs_present AS (
    -- Join expected con present
    SELECT 
        ec.lead_id,
        ec.lead_source_pk,
        ec.lead_date_canonico,
        ec.week_start,
        ec.person_key,
        ec.driver_id,
        ec.milestone,
        ec.trips_in_window,
        ec.milestone_reached,
        ec.amount_expected AS expected_amount,
        -- Present
        (pc.person_key_uuid IS NOT NULL) AS claim_present,
        pc.status AS claim_status,
        pc.amount_expected AS present_amount,
        pc.generated_at,
        pc.paid_at,
        -- Missing (todos los expected_claims son claim_expected=true por el WHERE)
        CASE 
            WHEN pc.person_key_uuid IS NULL THEN true
            ELSE false
        END AS claim_missing
    FROM expected_claims ec
    LEFT JOIN present_claims pc
        ON pc.person_key_uuid::text = ec.person_key
        AND pc.lead_date = ec.lead_date_canonico
        AND pc.milestone = ec.milestone
)
SELECT 
    lead_id,
    lead_source_pk,
    lead_date_canonico AS lead_date,
    week_start,
    person_key,
    driver_id,
    milestone AS milestone_value,
    trips_in_window AS trips_14d,
    milestone_reached,
    expected_amount,
    claim_present,
    claim_status,
    present_amount,
    generated_at,
    paid_at,
    claim_missing,
    -- missing_amount (si falta claim, usar expected_amount)
    CASE 
        WHEN claim_missing = true THEN expected_amount
        ELSE 0::numeric(12,2)
    END AS missing_amount
FROM expected_vs_present
ORDER BY week_start DESC, lead_date_canonico DESC, milestone DESC;

-- ============================================================================
-- Comentarios de la Vista
-- ============================================================================
COMMENT ON VIEW ops.v_claims_expected_vs_present_14d IS 
'Vista LEAD-FIRST que compara claims esperados vs claims presentes para detectar la "lógica que impide generar claim" con datos. NO mezcla con pagos. Grano: 1 fila por (lead_source_pk, milestone).';

COMMENT ON COLUMN ops.v_claims_expected_vs_present_14d.lead_id IS 
'ID del lead desde public.module_ct_cabinet_leads.id.';

COMMENT ON COLUMN ops.v_claims_expected_vs_present_14d.lead_source_pk IS 
'Source PK canónico: COALESCE(external_id::text, id::text).';

COMMENT ON COLUMN ops.v_claims_expected_vs_present_14d.lead_date IS 
'LEAD_DATE_CANONICO: lead_created_at::date (fecha cero operativa).';

COMMENT ON COLUMN ops.v_claims_expected_vs_present_14d.week_start IS 
'Inicio de semana ISO (date_trunc(''week'', lead_date_canonico)::date).';

COMMENT ON COLUMN ops.v_claims_expected_vs_present_14d.milestone_value IS 
'Milestone: 1 (M1), 5 (M5), o 25 (M25).';

COMMENT ON COLUMN ops.v_claims_expected_vs_present_14d.trips_14d IS 
'Total de viajes completados dentro de ventana 14d estricta.';

COMMENT ON COLUMN ops.v_claims_expected_vs_present_14d.milestone_reached IS 
'Flag indicando si el milestone fue alcanzado (trips_in_window >= milestone).';

COMMENT ON COLUMN ops.v_claims_expected_vs_present_14d.expected_amount IS 
'Monto esperado según milestone: M1=S/25, M5=S/35, M25=S/100.';

COMMENT ON COLUMN ops.v_claims_expected_vs_present_14d.claim_present IS 
'Flag indicando si el claim existe en canon.claims_yango_cabinet_14d.';

COMMENT ON COLUMN ops.v_claims_expected_vs_present_14d.claim_status IS 
'Estado del claim presente: expected, generated, paid (desde canon.claims_yango_cabinet_14d).';

COMMENT ON COLUMN ops.v_claims_expected_vs_present_14d.claim_missing IS 
'Flag indicando si falta el claim (expected=true pero present=false).';

COMMENT ON COLUMN ops.v_claims_expected_vs_present_14d.missing_amount IS 
'Monto faltante (expected_amount si claim_missing=true, 0 si no).';
