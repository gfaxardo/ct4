-- ============================================================================
-- BACKFILL: Propagar scout_id desde lead_events a lead_ledger (CATEGORÍA D)
-- ============================================================================
-- OBJETIVO: Para person_keys con scout_id en lead_events pero NO en lead_ledger
-- REGLA: Solo si hay EXACTAMENTE 1 scout_id distinto en eventos
-- EJECUCIÓN: Idempotente (solo actualiza si attributed_scout_id es NULL)
-- ============================================================================

-- ============================================================================
-- PASO 1: Crear tabla de auditoría (si no existe)
-- ============================================================================

CREATE TABLE IF NOT EXISTS ops.lead_ledger_scout_backfill_audit (
    id SERIAL PRIMARY KEY,
    person_key UUID NOT NULL,
    old_attributed_scout_id INTEGER,
    new_attributed_scout_id INTEGER,
    attribution_rule_old TEXT,
    attribution_rule_new TEXT,
    attribution_confidence_old TEXT,
    attribution_confidence_new TEXT,
    attribution_source TEXT,
    evidence_json_old JSONB,
    evidence_json_new JSONB,
    backfill_method TEXT NOT NULL,
    backfill_timestamp TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    notes TEXT
);

CREATE INDEX IF NOT EXISTS idx_lead_ledger_scout_backfill_audit_person_key 
    ON ops.lead_ledger_scout_backfill_audit(person_key);
CREATE INDEX IF NOT EXISTS idx_lead_ledger_scout_backfill_audit_timestamp 
    ON ops.lead_ledger_scout_backfill_audit(backfill_timestamp);

COMMENT ON TABLE ops.lead_ledger_scout_backfill_audit IS 
'Tabla de auditoría append-only para backfills de attributed_scout_id en lead_ledger.';

-- ============================================================================
-- PASO 2: Identificar person_keys candidatos (con exactamente 1 scout_id)
-- ============================================================================

CREATE OR REPLACE TEMP VIEW v_candidates_single_scout AS
SELECT 
    le.person_key,
    COUNT(DISTINCT COALESCE(le.scout_id, (le.payload_json->>'scout_id')::INTEGER)) AS distinct_scout_count,
    MAX(COALESCE(le.scout_id, (le.payload_json->>'scout_id')::INTEGER)) AS scout_id,
    MIN(le.event_date) AS first_event_date,
    MAX(le.event_date) AS last_event_date,
    array_agg(DISTINCT le.source_table) AS source_tables,
    NULL::TEXT[] AS origin_tags,
    COUNT(*) AS total_events
FROM observational.lead_events le
WHERE le.person_key IS NOT NULL
    AND (
        le.scout_id IS NOT NULL 
        OR (le.payload_json IS NOT NULL AND le.payload_json->>'scout_id' IS NOT NULL)
    )
    -- Excluir si ya tiene scout satisfactorio en lead_ledger
    AND NOT EXISTS (
        SELECT 1 FROM observational.lead_ledger ll
        WHERE ll.person_key = le.person_key
            AND ll.attributed_scout_id IS NOT NULL
    )
GROUP BY le.person_key
HAVING COUNT(DISTINCT COALESCE(le.scout_id, (le.payload_json->>'scout_id')::INTEGER)) = 1;

-- ============================================================================
-- PASO 3: Verificar que lead_ledger existe para estos person_keys
-- ============================================================================

CREATE OR REPLACE TEMP VIEW v_candidates_with_ledger AS
SELECT 
    c.person_key,
    c.scout_id,
    c.first_event_date,
    c.last_event_date,
    c.source_tables,
    c.origin_tags,
    c.total_events,
    ll.attributed_scout_id AS current_attributed_scout_id,
    ll.attribution_rule AS current_attribution_rule,
    ll.confidence_level AS current_attribution_confidence,
    ll.evidence_json AS current_evidence_json
FROM v_candidates_single_scout c
INNER JOIN observational.lead_ledger ll ON ll.person_key = c.person_key
WHERE ll.attributed_scout_id IS NULL;  -- Solo los que NO tienen scout atribuido

-- ============================================================================
-- PASO 4: Actualizar lead_ledger con attributed_scout_id
-- ============================================================================

DO $$
DECLARE
    updated_count INTEGER := 0;
    audit_count INTEGER := 0;
    rec RECORD;
    new_evidence_json JSONB;
