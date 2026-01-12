-- ============================================================================
-- VISTA: ops.v_yango_collection_with_scout (ENRIQUECIDA)
-- ============================================================================
-- Propósito: Extender vista de cobranza Yango con información de scout
-- Fuente: ops.v_yango_cabinet_claims_for_collection (vista existente)
-- Ejecución: Idempotente (DROP + CREATE)
-- ============================================================================
-- CAMBIOS RESPECTO A LA VERSIÓN ORIGINAL:
-- - Usa ops.v_scout_attribution (vista canónica multifuente) en lugar de solo lead_ledger
-- - Enriquece scout_name desde ops.v_dim_scouts
-- - Agrega metadata de fuente (source_table, origin_tag, priority)
-- ============================================================================

DROP VIEW IF EXISTS ops.v_yango_collection_with_scout CASCADE;
CREATE VIEW ops.v_yango_collection_with_scout AS
SELECT 
    -- Campos originales de cobranza Yango
    y.driver_id,
    y.person_key,
    y.driver_name,
    y.milestone_value,
    y.lead_date,
    y.expected_amount,
    y.yango_due_date,
    y.days_overdue_yango,
    y.overdue_bucket_yango,
    y.yango_payment_status,
    y.payment_key,
    y.pay_date,
    y.reason_code,
    y.match_rule,
    y.match_confidence,
    y.identity_status,
    y.suggested_driver_id,
    y.is_reconcilable_enriched,
    
    -- Campos de scout attribution (desde vista canónica multifuente)
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
        WHEN sa.scout_id IS NOT NULL THEN 'SCOUTING_DAILY_ONLY'  -- Fallback: si hay scout_id pero source_table no matchea, asumir scouting_daily
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
    sa.priority AS scout_priority

FROM ops.v_yango_cabinet_claims_for_collection y
-- Usar vista canónica de atribución (multifuente) en lugar de solo lead_ledger
LEFT JOIN ops.v_scout_attribution sa
    ON (sa.person_key = y.person_key AND y.person_key IS NOT NULL)
    OR (sa.driver_id = y.driver_id AND y.person_key IS NULL AND sa.person_key IS NULL)
-- Enriquecer con nombre del scout
LEFT JOIN ops.v_dim_scouts ds
    ON ds.scout_id = sa.scout_id;

COMMENT ON VIEW ops.v_yango_collection_with_scout IS 
'Vista de cobranza Yango extendida con información de scout. Incluye scout_id, scout_name (desde module_ct_scouts_list), scout_quality_bucket y metadata de atribución. Usa ops.v_scout_attribution como fuente canónica que agrega todas las fuentes RAW (lead_ledger, lead_events, migrations, scouting_daily, cabinet_payments).';

COMMENT ON COLUMN ops.v_yango_collection_with_scout.scout_id IS 
'Scout ID asignado al driver. Fuente canónica: ops.v_scout_attribution (agrega múltiples fuentes con prioridad).';

COMMENT ON COLUMN ops.v_yango_collection_with_scout.scout_name IS 
'Nombre del scout desde module_ct_scouts_list (raw_name).';

COMMENT ON COLUMN ops.v_yango_collection_with_scout.scout_quality_bucket IS 
'Calidad de la atribución scout basada en la fuente: SATISFACTORY_LEDGER (lead_ledger), EVENTS_ONLY, MIGRATIONS_ONLY, SCOUTING_DAILY_ONLY, CABINET_PAYMENTS_ONLY, MISSING.';

COMMENT ON COLUMN ops.v_yango_collection_with_scout.scout_source_table IS 
'Tabla fuente de donde proviene el scout_id (para auditoría).';

-- ============================================================================
-- QUERY DE VERIFICACIÓN: Cobertura de scout en cobranza Yango
-- ============================================================================

SELECT 
    'COBERTURA SCOUT EN COBRANZA YANGO (ENRIQUECIDA)' AS metric,
    COUNT(*) AS total_claims,
    COUNT(*) FILTER (WHERE is_scout_resolved = true) AS claims_with_scout,
    COUNT(*) FILTER (WHERE is_scout_resolved = false) AS claims_without_scout,
    ROUND((COUNT(*) FILTER (WHERE is_scout_resolved = true)::NUMERIC / NULLIF(COUNT(*), 0) * 100), 2) AS pct_with_scout
FROM ops.v_yango_collection_with_scout;

-- Distribución por scout_quality_bucket
SELECT 
    scout_quality_bucket,
    COUNT(*) AS claim_count,
    ROUND(COUNT(*)::NUMERIC / NULLIF((SELECT COUNT(*) FROM ops.v_yango_collection_with_scout), 0) * 100, 2) AS pct
FROM ops.v_yango_collection_with_scout
GROUP BY scout_quality_bucket
ORDER BY claim_count DESC;

-- Distribución por fuente (source_table)
SELECT 
    scout_source_table,
    COUNT(*) AS claim_count,
    ROUND(COUNT(*)::NUMERIC / NULLIF((SELECT COUNT(*) FROM ops.v_yango_collection_with_scout WHERE is_scout_resolved = true), 0) * 100, 2) AS pct
FROM ops.v_yango_collection_with_scout
WHERE is_scout_resolved = true
GROUP BY scout_source_table
ORDER BY claim_count DESC;
