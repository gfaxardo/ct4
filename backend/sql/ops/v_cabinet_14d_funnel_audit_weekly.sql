-- ============================================================================
-- Vista: ops.v_cabinet_14d_funnel_audit_weekly
-- ============================================================================
-- PROPÓSITO:
-- Auditoría semanal del embudo de Cobranza 14d por LEAD_DATE_CANONICO.
-- Identifica el punto exacto de ruptura en el flujo de leads.
-- ============================================================================
-- GRANO:
-- 1 fila por week_start (semana ISO truncada desde LEAD_DATE_CANONICO)
-- ============================================================================
-- REGLAS CANÓNICAS:
-- - LEAD_DATE_CANONICO: lead_created_at::date (fecha cero operativa del lead)
-- - week_start: DATE_TRUNC('week', LEAD_DATE_CANONICO)::date (lunes ISO)
-- - Ventana 14d: [LEAD_DATE_CANONICO, LEAD_DATE_CANONICO + INTERVAL '14 days')
-- ============================================================================
-- COLUMNAS:
-- - week_start: inicio de semana (date_trunc('week', lead_date)::date)
-- - leads_total: total de leads en module_ct_cabinet_leads con lead_created_at en esa semana
-- - leads_with_identity: leads que tienen person_key en identity_links
-- - leads_with_driver: leads que tienen driver_id (identity_link -> drivers)
-- - drivers_with_trips_14d: drivers con viajes dentro de ventana 14d desde lead_date
-- - reached_m1_14d, reached_m5_14d, reached_m25_14d: milestones alcanzados
-- - claims_expected_m1/m5/m25: claims que deberían existir según milestones
-- - claims_present_m1/m5/m25: claims que realmente existen en v_claims_payment_status_cabinet
-- - debt_expected_total: monto esperado total por semana
-- - limbo_no_identity/no_driver/no_trips_14d/trips_no_claim/ok: conteos por limbo_stage
-- ============================================================================

-- DROP VIEW si existe para permitir cambios en columnas
DROP VIEW IF EXISTS ops.v_cabinet_14d_funnel_audit_weekly CASCADE;

