-- ============================================================================
-- Vista: ops.v_cabinet_leads_limbo
-- ============================================================================
-- PROPÓSITO:
-- Vista LEAD-FIRST que muestra TODOS los leads de cabinet (incluyendo limbo)
-- con su etapa exacta en el embudo. Identifica leads que no avanzan.
-- ============================================================================
-- GRANO:
-- 1 fila por lead (source_pk canónico)
-- ============================================================================
-- REGLAS CANÓNICAS:
-- - source_pk: COALESCE(external_id::text, id::text)
-- - LEAD_DATE_CANONICO: lead_created_at::date (fecha cero operativa del lead)
--   NOTA: lead_created_at es la fecha real del lead (del archivo fuente).
--         created_at es solo timestamp de inserción en BD (no usar para fecha cero).
-- - week_start: DATE_TRUNC('week', LEAD_DATE_CANONICO)::date (lunes ISO)
-- - Ventana 14d: [LEAD_DATE_CANONICO, LEAD_DATE_CANONICO + INTERVAL '14 days')
-- - Milestones: M1>=1, M5>=5, M25>=25 dentro de ventana
-- - Claims deben existir aunque no estén pagados
-- ============================================================================

CREATE OR REPLACE VIEW ops.v_cabinet_leads_limbo AS
WITH leads_base AS (
    -- Base: TODOS los leads de cabinet (SIN filtrar)
    SELECT 
        mcl.id AS lead_id,
        COALESCE(mcl.external_id::text, mcl.id::text) AS lead_source_pk,
        -- LEAD_DATE_CANONICO: lead_created_at::date (fecha cero operativa)
        mcl.lead_created_at::date AS lead_date,
        -- week_start derivado de LEAD_DATE_CANONICO (lunes ISO)
        DATE_TRUNC('week', mcl.lead_created_at::date)::date AS week_start,
        mcl.park_phone,
        mcl.asset_plate_number,
        CONCAT(
            COALESCE(mcl.first_name, ''), ' ',
            COALESCE(mcl.middle_name, ''), ' ',
            COALESCE(mcl.last_name, '')
        ) AS lead_name
    FROM public.module_ct_cabinet_leads mcl
    WHERE mcl.lead_created_at IS NOT NULL
),
leads_identity AS (
    -- Resolver person_key desde identity_links
    SELECT DISTINCT ON (lb.lead_source_pk)
        lb.*,
        il.person_key
    FROM leads_base lb
    LEFT JOIN canon.identity_links il
        ON il.source_table = 'module_ct_cabinet_leads'
        AND il.source_pk = lb.lead_source_pk
    ORDER BY lb.lead_source_pk, il.linked_at DESC NULLS LAST
),
leads_driver AS (
    -- Resolver driver_id desde person_key → identity_links (drivers)
    SELECT 
        li.*,
        il_driver.source_pk AS driver_id
    FROM leads_identity li
    LEFT JOIN canon.identity_links il_driver
        ON il_driver.person_key = li.person_key
        AND il_driver.source_table = 'drivers'
    -- Si hay múltiples drivers, tomar el más reciente
    ORDER BY li.lead_source_pk, il_driver.linked_at DESC NULLS LAST
),
leads_driver_dedup AS (
    -- Deduplicar por lead_source_pk (quedarse con driver_id más reciente)
    SELECT DISTINCT ON (lead_source_pk)
        lead_id,
        lead_source_pk,
        lead_date,
        week_start,
        park_phone,
        asset_plate_number,
        lead_name,
        person_key,
        driver_id
    FROM leads_driver
    ORDER BY lead_source_pk, driver_id NULLS LAST
),
summary_daily_normalized AS (
    -- Normalizar summary_daily
    SELECT 
        driver_id,
        to_date(date_file, 'DD-MM-YYYY') AS prod_date,
        count_orders_completed
    FROM public.summary_daily
    WHERE driver_id IS NOT NULL
        AND date_file IS NOT NULL
        AND date_file ~ '^\d{2}-\d{2}-\d{4}$'
),
leads_trips_14d AS (
    -- Calcular viajes dentro de ventana 14d
    SELECT 
        ldd.lead_source_pk,
        ldd.lead_date,
        ldd.driver_id,
        COALESCE(SUM(sd.count_orders_completed), 0) AS trips_14d,
        -- Ventana 14d: [lead_date, lead_date + 14 days)
        ldd.lead_date + INTERVAL '14 days' AS window_end_14d
    FROM leads_driver_dedup ldd
    LEFT JOIN summary_daily_normalized sd
        ON sd.driver_id = ldd.driver_id
        AND sd.prod_date >= ldd.lead_date
        AND sd.prod_date < ldd.lead_date + INTERVAL '14 days'
    GROUP BY ldd.lead_source_pk, ldd.lead_date, ldd.driver_id
),
leads_milestones AS (
    -- Calcular milestones alcanzados dentro de ventana 14d
    SELECT 
        ltd.lead_source_pk,
        ltd.lead_date,
        ltd.driver_id,
        ltd.trips_14d,
        ltd.window_end_14d,
        -- Flags de milestones
        CASE WHEN ltd.trips_14d >= 1 THEN true ELSE false END AS reached_m1_14d,
        CASE WHEN ltd.trips_14d >= 5 THEN true ELSE false END AS reached_m5_14d,
        CASE WHEN ltd.trips_14d >= 25 THEN true ELSE false END AS reached_m25_14d,
        -- Montos esperados (acumulativo)
        CASE 
            WHEN ltd.trips_14d >= 25 THEN (25 + 35 + 100)::numeric(12,2)
            WHEN ltd.trips_14d >= 5 THEN (25 + 35)::numeric(12,2)
            WHEN ltd.trips_14d >= 1 THEN 25::numeric(12,2)
            ELSE 0::numeric(12,2)
        END AS expected_amount_14d
    FROM leads_trips_14d ltd
),
leads_claims AS (
    -- Verificar claims existentes (sin filtrar por pagado)
    SELECT 
        driver_id,
        BOOL_OR(milestone_value = 1) AS has_claim_m1,
        BOOL_OR(milestone_value = 5) AS has_claim_m5,
        BOOL_OR(milestone_value = 25) AS has_claim_m25
    FROM ops.v_claims_payment_status_cabinet
    WHERE driver_id IS NOT NULL
    GROUP BY driver_id
),
leads_final AS (
    -- Combinar todo
    SELECT 
        ldd.lead_id,
        ldd.lead_source_pk,
        ldd.lead_date,
        ldd.week_start,
        ldd.park_phone,
        ldd.asset_plate_number,
        ldd.lead_name,
        ldd.person_key,
        ldd.driver_id,
        COALESCE(lm.trips_14d, 0) AS trips_14d,
        COALESCE(lm.window_end_14d, ldd.lead_date + INTERVAL '14 days') AS window_end_14d,
        COALESCE(lm.reached_m1_14d, false) AS reached_m1_14d,
        COALESCE(lm.reached_m5_14d, false) AS reached_m5_14d,
        COALESCE(lm.reached_m25_14d, false) AS reached_m25_14d,
        COALESCE(lm.expected_amount_14d, 0::numeric(12,2)) AS expected_amount_14d,
        COALESCE(lc.has_claim_m1, false) AS has_claim_m1,
        COALESCE(lc.has_claim_m5, false) AS has_claim_m5,
        COALESCE(lc.has_claim_m25, false) AS has_claim_m25
    FROM leads_driver_dedup ldd
    LEFT JOIN leads_milestones lm ON lm.lead_source_pk = ldd.lead_source_pk
    LEFT JOIN leads_claims lc ON lc.driver_id = ldd.driver_id
)
SELECT 
    lf.lead_id,
    lf.lead_source_pk,
    lf.lead_date,
    lf.week_start,
    lf.park_phone,
    lf.asset_plate_number,
    lf.lead_name,
    lf.person_key,
    lf.driver_id,
    lf.trips_14d,
    lf.window_end_14d,
    lf.reached_m1_14d,
    lf.reached_m5_14d,
    lf.reached_m25_14d,
    lf.expected_amount_14d,
    lf.has_claim_m1,
    lf.has_claim_m5,
    lf.has_claim_m25,
    -- Determinar limbo_stage
    CASE
        WHEN lf.person_key IS NULL THEN 'NO_IDENTITY'
        WHEN lf.driver_id IS NULL THEN 'NO_DRIVER'
        WHEN lf.trips_14d = 0 THEN 'NO_TRIPS_14D'
        WHEN lf.reached_m1_14d = true AND lf.has_claim_m1 = false THEN 'TRIPS_NO_CLAIM'
        WHEN lf.reached_m5_14d = true AND lf.has_claim_m5 = false THEN 'TRIPS_NO_CLAIM'
        WHEN lf.reached_m25_14d = true AND lf.has_claim_m25 = false THEN 'TRIPS_NO_CLAIM'
        ELSE 'OK'
    END AS limbo_stage,
    -- limbo_reason_detail (ACCIONABLE: qué falta exactamente)
    CASE
        WHEN lf.person_key IS NULL THEN 
            'FALTA: identity_link. Accion: Ejecutar matching job para source_pk=' || lf.lead_source_pk || 
            ' (source_table=module_ct_cabinet_leads). Verificar phone/license/plate en raw data.'
        WHEN lf.driver_id IS NULL THEN 
            'FALTA: driver_id. Accion: Verificar identity_link de person_key=' || COALESCE(lf.person_key::text, 'NULL') || 
            ' a source_table=drivers. Puede requerir crear link manual o esperar job de drivers.'
        WHEN lf.trips_14d = 0 THEN 
            'FALTA: trips en ventana 14d. Accion: Verificar summary_daily para driver_id=' || COALESCE(lf.driver_id, 'NULL') || 
            ' en ventana [' || lf.lead_date || ', ' || lf.window_end_14d || '). Driver puede no haber completado viajes aún.'
        WHEN lf.reached_m1_14d = true AND lf.has_claim_m1 = false THEN 
            'FALTA: claim M1. Accion: Driver alcanzó M1 (trips=' || lf.trips_14d || ') pero no tiene claim. Ejecutar job reconcile_cabinet_claims_14d.'
        WHEN lf.reached_m5_14d = true AND lf.has_claim_m5 = false THEN 
            'FALTA: claim M5. Accion: Driver alcanzó M5 (trips=' || lf.trips_14d || ') pero no tiene claim. Ejecutar job reconcile_cabinet_claims_14d.'
        WHEN lf.reached_m25_14d = true AND lf.has_claim_m25 = false THEN 
            'FALTA: claim M25. Accion: Driver alcanzó M25 (trips=' || lf.trips_14d || ') pero no tiene claim. Ejecutar job reconcile_cabinet_claims_14d.'
        ELSE 'OK: Lead completo. Tiene identity, driver, trips y claims.'
    END AS limbo_reason_detail
