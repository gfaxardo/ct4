-- ============================================================================
-- Vista: ops.v_cabinet_claims_gap_14d
-- ============================================================================
-- PROPÓSITO:
-- Vista CLAIM-FIRST que identifica gaps: "debería existir claim y no existe"
-- con razón exacta. Usa ops.v_cabinet_claims_expected_14d como fuente de verdad
-- y verifica contra canon.claims_yango_cabinet_14d (tabla física).
-- ============================================================================
-- GRANO:
-- 1 fila por (lead_source_pk, milestone) donde hay gap o expected=true
-- ============================================================================
-- CONTRATO CANÓNICO DE CLAIM (reglas explícitas):
-- 
-- REGLA 1: Un claim 14d DEBE existir si:
--   a) driver_id IS NOT NULL
--   b) person_key IS NOT NULL
--   c) milestone_value IN (1, 5, 25)
--   d) milestone alcanzado dentro de ventana 14d desde LEAD_DATE_CANONICO
--      (trips_in_window >= milestone dentro de [lead_date_canonico, lead_date_canonico + 14 days))
--   e) lead_date_canonico IS NOT NULL
--
-- REGLA 2: Un claim 14d NO debe existir si:
--   a) milestone NO alcanzado dentro de ventana 14d
--   b) driver_id IS NULL
--   c) person_key IS NULL
--   d) lead_date_canonico IS NULL
--
-- REGLA 3: claim_status ENUM:
--   - 'CLAIM_NOT_GENERATED': claim_expected=true pero claim no existe en tabla física (GAP - debe generarse)
--   - 'OK': claim_expected=true y claim existe (OK)
--   - 'INVALID': claim_expected=false (NO debe generarse)
--
-- REGLA 4: gap_reason ENUM:
--   - 'CLAIM_NOT_GENERATED': claim_expected=true pero claim no existe en canon.claims_yango_cabinet_14d
--   - 'OK': claim_expected=true y claim existe
--   - 'NO_IDENTITY': person_key IS NULL
--   - 'NO_DRIVER': driver_id IS NULL
--   - 'INSUFFICIENT_TRIPS': trips_in_window < milestone
--   - 'OTHER': fallback
-- ============================================================================

DROP VIEW IF EXISTS ops.v_cabinet_claims_gap_14d CASCADE;

CREATE VIEW ops.v_cabinet_claims_gap_14d AS
WITH expected_claims AS (
    -- Fuente de verdad: qué claims DEBEN existir
    SELECT 
        lead_id,
        lead_source_pk,
        lead_date_canonico,
        week_start,
        person_key,
        driver_id,
        window_end_14d,
        milestone,
        trips_in_window,
        milestone_reached,
        claim_expected,
        amount_expected,
        expected_reason_detail
    FROM ops.v_cabinet_claims_expected_14d
),
existing_claims AS (
    -- Claims que realmente existen en tabla física
    SELECT 
        person_key::uuid AS person_key_uuid,
        lead_date,
        milestone,
        status,
        generated_at,
        paid_at
    FROM canon.claims_yango_cabinet_14d
    WHERE status IN ('expected', 'generated', 'paid')
),
claims_gap AS (
    -- Join expected con existing para identificar gaps
    SELECT 
        ec.lead_id,
        ec.lead_source_pk,
        ec.lead_date_canonico,
        ec.week_start,
        ec.person_key,
        ec.driver_id,
        ec.window_end_14d,
        ec.milestone,
        ec.trips_in_window,
        ec.milestone_reached,
        ec.claim_expected,
        ec.amount_expected,
        ec.expected_reason_detail,
        -- claim_exists: verificar en tabla física
        (exc.person_key_uuid IS NOT NULL) AS claim_exists,
        -- claim_status
        CASE
            WHEN ec.claim_expected = true AND exc.person_key_uuid IS NULL THEN 'CLAIM_NOT_GENERATED'
            WHEN ec.claim_expected = true AND exc.person_key_uuid IS NOT NULL THEN 'OK'
            ELSE 'INVALID'
        END AS claim_status,
        -- gap_reason
        CASE
            WHEN ec.claim_expected = true AND exc.person_key_uuid IS NULL THEN 'CLAIM_NOT_GENERATED'
            WHEN ec.claim_expected = true AND exc.person_key_uuid IS NOT NULL THEN 'OK'
            WHEN ec.expected_reason_detail = 'NO_IDENTITY' THEN 'NO_IDENTITY'
            WHEN ec.expected_reason_detail = 'NO_DRIVER' THEN 'NO_DRIVER'
            WHEN ec.expected_reason_detail = 'INSUFFICIENT_TRIPS' THEN 'INSUFFICIENT_TRIPS'
            ELSE 'OTHER'
        END AS gap_reason,
        -- gap_detail (texto descriptivo)
        CASE
            WHEN ec.claim_expected = true AND exc.person_key_uuid IS NULL THEN 
                'Milestone alcanzado pero claim no generado en canon.claims_yango_cabinet_14d'
            WHEN ec.claim_expected = true AND exc.person_key_uuid IS NOT NULL THEN 
                'Claim existe (OK)'
            WHEN ec.expected_reason_detail = 'NO_IDENTITY' THEN 
                'Lead no tiene person_key en identity_links'
            WHEN ec.expected_reason_detail = 'NO_DRIVER' THEN 
                'Lead tiene person_key pero no tiene driver_id'
            WHEN ec.expected_reason_detail = 'INSUFFICIENT_TRIPS' THEN 
                'Trips en ventana 14d (' || ec.trips_in_window || ') < milestone (' || ec.milestone || ')'
            ELSE 
                'Razón desconocida: ' || COALESCE(ec.expected_reason_detail, 'NULL')
        END AS gap_detail
    FROM expected_claims ec
    LEFT JOIN existing_claims exc
        ON exc.person_key_uuid::text = ec.person_key
        AND exc.lead_date = ec.lead_date_canonico
        AND exc.milestone = ec.milestone
)
SELECT 
    lead_id,
    lead_source_pk,
    lead_date_canonico AS lead_date,
    week_start,
    person_key,
    driver_id,
    window_end_14d,
    milestone AS milestone_value,
    trips_in_window AS trips_14d,
    milestone_reached AS milestone_achieved,
    claim_expected,
    claim_exists,
    claim_status,
    gap_reason,
    gap_detail,
    amount_expected AS expected_amount  -- Alias para mantener contrato claro con endpoint/UI