CREATE VIEW ops.v_cabinet_14d_funnel_audit_weekly AS
WITH leads_base AS (
    -- Base: todos los leads de cabinet con LEAD_DATE_CANONICO (lead_created_at::date)
    SELECT 
        COALESCE(external_id::text, id::text) AS source_pk,
        id,
        external_id,
        -- LEAD_DATE_CANONICO: lead_created_at::date (fecha cero operativa)
        lead_created_at::date AS lead_date,
        -- week_start derivado de LEAD_DATE_CANONICO (lunes ISO)
        DATE_TRUNC('week', lead_created_at::date)::date AS week_start
    FROM public.module_ct_cabinet_leads
    WHERE lead_created_at IS NOT NULL
),
leads_by_week AS (
    -- Agrupar leads por semana
    SELECT 
        week_start,
        COUNT(*) AS leads_total,
        COUNT(DISTINCT source_pk) AS leads_distinct_pk
    FROM leads_base
    GROUP BY week_start
),
leads_with_identity_cte AS (
    -- Leads que tienen identity_link (person_key)
    SELECT DISTINCT
        lb.week_start,
        lb.source_pk,
        il.person_key,
        il.source_pk AS driver_id_from_identity
    FROM leads_base lb
    LEFT JOIN canon.identity_links il
        ON il.source_table = 'module_ct_cabinet_leads'
        AND il.source_pk = lb.source_pk
    WHERE il.person_key IS NOT NULL
),
leads_with_identity_by_week AS (
    -- Contar leads con identity por semana
    SELECT 
        week_start,
        COUNT(DISTINCT source_pk) AS leads_with_identity,
        COUNT(DISTINCT person_key) AS distinct_person_keys,
        COUNT(DISTINCT driver_id_from_identity) AS leads_with_driver_id
    FROM leads_with_identity_cte
    GROUP BY week_start
),
leads_with_driver_cte AS (
    -- Leads que tienen driver_id (desde identity_links -> drivers)
    SELECT DISTINCT
        lwi.week_start,
        lwi.source_pk,
        lwi.person_key,
        lwi.driver_id_from_identity AS driver_id
    FROM leads_with_identity_cte lwi
    WHERE lwi.driver_id_from_identity IS NOT NULL
),
leads_with_driver_by_week AS (
    -- Contar leads con driver por semana
    SELECT 
        week_start,
        COUNT(DISTINCT source_pk) AS leads_with_driver,
        COUNT(DISTINCT driver_id) AS distinct_drivers
    FROM leads_with_driver_cte
    GROUP BY week_start
),
drivers_with_trips_14d_cte AS (
    -- Drivers con viajes dentro de ventana 14d desde lead_date
    SELECT DISTINCT
        lwd.week_start,
        lwd.driver_id,
        lwd.source_pk,
        lb.lead_date,
        lb.lead_date + INTERVAL '14 days' AS window_end_14d,
        COALESCE(SUM(sd.count_orders_completed), 0) AS trips_in_14d
    FROM leads_with_driver_cte lwd
    INNER JOIN leads_base lb ON lb.source_pk = lwd.source_pk
    LEFT JOIN (
        SELECT 
            driver_id,
            to_date(date_file, 'DD-MM-YYYY') AS prod_date,
            count_orders_completed
        FROM public.summary_daily
        WHERE date_file IS NOT NULL
            AND date_file ~ '^\d{2}-\d{2}-\d{4}$'
    ) sd
        ON sd.driver_id = lwd.driver_id
        AND sd.prod_date >= lb.lead_date
        AND sd.prod_date < lb.lead_date + INTERVAL '14 days'
    GROUP BY lwd.week_start, lwd.driver_id, lwd.source_pk, lb.lead_date
),
drivers_with_trips_14d_by_week AS (
    -- Agregar drivers con trips 14d por semana
    SELECT 
        week_start,
        COUNT(DISTINCT driver_id) AS drivers_with_trips_14d,
        COUNT(DISTINCT CASE WHEN trips_in_14d >= 1 THEN driver_id END) AS reached_m1_14d_count,
        COUNT(DISTINCT CASE WHEN trips_in_14d >= 5 THEN driver_id END) AS reached_m5_14d_count,
        COUNT(DISTINCT CASE WHEN trips_in_14d >= 25 THEN driver_id END) AS reached_m25_14d_count,
        SUM(trips_in_14d) AS total_trips_14d_sum
    FROM drivers_with_trips_14d_cte
    GROUP BY week_start
),
milestones_expected_by_week AS (
    -- Claims esperados según milestones alcanzados
    SELECT 
        week_start,
        COUNT(DISTINCT CASE WHEN trips_in_14d >= 1 THEN driver_id END) AS claims_expected_m1,
        COUNT(DISTINCT CASE WHEN trips_in_14d >= 5 THEN driver_id END) AS claims_expected_m5,
        COUNT(DISTINCT CASE WHEN trips_in_14d >= 25 THEN driver_id END) AS claims_expected_m25,
        -- Montos esperados (acumulativo)
        SUM(
            CASE 
                WHEN trips_in_14d >= 25 THEN (25 + 35 + 100)::numeric(12,2)
                WHEN trips_in_14d >= 5 THEN (25 + 35)::numeric(12,2)
                WHEN trips_in_14d >= 1 THEN 25::numeric(12,2)
                ELSE 0::numeric(12,2)
            END
        ) AS debt_expected_total
    FROM drivers_with_trips_14d_cte
    GROUP BY week_start
),
claims_present_by_week AS (
    -- Claims que realmente existen en v_claims_payment_status_cabinet
    -- NOTA: v_claims_payment_status_cabinet ya está filtrada para cabinet, no necesita origin_tag
    SELECT 
        DATE_TRUNC('week', c.lead_date)::date AS week_start,
        COUNT(DISTINCT CASE WHEN c.milestone_value = 1 THEN c.driver_id END) AS claims_present_m1,
        COUNT(DISTINCT CASE WHEN c.milestone_value = 5 THEN c.driver_id END) AS claims_present_m5,
        COUNT(DISTINCT CASE WHEN c.milestone_value = 25 THEN c.driver_id END) AS claims_present_m25
    FROM ops.v_claims_payment_status_cabinet c
    WHERE c.lead_date IS NOT NULL
    GROUP BY DATE_TRUNC('week', c.lead_date)::date
),
limbo_counts_by_week AS (
    -- Conteos de limbo por semana desde v_cabinet_leads_limbo
    SELECT 
        week_start,
        COUNT(*) FILTER (WHERE limbo_stage = 'NO_IDENTITY') AS limbo_no_identity,
        COUNT(*) FILTER (WHERE limbo_stage = 'NO_DRIVER') AS limbo_no_driver,
        COUNT(*) FILTER (WHERE limbo_stage = 'NO_TRIPS_14D') AS limbo_no_trips_14d,
        COUNT(*) FILTER (WHERE limbo_stage = 'TRIPS_NO_CLAIM') AS limbo_trips_no_claim,
        COUNT(*) FILTER (WHERE limbo_stage = 'OK') AS limbo_ok
    FROM ops.v_cabinet_leads_limbo
    WHERE week_start IS NOT NULL
    GROUP BY week_start
)
SELECT 
    COALESCE(lbw.week_start, lwi.week_start, lwd.week_start, dwt.week_start, me.week_start, cp.week_start, limbo_counts.week_start) AS week_start,
    -- Leads totales
    COALESCE(lbw.leads_total, 0) AS leads_total,
    COALESCE(lbw.leads_distinct_pk, 0) AS leads_distinct_pk,
    -- Leads con identity
    COALESCE(lwi.leads_with_identity, 0) AS leads_with_identity,
    COALESCE(lwi.distinct_person_keys, 0) AS distinct_person_keys,
    -- Leads con driver
    COALESCE(lwd.leads_with_driver, 0) AS leads_with_driver,
    COALESCE(lwd.distinct_drivers, 0) AS distinct_drivers,
    -- Drivers con trips 14d
    COALESCE(dwt.drivers_with_trips_14d, 0) AS drivers_with_trips_14d,
    COALESCE(dwt.reached_m1_14d_count, 0) AS reached_m1_14d,
    COALESCE(dwt.reached_m5_14d_count, 0) AS reached_m5_14d,
    COALESCE(dwt.reached_m25_14d_count, 0) AS reached_m25_14d,
    COALESCE(dwt.total_trips_14d_sum, 0) AS total_trips_14d_sum,
    -- Claims esperados
    COALESCE(me.claims_expected_m1, 0) AS claims_expected_m1,
    COALESCE(me.claims_expected_m5, 0) AS claims_expected_m5,
    COALESCE(me.claims_expected_m25, 0) AS claims_expected_m25,
    COALESCE(me.debt_expected_total, 0::numeric(12,2)) AS debt_expected_total,
    -- Claims presentes
    COALESCE(cp.claims_present_m1, 0) AS claims_present_m1,
    COALESCE(cp.claims_present_m5, 0) AS claims_present_m5,
    COALESCE(cp.claims_present_m25, 0) AS claims_present_m25,
    -- Gaps (claims faltantes)
    (COALESCE(me.claims_expected_m1, 0) - COALESCE(cp.claims_present_m1, 0)) AS claims_missing_m1,
    (COALESCE(me.claims_expected_m5, 0) - COALESCE(cp.claims_present_m5, 0)) AS claims_missing_m5,
    (COALESCE(me.claims_expected_m25, 0) - COALESCE(cp.claims_present_m25, 0)) AS claims_missing_m25,
    -- Limbo counts por stage (desde v_cabinet_leads_limbo)
    COALESCE(limbo_counts.limbo_no_identity, 0) AS limbo_no_identity,
    COALESCE(limbo_counts.limbo_no_driver, 0) AS limbo_no_driver,
    COALESCE(limbo_counts.limbo_no_trips_14d, 0) AS limbo_no_trips_14d,
    COALESCE(limbo_counts.limbo_trips_no_claim, 0) AS limbo_trips_no_claim,
    COALESCE(limbo_counts.limbo_ok, 0) AS limbo_ok,
    -- Tasa de conversión (porcentajes)
    CASE 
        WHEN COALESCE(lbw.leads_total, 0) > 0 
        THEN ROUND(100.0 * COALESCE(lwi.leads_with_identity, 0) / lbw.leads_total, 2)
        ELSE 0
    END AS pct_with_identity,
    CASE 
        WHEN COALESCE(lwi.leads_with_identity, 0) > 0 
        THEN ROUND(100.0 * COALESCE(lwd.leads_with_driver, 0) / lwi.leads_with_identity, 2)
        ELSE 0
    END AS pct_with_driver,
    CASE 
        WHEN COALESCE(lwd.leads_with_driver, 0) > 0 
        THEN ROUND(100.0 * COALESCE(dwt.drivers_with_trips_14d, 0) / lwd.leads_with_driver, 2)
        ELSE 0
    END AS pct_with_trips_14d