FROM leads_final lf
ORDER BY lf.week_start DESC, lf.lead_date DESC, lf.lead_id DESC;

-- ============================================================================
-- Comentarios de la Vista
-- ============================================================================
COMMENT ON VIEW ops.v_cabinet_leads_limbo IS 
'Vista LEAD-FIRST que muestra TODOS los leads de cabinet (incluyendo limbo) con su etapa exacta en el embudo. Identifica leads que no avanzan. Grano: 1 fila por lead (source_pk canónico).';

COMMENT ON COLUMN ops.v_cabinet_leads_limbo.lead_source_pk IS 
'Source PK canónico: COALESCE(external_id::text, id::text). Usado para joins con identity_links.';

COMMENT ON COLUMN ops.v_cabinet_leads_limbo.lead_date IS 
'Fecha de creación del lead (lead_created_at::date). Anchor para ventana 14d.';

COMMENT ON COLUMN ops.v_cabinet_leads_limbo.week_start IS 
'Inicio de semana ISO (date_trunc(''week'', lead_date)::date). Usado para agrupar por semana.';

COMMENT ON COLUMN ops.v_cabinet_leads_limbo.person_key IS 
'Person key desde canon.identity_links (source_table=''module_ct_cabinet_leads''). NULL si no pasó matching.';