FROM claims_gap
WHERE claim_status = 'CLAIM_NOT_GENERATED'  -- Solo mostrar gaps (claims expected pero no generados)
ORDER BY week_start DESC, lead_date_canonico DESC, milestone DESC;

-- ============================================================================
-- Comentarios de la Vista
-- ============================================================================
COMMENT ON VIEW ops.v_cabinet_claims_gap_14d IS 
'Vista CLAIM-FIRST que identifica gaps: "debería existir claim y no existe" con razón exacta. Usa ops.v_cabinet_claims_expected_14d como fuente de verdad y verifica contra canon.claims_yango_cabinet_14d (tabla física). Grano: 1 fila por (lead_source_pk, milestone) donde hay gap.';

COMMENT ON COLUMN ops.v_cabinet_claims_gap_14d.lead_id IS 
'ID del lead desde public.module_ct_cabinet_leads.id.';

COMMENT ON COLUMN ops.v_cabinet_claims_gap_14d.lead_source_pk IS 
'Source PK canónico: COALESCE(external_id::text, id::text).';

COMMENT ON COLUMN ops.v_cabinet_claims_gap_14d.lead_date IS 
'LEAD_DATE_CANONICO: lead_created_at::date (mismo que ops.v_cabinet_leads_limbo).';

COMMENT ON COLUMN ops.v_cabinet_claims_gap_14d.week_start IS 
'Inicio de semana ISO (date_trunc(''week'', lead_date_canonico)::date).';

COMMENT ON COLUMN ops.v_cabinet_claims_gap_14d.person_key IS 
'Person key desde identity_links (UUID como string).';

COMMENT ON COLUMN ops.v_cabinet_claims_gap_14d.driver_id IS 
'Driver ID resuelto desde person_key → identity_links (source_table=''drivers'').';

COMMENT ON COLUMN ops.v_cabinet_claims_gap_14d.milestone_value IS 
'Milestone: 1 (M1), 5 (M5), o 25 (M25).';

COMMENT ON COLUMN ops.v_cabinet_claims_gap_14d.trips_14d IS 
'Total de viajes completados dentro de ventana 14d estricta [lead_date_canonico, lead_date_canonico + 14 days).';

COMMENT ON COLUMN ops.v_cabinet_claims_gap_14d.milestone_achieved IS 
'Flag indicando si el milestone fue alcanzado (trips_in_window >= milestone).';

COMMENT ON COLUMN ops.v_cabinet_claims_gap_14d.claim_expected IS 
'Flag indicando si se espera un claim (milestone_reached AND driver_id NOT NULL AND person_key NOT NULL).';

COMMENT ON COLUMN ops.v_cabinet_claims_gap_14d.claim_exists IS 
'Flag indicando si el claim existe en canon.claims_yango_cabinet_14d.';

COMMENT ON COLUMN ops.v_cabinet_claims_gap_14d.claim_status IS 
'Estado del claim: CLAIM_NOT_GENERATED (gap - debe generarse), OK (existe), INVALID (no debe generarse).';

COMMENT ON COLUMN ops.v_cabinet_claims_gap_14d.gap_reason IS 
'Razón del gap: CLAIM_NOT_GENERATED (debe generarse), OK (existe), NO_IDENTITY, NO_DRIVER, INSUFFICIENT_TRIPS, OTHER.';

COMMENT ON COLUMN ops.v_cabinet_claims_gap_14d.gap_detail IS 
'Detalle textual de por qué hay gap o no.';

COMMENT ON COLUMN ops.v_cabinet_claims_gap_14d.expected_amount IS 
'Monto esperado según milestone: M1=S/25, M5=S/35, M25=S/100.';
