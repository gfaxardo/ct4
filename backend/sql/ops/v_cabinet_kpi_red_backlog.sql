-- ============================================================================
-- Vista: ops.v_cabinet_kpi_red_backlog
-- ============================================================================
-- PROPÓSITO:
-- Define el set exacto de leads que están en el KPI rojo "Leads sin identidad ni claims".
-- Esta es la fuente de verdad para el backlog del KPI rojo.
-- ============================================================================
-- GRANO:
-- 1 fila por lead_source_pk que está en el KPI rojo
-- ============================================================================
-- FUENTES:
-- - public.module_ct_cabinet_leads (leads originales)
-- - canon.identity_links (vínculos de identidad)
-- - ops.v_claims_payment_status_cabinet (claims con pagos)
-- ============================================================================

CREATE OR REPLACE VIEW ops.v_cabinet_kpi_red_backlog AS
WITH leads_with_identity AS (
    -- Leads que tienen identity_link
    SELECT DISTINCT
        COALESCE(mcl.external_id::text, mcl.id::text) AS lead_source_pk
    FROM public.module_ct_cabinet_leads mcl
    INNER JOIN canon.identity_links il
        ON il.source_table = 'module_ct_cabinet_leads'
        AND il.source_pk = COALESCE(mcl.external_id::text, mcl.id::text)
),
leads_with_claims AS (
    -- Leads que tienen claims
    SELECT DISTINCT
        COALESCE(mcl.external_id::text, mcl.id::text) AS lead_source_pk
    FROM public.module_ct_cabinet_leads mcl
    INNER JOIN canon.identity_links il
        ON il.source_table = 'module_ct_cabinet_leads'
        AND il.source_pk = COALESCE(mcl.external_id::text, mcl.id::text)
    INNER JOIN ops.v_claims_payment_status_cabinet c
        ON c.person_key = il.person_key
        AND c.driver_id IS NOT NULL
),
kpi_red_leads AS (
    -- Leads que están en el KPI rojo (sin identidad ni claims)
    SELECT DISTINCT
        COALESCE(mcl.external_id::text, mcl.id::text) AS lead_source_pk,
        mcl.lead_created_at::DATE AS lead_date
    FROM public.module_ct_cabinet_leads mcl
    WHERE NOT EXISTS (
        SELECT 1
        FROM leads_with_identity li
        WHERE li.lead_source_pk = COALESCE(mcl.external_id::text, mcl.id::text)
    )
    AND NOT EXISTS (
        SELECT 1
        FROM leads_with_claims lc
        WHERE lc.lead_source_pk = COALESCE(mcl.external_id::text, mcl.id::text)
    )
)
SELECT
    krl.lead_source_pk,
    krl.lead_date,
    -- reason_bucket: categoría del motivo
    CASE
        WHEN NOT EXISTS (SELECT 1 FROM leads_with_identity li WHERE li.lead_source_pk = krl.lead_source_pk)
            AND NOT EXISTS (SELECT 1 FROM leads_with_claims lc WHERE lc.lead_source_pk = krl.lead_source_pk)
            THEN 'both'  -- Sin identidad Y sin claims
        WHEN NOT EXISTS (SELECT 1 FROM leads_with_identity li WHERE li.lead_source_pk = krl.lead_source_pk)
            THEN 'no_identity'  -- Solo sin identidad
        ELSE 'no_claim'  -- Solo sin claim (no debería pasar en este contexto)
    END AS reason_bucket,
    -- age_days: días desde que se creó el lead
    (CURRENT_DATE - krl.lead_date) AS age_days
FROM kpi_red_leads krl;

COMMENT ON VIEW ops.v_cabinet_kpi_red_backlog IS
'Vista que define el set exacto de leads que están en el KPI rojo "Leads sin identidad ni claims".';

COMMENT ON COLUMN ops.v_cabinet_kpi_red_backlog.lead_source_pk IS
'ID unificado del lead (COALESCE(external_id::text, id::text)).';

COMMENT ON COLUMN ops.v_cabinet_kpi_red_backlog.lead_date IS
'Fecha de creación del lead.';

COMMENT ON COLUMN ops.v_cabinet_kpi_red_backlog.reason_bucket IS
'Categoría del motivo: "both" (sin identidad y sin claims), "no_identity" (solo sin identidad), "no_claim" (solo sin claim).';

COMMENT ON COLUMN ops.v_cabinet_kpi_red_backlog.age_days IS
'Días desde que se creó el lead hasta hoy.';