COMMENT ON COLUMN ops.v_cabinet_leads_limbo.driver_id IS 
'Driver ID resuelto desde person_key → identity_links (source_table=''drivers''). NULL si no hay driver asociado.';

COMMENT ON COLUMN ops.v_cabinet_leads_limbo.trips_14d IS 
'Total de viajes completados dentro de ventana 14d desde lead_date (summary_daily.count_orders_completed).';

COMMENT ON COLUMN ops.v_cabinet_leads_limbo.reached_m1_14d IS 
'Flag indicando si alcanzó M1 dentro de ventana 14d (trips_14d >= 1).';

COMMENT ON COLUMN ops.v_cabinet_leads_limbo.reached_m5_14d IS 
'Flag indicando si alcanzó M5 dentro de ventana 14d (trips_14d >= 5).';

COMMENT ON COLUMN ops.v_cabinet_leads_limbo.reached_m25_14d IS 
'Flag indicando si alcanzó M25 dentro de ventana 14d (trips_14d >= 25).';

COMMENT ON COLUMN ops.v_cabinet_leads_limbo.expected_amount_14d IS 
'Monto esperado acumulativo según milestones alcanzados (M1=25, M5=+35, M25=+100).';

COMMENT ON COLUMN ops.v_cabinet_leads_limbo.has_claim_m1 IS 
'Flag indicando si existe claim M1 en ops.v_claims_payment_status_cabinet (sin filtrar por pagado).';

COMMENT ON COLUMN ops.v_cabinet_leads_limbo.has_claim_m5 IS 
'Flag indicando si existe claim M5 en ops.v_claims_payment_status_cabinet (sin filtrar por pagado).';

COMMENT ON COLUMN ops.v_cabinet_leads_limbo.has_claim_m25 IS 
'Flag indicando si existe claim M25 en ops.v_claims_payment_status_cabinet (sin filtrar por pagado).';

COMMENT ON COLUMN ops.v_cabinet_leads_limbo.limbo_stage IS 
'Etapa de limbo: NO_IDENTITY, NO_DRIVER, NO_TRIPS_14D, TRIPS_NO_CLAIM, OK. Identifica dónde se detiene el lead.';

COMMENT ON COLUMN ops.v_cabinet_leads_limbo.limbo_reason_detail IS 
'Detalle textual de por qué el lead está en esa etapa de limbo.';