FROM leads_by_week lbw
FULL OUTER JOIN leads_with_identity_by_week lwi ON lwi.week_start = lbw.week_start
FULL OUTER JOIN leads_with_driver_by_week lwd ON lwd.week_start = COALESCE(lbw.week_start, lwi.week_start)
FULL OUTER JOIN drivers_with_trips_14d_by_week dwt ON dwt.week_start = COALESCE(lbw.week_start, lwi.week_start, lwd.week_start)
FULL OUTER JOIN milestones_expected_by_week me ON me.week_start = COALESCE(lbw.week_start, lwi.week_start, lwd.week_start, dwt.week_start)
FULL OUTER JOIN claims_present_by_week cp ON cp.week_start = COALESCE(lbw.week_start, lwi.week_start, lwd.week_start, dwt.week_start, me.week_start)
FULL OUTER JOIN limbo_counts_by_week limbo_counts ON limbo_counts.week_start = COALESCE(lbw.week_start, lwi.week_start, lwd.week_start, dwt.week_start, me.week_start, cp.week_start)
ORDER BY week_start DESC;

-- ============================================================================
-- Comentarios de la Vista
-- ============================================================================
COMMENT ON VIEW ops.v_cabinet_14d_funnel_audit_weekly IS 
'Auditoría semanal del embudo de Cobranza 14d por lead_date. Identifica el punto exacto de ruptura en el flujo de leads. Grano: 1 fila por week_start (semana ISO truncada desde lead_date).';

