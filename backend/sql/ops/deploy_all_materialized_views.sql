-- ============================================================================
-- SCRIPT MAESTRO: Despliegue de Todas las Vistas Materializadas
-- ============================================================================
-- PROPÓSITO:
-- Crear y refrescar todas las MVs necesarias para optimizar el rendimiento
-- de las APIs de Cobranza Yango y Dashboard.
-- ============================================================================
-- EJECUCIÓN:
-- psql -h localhost -U postgres -d ct4 -f deploy_all_materialized_views.sql
-- ============================================================================

\echo '=============================================='
\echo 'INICIO: Despliegue de Vistas Materializadas'
\echo '=============================================='

-- ============================================================================
-- PASO 1: Crear MVs base (sin dependencias)
-- ============================================================================

\echo ''
\echo '>>> PASO 1: Creando MVs base...'

-- 1.1: mv_cabinet_financial_14d
\echo '  [1/8] Creando ops.mv_cabinet_financial_14d...'

DROP MATERIALIZED VIEW IF EXISTS ops.mv_cabinet_financial_14d CASCADE;

CREATE MATERIALIZED VIEW ops.mv_cabinet_financial_14d AS
SELECT * FROM ops.v_cabinet_financial_14d;

CREATE UNIQUE INDEX idx_mv_cabinet_fin_driver_id_unique 
ON ops.mv_cabinet_financial_14d(driver_id);

CREATE INDEX idx_mv_cabinet_financial_14d_lead_date 
ON ops.mv_cabinet_financial_14d(lead_date);

CREATE INDEX idx_mv_cabinet_financial_14d_amount_due 
ON ops.mv_cabinet_financial_14d(amount_due_yango DESC) 
WHERE amount_due_yango > 0;

CREATE INDEX idx_mv_cabinet_financial_14d_expected_total 
ON ops.mv_cabinet_financial_14d(expected_total_yango DESC) 
WHERE expected_total_yango > 0;

\echo '  ✓ mv_cabinet_financial_14d creada'

-- 1.2: mv_claims_payment_status_cabinet
\echo '  [2/8] Creando ops.mv_claims_payment_status_cabinet...'

DROP MATERIALIZED VIEW IF EXISTS ops.mv_claims_payment_status_cabinet CASCADE;

CREATE MATERIALIZED VIEW ops.mv_claims_payment_status_cabinet AS
SELECT 
    driver_id,
    person_key,
    milestone_value,
    lead_date,
    due_date,
    expected_amount,
    days_overdue,
    bucket_overdue,
    paid_flag,
    paid_date,
    payment_key,
    payment_identity_status,
    payment_match_rule,
    payment_match_confidence,
    payment_status,
    payment_reason,
    reason_code,
    action_priority
FROM ops.v_claims_payment_status_cabinet;

CREATE UNIQUE INDEX idx_mv_claims_driver_milestone 
ON ops.mv_claims_payment_status_cabinet(driver_id, milestone_value) 
WHERE driver_id IS NOT NULL;

CREATE INDEX idx_mv_claims_person_key 
ON ops.mv_claims_payment_status_cabinet(person_key) 
WHERE person_key IS NOT NULL;

CREATE INDEX idx_mv_claims_reason_code 
ON ops.mv_claims_payment_status_cabinet(reason_code);

CREATE INDEX idx_mv_claims_paid_flag 
ON ops.mv_claims_payment_status_cabinet(paid_flag);

CREATE INDEX idx_mv_claims_lead_date 
ON ops.mv_claims_payment_status_cabinet(lead_date DESC);

\echo '  ✓ mv_claims_payment_status_cabinet creada'

-- ============================================================================
-- PASO 2: Crear MV enriquecida (depende de v_cabinet_financial_14d)
-- ============================================================================

\echo ''
\echo '>>> PASO 2: Creando MV enriquecida...'

-- 2.1: mv_yango_cabinet_cobranza_enriched_14d
\echo '  [3/8] Creando ops.mv_yango_cabinet_cobranza_enriched_14d...'

DROP MATERIALIZED VIEW IF EXISTS ops.mv_yango_cabinet_cobranza_enriched_14d CASCADE;

CREATE MATERIALIZED VIEW ops.mv_yango_cabinet_cobranza_enriched_14d AS
SELECT 
    -- Campos base de v_cabinet_financial_14d
    cf.driver_id,
    cf.driver_name,
    cf.lead_date,
    cf.iso_week,
    -- week_start: lunes de la semana ISO (canónico)
    DATE_TRUNC('week', cf.lead_date)::date AS week_start,
    cf.connected_flag,
    cf.connected_date,
    cf.total_trips_14d,
    cf.reached_m1_14d,
    cf.reached_m5_14d,
    cf.reached_m25_14d,
    cf.expected_amount_m1,
    cf.expected_amount_m5,
    cf.expected_amount_m25,
    cf.expected_total_yango,
    cf.claim_m1_exists,
    cf.claim_m1_paid,
    cf.claim_m5_exists,
    cf.claim_m5_paid,
    cf.claim_m25_exists,
    cf.claim_m25_paid,
    cf.paid_amount_m1,
    cf.paid_amount_m5,
    cf.paid_amount_m25,
    cf.total_paid_yango,
    cf.amount_due_yango,
    
    -- Campos de scout attribution (desde vista canónica si existe)
    sa.scout_id,
    ds.raw_name AS scout_name,
    ds.scout_name_normalized,
    ds.is_active AS scout_is_active,
    
    -- Scout quality bucket (basado en fuente)
    CASE 
        WHEN sa.source_table = 'observational.lead_ledger' THEN 'SATISFACTORY_LEDGER'
        WHEN sa.source_table = 'observational.lead_events' THEN 'EVENTS_ONLY'
        WHEN sa.source_table = 'public.module_ct_migrations' THEN 'MIGRATIONS_ONLY'
        WHEN sa.source_table = 'public.module_ct_scouting_daily' OR sa.source_table = 'module_ct_scouting_daily' THEN 'SCOUTING_DAILY_ONLY'
        WHEN sa.source_table = 'public.module_ct_cabinet_payments' THEN 'CABINET_PAYMENTS_ONLY'
        WHEN sa.scout_id IS NOT NULL THEN 'SCOUTING_DAILY_ONLY'
        ELSE 'MISSING'
    END AS scout_quality_bucket,
    
    -- Flag de scout resuelto
    CASE 
        WHEN sa.scout_id IS NOT NULL THEN true
        ELSE false
    END AS is_scout_resolved,
    
    -- Metadata adicional de atribución
    sa.source_table AS scout_source_table,
    sa.attribution_date AS scout_attribution_date,
    sa.priority AS scout_priority,
    
    -- Person key
    il_driver.person_key

