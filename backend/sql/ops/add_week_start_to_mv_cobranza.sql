-- ============================================================================
-- Migration: Agregar week_start a ops.mv_yango_cabinet_cobranza_enriched_14d
-- ============================================================================
-- PROPÓSITO:
-- Agregar campo week_start (lunes de la semana ISO) a la MV existente.
-- Estrategia: Recrear MV con week_start (PostgreSQL no permite ALTER MATERIALIZED VIEW)
-- ============================================================================
-- NOTA: Este script debe ejecutarse en una ventana de mantenimiento o con
-- cuidado ya que recrea la MV. El proceso es:
-- 1. Renombrar MV actual a backup
-- 2. Crear nueva MV con week_start
-- 3. Crear índices necesarios
-- 4. Refrescar MV
-- ============================================================================

BEGIN;

-- Paso 1: Renombrar MV actual a backup (si no existe ya)
DROP MATERIALIZED VIEW IF EXISTS ops.mv_yango_cabinet_cobranza_enriched_14d_backup;
ALTER MATERIALIZED VIEW IF EXISTS ops.mv_yango_cabinet_cobranza_enriched_14d 
RENAME TO mv_yango_cabinet_cobranza_enriched_14d_backup;

-- Paso 2: Crear nueva MV con week_start
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
    
    -- Campos de scout attribution (desde vista canónica)
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
        WHEN sa.scout_id IS NOT NULL THEN 'SCOUTING_DAILY_ONLY'  -- Fallback
        ELSE 'MISSING'
    END AS scout_quality_bucket,
    
    -- Flag de scout resuelto
    CASE 
        WHEN sa.scout_id IS NOT NULL THEN true
        ELSE false
    END AS is_scout_resolved,
    
    -- Metadata adicional de atribución (para auditoría)
    sa.source_table AS scout_source_table,
    sa.attribution_date AS scout_attribution_date,
    sa.priority AS scout_priority,
    
    -- Person key (obtenido desde identity_links)
    il_driver.person_key

FROM ops.v_cabinet_financial_14d cf
-- Obtener person_key desde identity_links para hacer JOIN con scout attribution
LEFT JOIN LATERAL (
    SELECT DISTINCT person_key
    FROM canon.identity_links il
    WHERE il.source_table = 'drivers'
        AND il.source_pk = cf.driver_id::TEXT
    LIMIT 1
) il_driver ON true
-- Usar vista canónica de atribución (multifuente)
LEFT JOIN ops.v_scout_attribution sa
    ON (sa.person_key = il_driver.person_key AND il_driver.person_key IS NOT NULL)
    OR (sa.driver_id = cf.driver_id AND (il_driver.person_key IS NULL OR sa.person_key IS NULL))
-- Enriquecer con nombre del scout
LEFT JOIN ops.v_dim_scouts ds
    ON ds.scout_id = sa.scout_id;

-- Paso 3: Crear índices (incluyendo el único necesario para REFRESH CONCURRENTLY)
-- Usar IF NOT EXISTS o DROP IF EXISTS para evitar errores si ya existen
CREATE UNIQUE INDEX IF NOT EXISTS idx_mv_cobranza_enriched_driver_id_unique
ON ops.mv_yango_cabinet_cobranza_enriched_14d(driver_id);

DROP INDEX IF EXISTS ops.idx_mv_cobranza_enriched_driver_id;
CREATE INDEX idx_mv_cobranza_enriched_driver_id 
ON ops.mv_yango_cabinet_cobranza_enriched_14d(driver_id);

DROP INDEX IF EXISTS ops.idx_mv_cobranza_enriched_lead_date;
CREATE INDEX idx_mv_cobranza_enriched_lead_date 
ON ops.mv_yango_cabinet_cobranza_enriched_14d(lead_date DESC);

DROP INDEX IF EXISTS ops.idx_mv_cobranza_enriched_week_start;
CREATE INDEX idx_mv_cobranza_enriched_week_start 
ON ops.mv_yango_cabinet_cobranza_enriched_14d(week_start DESC);

DROP INDEX IF EXISTS ops.idx_mv_cobranza_enriched_scout_id;
CREATE INDEX idx_mv_cobranza_enriched_scout_id 
ON ops.mv_yango_cabinet_cobranza_enriched_14d(scout_id) 
WHERE scout_id IS NOT NULL;

DROP INDEX IF EXISTS ops.idx_mv_cobranza_enriched_debt_partial;
CREATE INDEX idx_mv_cobranza_enriched_debt_partial 
ON ops.mv_yango_cabinet_cobranza_enriched_14d(amount_due_yango DESC) 
WHERE amount_due_yango > 0;

DROP INDEX IF EXISTS ops.idx_mv_cobranza_enriched_milestone_flags;
CREATE INDEX idx_mv_cobranza_enriched_milestone_flags 
ON ops.mv_yango_cabinet_cobranza_enriched_14d(reached_m1_14d, reached_m5_14d, reached_m25_14d);

DROP INDEX IF EXISTS ops.idx_mv_cobranza_enriched_scout_quality;
CREATE INDEX idx_mv_cobranza_enriched_scout_quality 
ON ops.mv_yango_cabinet_cobranza_enriched_14d(scout_quality_bucket) 
WHERE scout_quality_bucket IS NOT NULL;

COMMIT;

-- Paso 4: Refrescar MV (debe ejecutarse después del COMMIT)
-- NOTA: Ejecutar manualmente después de aplicar este script:
-- REFRESH MATERIALIZED VIEW CONCURRENTLY ops.mv_yango_cobranza_enriched_14d;

-- Comentarios
COMMENT ON COLUMN ops.mv_yango_cabinet_cobranza_enriched_14d.week_start IS 
'Lunes de la semana ISO calculado desde lead_date. Usado para agregación semanal y filtros por semana.';