COMMENT ON COLUMN ops.v_cabinet_14d_funnel_audit_weekly.week_start IS 
'Inicio de semana ISO (date_trunc(''week'', lead_date)::date). Usado para agrupar leads por semana.';

COMMENT ON COLUMN ops.v_cabinet_14d_funnel_audit_weekly.leads_total IS 
'Total de leads en module_ct_cabinet_leads con lead_created_at en esa semana. Universo base.';

COMMENT ON COLUMN ops.v_cabinet_14d_funnel_audit_weekly.leads_with_identity IS 
'Leads que tienen person_key en canon.identity_links (source_table=''module_ct_cabinet_leads'').';

COMMENT ON COLUMN ops.v_cabinet_14d_funnel_audit_weekly.leads_with_driver IS 
'Leads que tienen driver_id (identity_link -> drivers).';

COMMENT ON COLUMN ops.v_cabinet_14d_funnel_audit_weekly.drivers_with_trips_14d IS 
'Drivers con viajes dentro de ventana 14d desde lead_date (summary_daily).';

COMMENT ON COLUMN ops.v_cabinet_14d_funnel_audit_weekly.reached_m1_14d IS 
'Drivers que alcanzaron M1 dentro de ventana 14d (trips_in_14d >= 1).';

COMMENT ON COLUMN ops.v_cabinet_14d_funnel_audit_weekly.reached_m5_14d IS 
'Drivers que alcanzaron M5 dentro de ventana 14d (trips_in_14d >= 5).';

COMMENT ON COLUMN ops.v_cabinet_14d_funnel_audit_weekly.reached_m25_14d IS 
'Drivers que alcanzaron M25 dentro de ventana 14d (trips_in_14d >= 25).';