BEGIN
    FOR rec IN 
        SELECT * FROM v_candidates_with_ledger
    LOOP
        -- Construir evidence_json
        new_evidence_json := COALESCE(rec.current_evidence_json, '{}'::JSONB) || jsonb_build_object(
            'backfill_method', 'BACKFILL_SINGLE_SCOUT_FROM_EVENTS',
            'backfill_timestamp', NOW(),
            'attribution_source', 'lead_events',
            'source_tables', rec.source_tables,
            'origin_tags', rec.origin_tags,
            'total_events', rec.total_events,
            'first_event_date', rec.first_event_date,
            'last_event_date', rec.last_event_date
        );
        
        -- Actualizar lead_ledger
        UPDATE observational.lead_ledger
        SET 
            attributed_scout_id = rec.scout_id,
            attribution_rule = COALESCE(attribution_rule, 'BACKFILL_SINGLE_SCOUT_FROM_EVENTS'),
            confidence_level = CASE 
                WHEN confidence_level::TEXT = 'high' THEN confidence_level
                ELSE 'high'::attributionconfidence
            END,
            evidence_json = new_evidence_json,
            updated_at = NOW()
        WHERE person_key = rec.person_key
            AND attributed_scout_id IS NULL;  -- Solo si aún no tiene scout
        
        IF FOUND THEN
            updated_count := updated_count + 1;
            
            -- Registrar en auditoría
            INSERT INTO ops.lead_ledger_scout_backfill_audit (
                person_key,
                old_attributed_scout_id,
                new_attributed_scout_id,
                attribution_rule_old,
                attribution_rule_new,
                attribution_confidence_old,
                attribution_confidence_new,
                attribution_source,
                evidence_json_old,
                evidence_json_new,
                backfill_method,
                notes
            )
            VALUES (
                rec.person_key,
                rec.current_attributed_scout_id,
                rec.scout_id,
                rec.current_attribution_rule,
                'BACKFILL_SINGLE_SCOUT_FROM_EVENTS',
                rec.current_attribution_confidence::TEXT,
                'high',
                'lead_events',
                rec.current_evidence_json,
                new_evidence_json,
                'BACKFILL_SINGLE_SCOUT_FROM_EVENTS',
                format('Backfill desde lead_events: %s eventos, scout_id=%s', rec.total_events, rec.scout_id)
            );
            
            audit_count := audit_count + 1;
        END IF;
    END LOOP;
    
    RAISE NOTICE 'Actualizados % registros en lead_ledger', updated_count;
    RAISE NOTICE 'Registrados % registros en auditoría', audit_count;
END $$;

-- ============================================================================
-- PASO 5: Identificar casos con múltiples scouts (conflictos)
-- ============================================================================

CREATE OR REPLACE TEMP VIEW v_conflicts_multiple_scouts AS
SELECT 
    le.person_key,
    COUNT(DISTINCT COALESCE(le.scout_id, (le.payload_json->>'scout_id')::INTEGER)) AS distinct_scout_count,
    array_agg(DISTINCT COALESCE(le.scout_id, (le.payload_json->>'scout_id')::INTEGER)) AS scout_ids,
    array_agg(DISTINCT le.source_table) AS source_tables,
    MIN(le.event_date) AS first_event_date,
    MAX(le.event_date) AS last_event_date,
    COUNT(*) AS total_events
FROM observational.lead_events le
WHERE le.person_key IS NOT NULL
    AND (
        le.scout_id IS NOT NULL 
        OR (le.payload_json IS NOT NULL AND le.payload_json->>'scout_id' IS NOT NULL)
    )
    AND NOT EXISTS (
        SELECT 1 FROM observational.lead_ledger ll
        WHERE ll.person_key = le.person_key
            AND ll.attributed_scout_id IS NOT NULL
    )
GROUP BY le.person_key
HAVING COUNT(DISTINCT COALESCE(le.scout_id, (le.payload_json->>'scout_id')::INTEGER)) > 1;

-- ============================================================================
-- RESUMEN FINAL
-- ============================================================================

SELECT 
    'RESUMEN BACKFILL LEAD_LEDGER ATTRIBUTED_SCOUT' AS summary,
    (SELECT COUNT(*) FROM v_candidates_with_ledger) AS candidatos_con_scout_unico,
    (SELECT COUNT(*) FROM v_conflicts_multiple_scouts) AS conflictos_multiple_scout,
    (SELECT COUNT(*) FROM ops.lead_ledger_scout_backfill_audit 
     WHERE backfill_method = 'BACKFILL_SINGLE_SCOUT_FROM_EVENTS'
       AND backfill_timestamp >= NOW() - INTERVAL '1 minute') AS registros_actualizados_hoy;

-- Muestra de conflictos
SELECT 
    'CONFLICTOS (requieren revisión manual)' AS tipo,
    person_key,
    distinct_scout_count,
    scout_ids,
    source_tables,
    first_event_date,
    last_event_date,
    total_events
FROM v_conflicts_multiple_scouts
ORDER BY distinct_scout_count DESC, total_events DESC
LIMIT 20;
