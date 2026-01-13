-- ============================================================================
-- Vista: ops.v_cabinet_identity_recovery_impact_14d
-- ============================================================================
-- PROPÓSITO:
-- Vista puente de impacto que mide el impacto real del recovery sobre Cobranza Cabinet 14d.
-- Es la fuente de verdad del "impacto recovery → cobranza".
-- ============================================================================
-- GRANO:
-- 1 fila por lead cabinet (dentro del rango que usa UI, típicamente últimos N días o todos).
-- ============================================================================
-- COLUMNAS:
-- - lead_id, lead_date, window_end_14d
-- - person_key_effective, identity_effective, origin_ok
-- - has_claim (según v_payment_calculation)
-- - claim_status_bucket (unidentified, identified_no_origin, identified_origin_no_claim, identified_origin_claim)
-- - recovered_at (desde ops.cabinet_lead_recovery_audit)
-- - recovered_within_14d BOOLEAN
-- - impact_bucket (still_unidentified, recovered_within_14d_but_no_claim, recovered_within_14d_and_claim, recovered_late, identified_but_missing_origin, identified_origin_no_claim)
-- ============================================================================
-- IMPORTANTE:
-- Esta vista NO recalcula elegibilidad. Solo usa "has_claim" tal como ya existe hoy en la lógica actual.
-- ============================================================================

CREATE OR REPLACE VIEW ops.v_cabinet_identity_recovery_impact_14d AS
WITH lead_identity AS (
    -- Base: identidad efectiva desde FASE 1
    SELECT 
        lead_id,
        lead_date,
        person_key_effective,
        identity_effective,
        identity_link_source
    FROM ops.v_cabinet_lead_identity_effective
),
lead_origin AS (
    -- Verificar si existe canon.identity_origin con origin_tag='cabinet_lead' y origin_source_id=lead_id
    SELECT DISTINCT ON (io.origin_source_id)
        io.origin_source_id AS lead_id,
        io.person_key,
        TRUE AS origin_ok
    FROM canon.identity_origin io
    WHERE io.origin_tag = 'cabinet_lead'
),
lead_claims AS (
    -- Verificar si tiene claims según v_payment_calculation (vista canónica C2)
    -- Un lead tiene claim si existe registro con origin_tag='cabinet' y milestone_achieved=true
    SELECT DISTINCT
        li.lead_id,
        li.lead_date,
        li.person_key_effective AS person_key,
        TRUE AS has_claim
    FROM lead_identity li
    INNER JOIN ops.v_payment_calculation pc ON pc.person_key = li.person_key_effective
        AND pc.lead_date = li.lead_date
        AND pc.origin_tag = 'cabinet'
        AND pc.milestone_achieved = true
        AND pc.milestone_trips IN (1, 5, 25)
        AND pc.driver_id IS NOT NULL
),
lead_recovery AS (
    -- Obtener recovered_at desde ops.cabinet_lead_recovery_audit (si existe)
    SELECT 
        lead_id,
        first_recovered_at AS recovered_at
    FROM ops.cabinet_lead_recovery_audit
)
SELECT 
    li.lead_id,
    li.lead_date,
    li.lead_date + INTERVAL '14 days' AS window_end_14d,
    li.person_key_effective,
    li.identity_effective,
    COALESCE(lo.origin_ok, false) AS origin_ok,
    COALESCE(lc.has_claim, false) AS has_claim,
    -- claim_status_bucket: estado del claim (basado en identidad + origin + claim)
    CASE 
        WHEN li.identity_effective = false THEN 'unidentified'
        WHEN li.identity_effective = true AND COALESCE(lo.origin_ok, false) = false THEN 'identified_no_origin'
        WHEN li.identity_effective = true AND COALESCE(lo.origin_ok, false) = true AND COALESCE(lc.has_claim, false) = false THEN 'identified_origin_no_claim'
        WHEN li.identity_effective = true AND COALESCE(lo.origin_ok, false) = true AND COALESCE(lc.has_claim, false) = true THEN 'identified_origin_claim'
        ELSE 'unidentified'
    END AS claim_status_bucket,
    -- recovered_at: timestamp de cuando se recuperó (si existe)
    lr.recovered_at,
    -- recovered_within_14d: TRUE si recovered_at <= window_end_14d
    CASE 
        WHEN lr.recovered_at IS NOT NULL THEN (lr.recovered_at <= (li.lead_date + INTERVAL '14 days'))
        ELSE NULL
    END AS recovered_within_14d,
    -- impact_bucket: bucket de impacto del recovery
    CASE 
        -- still_unidentified: no tiene identidad
        WHEN li.identity_effective = false THEN 'still_unidentified'
        -- recovered_within_14d_but_no_claim: recuperado dentro de 14d pero sin claim
        WHEN lr.recovered_at IS NOT NULL 
            AND (lr.recovered_at <= (li.lead_date + INTERVAL '14 days'))
            AND COALESCE(lc.has_claim, false) = false THEN 'recovered_within_14d_but_no_claim'
        -- recovered_within_14d_and_claim: recuperado dentro de 14d y con claim
        WHEN lr.recovered_at IS NOT NULL 
            AND (lr.recovered_at <= (li.lead_date + INTERVAL '14 days'))
            AND COALESCE(lc.has_claim, false) = true THEN 'recovered_within_14d_and_claim'
        -- recovered_late: recuperado después de 14d
        WHEN lr.recovered_at IS NOT NULL 
            AND (lr.recovered_at > (li.lead_date + INTERVAL '14 days')) THEN 'recovered_late'
        -- identified_but_missing_origin: tiene identidad pero falta origin
        WHEN li.identity_effective = true AND COALESCE(lo.origin_ok, false) = false THEN 'identified_but_missing_origin'
        -- identified_origin_no_claim: tiene identidad y origin pero sin claim (recovered_at null pero ya estaba linked)
        WHEN li.identity_effective = true 
            AND COALESCE(lo.origin_ok, false) = true 
            AND COALESCE(lc.has_claim, false) = false 
            AND lr.recovered_at IS NULL THEN 'identified_origin_no_claim'
        ELSE 'still_unidentified'
    END AS impact_bucket