COMMENT ON COLUMN ops.v_cabinet_14d_funnel_audit_weekly.claims_expected_m1 IS 
'Claims M1 que deberían existir según milestones alcanzados (reached_m1_14d).';

COMMENT ON COLUMN ops.v_cabinet_14d_funnel_audit_weekly.claims_expected_m5 IS 
'Claims M5 que deberían existir según milestones alcanzados (reached_m5_14d).';

COMMENT ON COLUMN ops.v_cabinet_14d_funnel_audit_weekly.claims_expected_m25 IS 
'Claims M25 que deberían existir según milestones alcanzados (reached_m25_14d).';

COMMENT ON COLUMN ops.v_cabinet_14d_funnel_audit_weekly.claims_present_m1 IS 
'Claims M1 que realmente existen en ops.v_claims_payment_status_cabinet.';

COMMENT ON COLUMN ops.v_cabinet_14d_funnel_audit_weekly.claims_present_m5 IS 
'Claims M5 que realmente existen en ops.v_claims_payment_status_cabinet.';

COMMENT ON COLUMN ops.v_cabinet_14d_funnel_audit_weekly.claims_present_m25 IS 
'Claims M25 que realmente existen en ops.v_claims_payment_status_cabinet.';

COMMENT ON COLUMN ops.v_cabinet_14d_funnel_audit_weekly.debt_expected_total IS 
'Monto esperado total por semana según milestones alcanzados (acumulativo: M1=25, M5=+35, M25=+100).';

COMMENT ON COLUMN ops.v_cabinet_14d_funnel_audit_weekly.claims_missing_m1 IS 
'Gap: claims M1 faltantes (claims_expected_m1 - claims_present_m1).';

COMMENT ON COLUMN ops.v_cabinet_14d_funnel_audit_weekly.claims_missing_m5 IS 
'Gap: claims M5 faltantes (claims_expected_m5 - claims_present_m5).';

COMMENT ON COLUMN ops.v_cabinet_14d_funnel_audit_weekly.claims_missing_m25 IS 
'Gap: claims M25 faltantes (claims_expected_m25 - claims_present_m25).';

COMMENT ON COLUMN ops.v_cabinet_14d_funnel_audit_weekly.pct_with_identity IS 
'Porcentaje de leads con identity (leads_with_identity / leads_total * 100).';

COMMENT ON COLUMN ops.v_cabinet_14d_funnel_audit_weekly.pct_with_driver IS 
'Porcentaje de leads con identity que tienen driver_id (leads_with_driver / leads_with_identity * 100).';

COMMENT ON COLUMN ops.v_cabinet_14d_funnel_audit_weekly.pct_with_trips_14d IS 
'Porcentaje de leads con driver que tienen trips 14d (drivers_with_trips_14d / leads_with_driver * 100).';

COMMENT ON COLUMN ops.v_cabinet_14d_funnel_audit_weekly.limbo_no_identity IS 
'Conteo de leads en limbo NO_IDENTITY por semana (desde ops.v_cabinet_leads_limbo).';

COMMENT ON COLUMN ops.v_cabinet_14d_funnel_audit_weekly.limbo_no_driver IS 
'Conteo de leads en limbo NO_DRIVER por semana (desde ops.v_cabinet_leads_limbo).';

COMMENT ON COLUMN ops.v_cabinet_14d_funnel_audit_weekly.limbo_no_trips_14d IS 
'Conteo de leads en limbo NO_TRIPS_14D por semana (desde ops.v_cabinet_leads_limbo).';

COMMENT ON COLUMN ops.v_cabinet_14d_funnel_audit_weekly.limbo_trips_no_claim IS 
'Conteo de leads en limbo TRIPS_NO_CLAIM por semana (desde ops.v_cabinet_leads_limbo).';

COMMENT ON COLUMN ops.v_cabinet_14d_funnel_audit_weekly.limbo_ok IS 
'Conteo de leads OK (completos) por semana (desde ops.v_cabinet_leads_limbo).';
