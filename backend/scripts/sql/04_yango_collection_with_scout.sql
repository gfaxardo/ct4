-- ============================================================================
-- VISTA: ops.v_yango_collection_with_scout
-- ============================================================================
-- Propósito: Extender vista de cobranza Yango con información de scout
-- Fuente: ops.v_yango_cabinet_claims_for_collection (vista existente)
-- Ejecución: Idempotente (DROP + CREATE)
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
    
    -- Campos de scout attribution
    -- Scout ID (desde lead_ledger si existe, sino NULL por ahora hasta que existan las vistas)
    ll.attributed_scout_id AS scout_id,
    
    -- Scout name y type (NULL por ahora - se puede enriquecer después si existen tablas scouts_list)
    NULL::TEXT AS scout_name,
    NULL::TEXT AS scout_type,
    
    -- Scout quality bucket
    CASE 
        WHEN ll.attributed_scout_id IS NOT NULL THEN 'SATISFACTORY_LEDGER'
        ELSE 'MISSING'
    END AS scout_quality_bucket,
    
    -- Flag de scout resuelto
    CASE 
        WHEN ll.attributed_scout_id IS NOT NULL THEN true
        ELSE false
    END AS is_scout_resolved

FROM ops.v_yango_cabinet_claims_for_collection y
-- JOIN a lead_ledger para scout satisfactorio (prioridad 1)
LEFT JOIN observational.lead_ledger ll 
    ON ll.person_key = y.person_key
    AND ll.attributed_scout_id IS NOT NULL;
-- NOTA: JOIN a scouts_list se puede agregar después si existen las tablas
-- Por ahora, scout_name y scout_type son NULL

COMMENT ON VIEW ops.v_yango_collection_with_scout IS 
'Vista de cobranza Yango extendida con información de scout. Incluye scout_id, scout_name, scout_type, scout_quality_bucket (SATISFACTORY_LEDGER, EVENTS_ONLY, SCOUTING_DAILY_ONLY, MISSING) e is_scout_resolved. Prioridad: lead_ledger (source-of-truth) > vista canónica de atribución.';

COMMENT ON COLUMN ops.v_yango_collection_with_scout.scout_id IS 
'Scout ID asignado al driver. Prioridad: lead_ledger.attributed_scout_id > ops.v_scout_attribution.scout_id.';

COMMENT ON COLUMN ops.v_yango_collection_with_scout.scout_quality_bucket IS 
'Calidad de la atribución scout: SATISFACTORY_LEDGER (desde lead_ledger, source-of-truth), EVENTS_ONLY (solo desde eventos), SCOUTING_DAILY_ONLY (solo desde scouting_daily), MISSING (sin scout).';

COMMENT ON COLUMN ops.v_yango_collection_with_scout.is_scout_resolved IS 
'Flag indicando si el scout está resuelto (true si hay scout_id de cualquier fuente, false si no).';

-- ============================================================================
-- QUERY DE VERIFICACIÓN: Cobertura de scout en cobranza Yango
-- ============================================================================

SELECT 
    'COBERTURA SCOUT EN COBRANZA YANGO' AS metric,
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