FROM lead_identity li
LEFT JOIN lead_origin lo ON lo.lead_id = li.lead_id AND lo.person_key = li.person_key_effective
LEFT JOIN lead_claims lc ON lc.lead_id = li.lead_id
LEFT JOIN lead_recovery lr ON lr.lead_id = li.lead_id;

-- ============================================================================
-- Comentarios de la Vista
-- ============================================================================
COMMENT ON VIEW ops.v_cabinet_identity_recovery_impact_14d IS 
'Vista puente de impacto que mide el impacto real del recovery sobre Cobranza Cabinet 14d. Es la fuente de verdad del "impacto recovery → cobranza". Grano: 1 fila por lead_id.';

COMMENT ON COLUMN ops.v_cabinet_identity_recovery_impact_14d.lead_id IS 
'ID del lead (external_id o id). Grano principal de la vista.';

COMMENT ON COLUMN ops.v_cabinet_identity_recovery_impact_14d.lead_date IS 
'Fecha de creación del lead (lead_created_at::DATE).';

COMMENT ON COLUMN ops.v_cabinet_identity_recovery_impact_14d.window_end_14d IS 
'Fin de ventana de 14 días desde lead_date (lead_date + 14 days).';

COMMENT ON COLUMN ops.v_cabinet_identity_recovery_impact_14d.person_key_effective IS 
'Person key efectivo asignado al lead desde canon.identity_links. NULL si no tiene identidad.';

COMMENT ON COLUMN ops.v_cabinet_identity_recovery_impact_14d.identity_effective IS 
'Flag indicando si el lead tiene identidad efectiva (person_key IS NOT NULL).';

COMMENT ON COLUMN ops.v_cabinet_identity_recovery_impact_14d.origin_ok IS 
'Flag indicando si existe canon.identity_origin con origin_tag=''cabinet_lead'' y origin_source_id=lead_id.';

COMMENT ON COLUMN ops.v_cabinet_identity_recovery_impact_14d.has_claim IS 
'Flag indicando si tiene claims según ops.v_payment_calculation (origin_tag=''cabinet'', milestone_achieved=true).';

COMMENT ON COLUMN ops.v_cabinet_identity_recovery_impact_14d.claim_status_bucket IS 
'Estado del claim: unidentified (sin identidad), identified_no_origin (identidad sin origin), identified_origin_no_claim (identidad+origin sin claim), identified_origin_claim (identidad+origin+claim).';

COMMENT ON COLUMN ops.v_cabinet_identity_recovery_impact_14d.recovered_at IS 
'Timestamp de cuando se recuperó el lead (desde ops.cabinet_lead_recovery_audit.first_recovered_at). NULL si nunca recuperado.';

COMMENT ON COLUMN ops.v_cabinet_identity_recovery_impact_14d.recovered_within_14d IS 
'Flag indicando si recovered_at <= window_end_14d. NULL si nunca recuperado.';

COMMENT ON COLUMN ops.v_cabinet_identity_recovery_impact_14d.impact_bucket IS 
'Bucket de impacto del recovery: still_unidentified, recovered_within_14d_but_no_claim, recovered_within_14d_and_claim, recovered_late, identified_but_missing_origin, identified_origin_no_claim.';
