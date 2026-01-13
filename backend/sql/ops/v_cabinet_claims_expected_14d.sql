-- ============================================================================
-- Vista: ops.v_cabinet_claims_expected_14d
-- ============================================================================
-- PROPÓSITO:
-- Vista FUENTE DE VERDAD que calcula qué claims DEBEN existir (expected=true)
-- basándose en milestones alcanzados dentro de ventana 14d estricta.
-- 
-- Esta vista es LEAD-FIRST: universo = public.module_ct_cabinet_leads
-- ============================================================================
-- REGLAS CANÓNICAS:
-- 1. lead_date_canónico = lead_created_at::date (mismo que ops.v_cabinet_leads_limbo)
-- 2. source_pk canónico = COALESCE(external_id::text, id::text)
-- 3. Ventana 14d estricta: [lead_date_canónico, lead_date_canónico + 14 days)
-- 4. Trips se miden con public.summary_daily (o fuente canónica equivalente)
-- 5. claim_expected = true SI Y SOLO SI:
--    - milestone_reached = true (trips_in_window >= milestone)
--    - driver_id IS NOT NULL
--    - person_key IS NOT NULL
-- 6. Montos: M1=S/25, M5=S/35, M25=S/100
-- ============================================================================
-- GRANO:
-- 1 fila por (lead_source_pk, milestone) donde milestone puede ser alcanzado
-- ============================================================================

DROP VIEW IF EXISTS ops.v_cabinet_claims_expected_14d CASCADE;

CREATE VIEW ops.v_cabinet_claims_expected_14d AS
WITH leads_base AS (
    -- Base: leads de cabinet con LEAD_DATE_CANONICO (mismo que v_cabinet_leads_limbo)
    SELECT 
        mcl.id AS lead_id,
        COALESCE(mcl.external_id::text, mcl.id::text) AS lead_source_pk,
        mcl.lead_created_at::date AS lead_date_canonico,
        DATE_TRUNC('week', mcl.lead_created_at::date)::date AS week_start
    FROM public.module_ct_cabinet_leads mcl
    WHERE mcl.lead_created_at IS NOT NULL
),
leads_with_identity AS (
    -- Resolver person_key desde identity_links
    SELECT DISTINCT ON (lb.lead_source_pk)
        lb.lead_id,
        lb.lead_source_pk,
        lb.lead_date_canonico,
        lb.week_start,
        il.person_key
    FROM leads_base lb
    LEFT JOIN canon.identity_links il
        ON il.source_table = 'module_ct_cabinet_leads'
        AND il.source_pk = lb.lead_source_pk
    ORDER BY lb.lead_source_pk, il.linked_at DESC NULLS LAST
),
leads_with_driver AS (
    -- Resolver driver_id desde person_key
    SELECT DISTINCT ON (lwi.lead_source_pk)
        lwi.lead_id,
        lwi.lead_source_pk,
        lwi.lead_date_canonico,
        lwi.week_start,
        lwi.person_key,
        il_driver.source_pk AS driver_id
    FROM leads_with_identity lwi
    LEFT JOIN canon.identity_links il_driver
        ON il_driver.person_key = lwi.person_key
        AND il_driver.source_table = 'drivers'
    ORDER BY lwi.lead_source_pk, il_driver.linked_at DESC NULLS LAST
),
summary_daily_normalized AS (
    -- Normalizar summary_daily (mismo que v_cabinet_leads_limbo)
    SELECT 
        driver_id,
        to_date(date_file, 'DD-MM-YYYY') AS prod_date,
        count_orders_completed
    FROM public.summary_daily
    WHERE driver_id IS NOT NULL
        AND date_file IS NOT NULL
        AND date_file ~ '^\d{2}-\d{2}-\d{4}$'
),
trips_in_window_14d AS (
    -- Calcular viajes dentro de ventana 14d estricta
    SELECT 
        lwd.lead_id,
        lwd.lead_source_pk,
        lwd.lead_date_canonico,
        lwd.week_start,
        lwd.person_key,
        lwd.driver_id,
        -- Ventana 14d: [lead_date_canonico, lead_date_canonico + 14 days)
        lwd.lead_date_canonico + INTERVAL '14 days' AS window_end_14d,
        -- Viajes dentro de ventana
        COALESCE(SUM(sd.count_orders_completed), 0) AS trips_in_window
    FROM leads_with_driver lwd
    LEFT JOIN summary_daily_normalized sd
        ON sd.driver_id = lwd.driver_id
        AND sd.prod_date >= lwd.lead_date_canonico
        AND sd.prod_date < lwd.lead_date_canonico + INTERVAL '14 days'
    GROUP BY lwd.lead_id, lwd.lead_source_pk, lwd.lead_date_canonico, lwd.week_start, lwd.person_key, lwd.driver_id
),
milestones_expanded AS (
    -- Expandir milestones posibles (1, 5, 25) para cada lead
    SELECT 
        tiw.lead_id,
        tiw.lead_source_pk,
        tiw.lead_date_canonico,
        tiw.week_start,
        tiw.person_key,
        tiw.driver_id,
        tiw.window_end_14d,
        tiw.trips_in_window,
        1 AS milestone,
        25::numeric(12,2) AS amount_expected
    FROM trips_in_window_14d tiw
    
    UNION ALL
    
    SELECT 
        tiw.lead_id,
        tiw.lead_source_pk,
        tiw.lead_date_canonico,
        tiw.week_start,
        tiw.person_key,
        tiw.driver_id,
        tiw.window_end_14d,
        tiw.trips_in_window,
        5 AS milestone,
        35::numeric(12,2) AS amount_expected
    FROM trips_in_window_14d tiw
    
    UNION ALL
    
    SELECT 
        tiw.lead_id,
        tiw.lead_source_pk,
        tiw.lead_date_canonico,
        tiw.week_start,
        tiw.person_key,
        tiw.driver_id,
        tiw.window_end_14d,
        tiw.trips_in_window,
        25 AS milestone,
        100::numeric(12,2) AS amount_expected
    FROM trips_in_window_14d tiw
),
claims_expected AS (
    -- Calcular claim_expected según reglas canónicas
    SELECT 
        me.lead_id,
        me.lead_source_pk,
        me.lead_date_canonico,
        me.week_start,
        me.person_key,
        me.driver_id,
        me.window_end_14d,
        me.milestone,
        me.trips_in_window,
        me.amount_expected,
        -- milestone_reached: trips_in_window >= milestone
        (me.trips_in_window >= me.milestone) AS milestone_reached,
        -- claim_expected: milestone_reached AND driver_id NOT NULL AND person_key NOT NULL
        (
            (me.trips_in_window >= me.milestone)
            AND me.driver_id IS NOT NULL
            AND me.person_key IS NOT NULL
        ) AS claim_expected,
        -- expected_reason_detail: explica por qué no es expected
        CASE
            WHEN me.person_key IS NULL THEN 'NO_IDENTITY'
            WHEN me.driver_id IS NULL THEN 'NO_DRIVER'
            WHEN me.trips_in_window < me.milestone THEN 'INSUFFICIENT_TRIPS'
            WHEN me.trips_in_window >= me.milestone AND me.driver_id IS NOT NULL AND me.person_key IS NOT NULL THEN 'OK'
            ELSE 'OTHER'
        END AS expected_reason_detail
    FROM milestones_expanded me
)
SELECT 
    lead_id,
    lead_source_pk,
    lead_date_canonico,
    week_start,
    person_key::text AS person_key,
    driver_id,
    window_end_14d,
    milestone,
    trips_in_window,
    milestone_reached,
    claim_expected,
    amount_expected,
    expected_reason_detail
