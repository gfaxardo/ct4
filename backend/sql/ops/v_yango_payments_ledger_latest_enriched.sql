-- ============================================================================
-- Vista: Ledger Yango con Identidad Enriquecida V2
-- ============================================================================
-- PROBLEMA RESUELTO:
-- El ledger fue ingested antes de implementar matching por nombre, por lo que
-- driver_id/person_key están NULL en la tabla base. Esta versión hace JOIN
-- en tiempo real con ops.v_yango_payments_raw_current para obtener la identidad
-- más reciente calculada por la vista de matching.
--
-- ESTRATEGIA:
-- 1. Obtener último estado del ledger (v_yango_payments_ledger_latest)
-- 2. JOIN con v_yango_payments_raw_current por payment_key para hidratar identidad
-- 3. Si raw_current tiene driver_id → usarlo como driver_id_from_matching
-- 4. Mantener compatibilidad con columnas existentes
--
-- RESULTADO:
-- - driver_id_final NO NULL para ~68% de pagados (matching por nombre único)
-- - identity_status correcto basado en match_rule de raw_current
--
-- COLUMNAS EXPUESTAS:
-- - driver_id_original: driver_id desde ledger (generalmente NULL por ingest antiguo)
-- - driver_id_enriched: driver_id obtenido de raw_current por matching
-- - driver_id_final: COALESCE(ledger, raw_current)
-- - person_key_original, person_key_final
-- - identity_status: 'confirmed' | 'enriched' | 'ambiguous' | 'no_match'
-- - match_rule: 'source_upstream' | 'name_unique' | 'ambiguous' | 'no_match'
-- - match_confidence: 'high' | 'medium' | 'low'
-- - identity_enriched: boolean
-- ============================================================================

DROP VIEW IF EXISTS ops.v_yango_payments_ledger_latest_enriched CASCADE;

CREATE VIEW ops.v_yango_payments_ledger_latest_enriched AS
WITH ledger_latest AS (
    SELECT 
        id,
        latest_snapshot_at,
        source_table,
        source_pk,
        pay_date,
        pay_time,
        raw_driver_name,
        driver_name_normalized,
        milestone_type,
        milestone_value,
        is_paid,
        paid_flag_source,
        driver_id AS ledger_driver_id,
        person_key AS ledger_person_key,
        match_rule AS ledger_match_rule,
        match_confidence AS ledger_match_confidence,
        payment_key,
        state_hash,
        created_at
    FROM ops.v_yango_payments_ledger_latest
),
-- Join con raw_current para obtener la identidad más reciente calculada
enriched AS (
    SELECT 
        ll.*,
        -- Identidad desde raw_current (matching por nombre)
        rc.driver_id AS raw_driver_id,
        rc.person_key AS raw_person_key,
        rc.match_rule AS raw_match_rule,
        rc.match_confidence AS raw_match_confidence
    FROM ledger_latest ll
    LEFT JOIN ops.v_yango_payments_raw_current rc
        ON rc.payment_key = ll.payment_key
)
SELECT 
    e.id,
    e.latest_snapshot_at,
    e.source_table,
    e.source_pk,
    e.pay_date,
    e.pay_time,
    e.raw_driver_name,
    e.driver_name_normalized,
    e.milestone_type,
    e.milestone_value,
    e.is_paid,
    e.paid_flag_source,
    
    -- driver_id_original: lo que vino del ledger (casi siempre NULL por bug de ingest)
    e.ledger_driver_id AS driver_id_original,
    e.ledger_person_key AS person_key_original,
    
    -- driver_id_enriched: obtenido de raw_current por matching
    CASE 
        WHEN e.ledger_driver_id IS NULL AND e.raw_driver_id IS NOT NULL 
        THEN e.raw_driver_id
        ELSE NULL
    END AS driver_id_enriched,
    
    -- driver_id_final: COALESCE(ledger, raw_current)
    COALESCE(e.ledger_driver_id, e.raw_driver_id) AS driver_id_final,
    
    -- person_key_final
    COALESCE(e.ledger_person_key, e.raw_person_key) AS person_key_final,
    
    -- identity_status basado en fuente y match_rule
    CASE 
        -- Si el ledger ya tenía driver_id → confirmed (upstream)
        WHEN e.ledger_driver_id IS NOT NULL THEN 'confirmed'
        -- Si lo obtuvimos de raw_current con match único → enriched
        WHEN e.raw_driver_id IS NOT NULL AND e.raw_match_rule = 'driver_name_unique' THEN 'enriched'
        -- Si hay nombre pero no hay match o es ambiguo
        WHEN e.raw_driver_name IS NOT NULL AND e.raw_match_rule = 'none' THEN 'ambiguous'
        -- Si no hay nombre en absoluto
        ELSE 'no_match'
    END AS identity_status,
    
    -- match_rule: fuente del matching
    CASE 
        WHEN e.ledger_driver_id IS NOT NULL THEN 'source_upstream'
        WHEN e.raw_driver_id IS NOT NULL AND e.raw_match_rule = 'driver_name_unique' THEN 'name_unique'
        WHEN e.raw_match_rule = 'none' THEN 'ambiguous'
        ELSE 'no_match'
    END AS match_rule,
    
    -- match_confidence
    CASE 
        WHEN e.ledger_driver_id IS NOT NULL THEN 'high'
        WHEN e.raw_driver_id IS NOT NULL THEN 'medium'
        ELSE 'low'
    END AS match_confidence,
    
    -- Flag de enriquecimiento
    (e.ledger_driver_id IS NULL AND e.raw_driver_id IS NOT NULL) AS identity_enriched,
    
    -- Campos de auditoría
    e.payment_key,
    e.state_hash,
    e.created_at
FROM enriched e
ORDER BY e.latest_snapshot_at DESC, e.payment_key;

-- Comentarios
COMMENT ON VIEW ops.v_yango_payments_ledger_latest_enriched IS 
'Vista que enriquece el ledger con identidad obtenida de ops.v_yango_payments_raw_current en tiempo real. JOIN por payment_key para hidratar driver_id/person_key. Soluciona que el ledger fue ingested antes de matching.';

COMMENT ON COLUMN ops.v_yango_payments_ledger_latest_enriched.driver_id_original IS 
'Driver ID desde el ledger (generalmente NULL porque el ingest ocurrió antes del matching).';

COMMENT ON COLUMN ops.v_yango_payments_ledger_latest_enriched.driver_id_enriched IS 
'Driver ID obtenido de raw_current por matching de nombre único.';

COMMENT ON COLUMN ops.v_yango_payments_ledger_latest_enriched.driver_id_final IS 
'Driver ID final: COALESCE(ledger, raw_current). Prioridad a upstream si existe.';

COMMENT ON COLUMN ops.v_yango_payments_ledger_latest_enriched.person_key_final IS 
'Person Key final: COALESCE(ledger, raw_current).';

COMMENT ON COLUMN ops.v_yango_payments_ledger_latest_enriched.identity_status IS 
'Estado de identidad: confirmed (upstream), enriched (matching único), ambiguous (sin match único), no_match (sin datos).';

COMMENT ON COLUMN ops.v_yango_payments_ledger_latest_enriched.match_rule IS 
'Regla de matching: source_upstream, name_unique, ambiguous, no_match.';

COMMENT ON COLUMN ops.v_yango_payments_ledger_latest_enriched.match_confidence IS 
'Confianza del match: high (upstream), medium (matching único), low (sin match).';

COMMENT ON COLUMN ops.v_yango_payments_ledger_latest_enriched.identity_enriched IS 
'TRUE si la identidad fue obtenida por matching (no de upstream).';