FROM ops.v_cabinet_financial_14d cf
-- Obtener person_key desde identity_links
LEFT JOIN LATERAL (
    SELECT DISTINCT person_key
    FROM canon.identity_links il
    WHERE il.source_table = 'drivers'
        AND il.source_pk = cf.driver_id::TEXT
    LIMIT 1
) il_driver ON true
-- Usar vista canónica de atribución (si existe)
LEFT JOIN ops.v_scout_attribution sa
    ON (sa.person_key = il_driver.person_key AND il_driver.person_key IS NOT NULL)
    OR (sa.driver_id = cf.driver_id AND (il_driver.person_key IS NULL OR sa.person_key IS NULL))
-- Enriquecer con nombre del scout
LEFT JOIN ops.v_dim_scouts ds
    ON ds.scout_id = sa.scout_id;

-- Índices
CREATE UNIQUE INDEX idx_mv_cobranza_enriched_driver_id_unique
ON ops.mv_yango_cabinet_cobranza_enriched_14d(driver_id);

CREATE INDEX idx_mv_cobranza_enriched_lead_date 
ON ops.mv_yango_cabinet_cobranza_enriched_14d(lead_date DESC);

CREATE INDEX idx_mv_cobranza_enriched_week_start 
ON ops.mv_yango_cabinet_cobranza_enriched_14d(week_start DESC);

CREATE INDEX idx_mv_cobranza_enriched_scout_id 
ON ops.mv_yango_cabinet_cobranza_enriched_14d(scout_id) 
WHERE scout_id IS NOT NULL;

CREATE INDEX idx_mv_cobranza_enriched_debt_partial 
ON ops.mv_yango_cabinet_cobranza_enriched_14d(amount_due_yango DESC) 
WHERE amount_due_yango > 0;

CREATE INDEX idx_mv_cobranza_enriched_milestone_flags 
ON ops.mv_yango_cabinet_cobranza_enriched_14d(reached_m1_14d, reached_m5_14d, reached_m25_14d);

\echo '  ✓ mv_yango_cabinet_cobranza_enriched_14d creada'

-- ============================================================================
-- PASO 3: Crear índices adicionales en tablas base
-- ============================================================================

\echo ''
\echo '>>> PASO 3: Creando índices adicionales...'

-- Índice para mejorar funnel_gap query
\echo '  [4/8] Creando índice en canon.identity_links...'

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_identity_links_source_cabinet
ON canon.identity_links(source_table, source_pk)
WHERE source_table = 'module_ct_cabinet_leads';

\echo '  ✓ Índice en identity_links creado'

-- ============================================================================
-- PASO 4: Comentarios de vistas
-- ============================================================================

\echo ''
\echo '>>> PASO 4: Agregando comentarios...'

COMMENT ON MATERIALIZED VIEW ops.mv_cabinet_financial_14d IS 
'MV de ops.v_cabinet_financial_14d para mejorar rendimiento. Grano: 1 fila por driver_id. Refrescar diariamente.';

COMMENT ON MATERIALIZED VIEW ops.mv_claims_payment_status_cabinet IS 
'MV de claims payment status con JOINs LATERAL costosos precalculados. Refrescar cada hora o cuando hay nuevos claims.';

COMMENT ON MATERIALIZED VIEW ops.mv_yango_cabinet_cobranza_enriched_14d IS 
'MV final para Cobranza Yango con atribución scout. Incluye todos los campos financieros + scout. Refrescar diariamente.';

\echo '  ✓ Comentarios agregados'

-- ============================================================================
-- RESUMEN FINAL
-- ============================================================================

\echo ''
\echo '=============================================='
\echo 'DESPLIEGUE COMPLETADO'
\echo '=============================================='
\echo ''
\echo 'Vistas materializadas creadas:'
\echo '  1. ops.mv_cabinet_financial_14d'
\echo '  2. ops.mv_claims_payment_status_cabinet'
\echo '  3. ops.mv_yango_cabinet_cobranza_enriched_14d'
\echo ''
\echo 'Para refrescar en el futuro:'
\echo '  REFRESH MATERIALIZED VIEW CONCURRENTLY ops.mv_cabinet_financial_14d;'
\echo '  REFRESH MATERIALIZED VIEW CONCURRENTLY ops.mv_claims_payment_status_cabinet;'
\echo '  REFRESH MATERIALIZED VIEW CONCURRENTLY ops.mv_yango_cabinet_cobranza_enriched_14d;'
\echo ''