FROM claims_expected
ORDER BY week_start DESC, lead_date_canonico DESC, milestone DESC;

-- ============================================================================
-- Comentarios de la Vista
-- ============================================================================
COMMENT ON VIEW ops.v_cabinet_claims_expected_14d IS 
'Vista FUENTE DE VERDAD que calcula qué claims DEBEN existir (expected=true) basándose en milestones alcanzados dentro de ventana 14d estricta. LEAD-FIRST: universo = public.module_ct_cabinet_leads. Grano: 1 fila por (lead_source_pk, milestone).';

COMMENT ON COLUMN ops.v_cabinet_claims_expected_14d.lead_id IS 
'ID del lead desde public.module_ct_cabinet_leads.id.';

COMMENT ON COLUMN ops.v_cabinet_claims_expected_14d.lead_source_pk IS 
'Source PK canónico: COALESCE(external_id::text, id::text).';

COMMENT ON COLUMN ops.v_cabinet_claims_expected_14d.lead_date_canonico IS 
'LEAD_DATE_CANONICO: lead_created_at::date (mismo que ops.v_cabinet_leads_limbo).';

COMMENT ON COLUMN ops.v_cabinet_claims_expected_14d.week_start IS 
'Inicio de semana ISO (date_trunc(''week'', lead_date_canonico)::date).';

COMMENT ON COLUMN ops.v_cabinet_claims_expected_14d.person_key IS 
'Person key desde identity_links (UUID como string).';

COMMENT ON COLUMN ops.v_cabinet_claims_expected_14d.driver_id IS 
'Driver ID resuelto desde person_key → identity_links (source_table=''drivers'').';

COMMENT ON COLUMN ops.v_cabinet_claims_expected_14d.window_end_14d IS 
'Fin de ventana 14d (lead_date_canonico + INTERVAL ''14 days'').';

COMMENT ON COLUMN ops.v_cabinet_claims_expected_14d.milestone IS 
'Milestone: 1 (M1), 5 (M5), o 25 (M25).';

COMMENT ON COLUMN ops.v_cabinet_claims_expected_14d.trips_in_window IS 
'Total de viajes completados dentro de ventana 14d estricta [lead_date_canonico, lead_date_canonico + 14 days).';

COMMENT ON COLUMN ops.v_cabinet_claims_expected_14d.milestone_reached IS 
'Flag indicando si el milestone fue alcanzado (trips_in_window >= milestone).';

COMMENT ON COLUMN ops.v_cabinet_claims_expected_14d.claim_expected IS 
'Flag indicando si se espera un claim (milestone_reached AND driver_id NOT NULL AND person_key NOT NULL).';

COMMENT ON COLUMN ops.v_cabinet_claims_expected_14d.amount_expected IS 
'Monto esperado según milestone: M1=S/25, M5=S/35, M25=S/100.';

COMMENT ON COLUMN ops.v_cabinet_claims_expected_14d.expected_reason_detail IS 
'Razón detallada: NO_IDENTITY, NO_DRIVER, INSUFFICIENT_TRIPS, OK, OTHER.';
