-- ============================================================================
-- BACKFILL: Propagar scout_id desde lead_events a lead_ledger
-- ============================================================================
-- OBJETIVO: Para person_keys que tienen scout_id en lead_events pero NO en lead_ledger
-- (Categoría D: 174 personas)
--
-- REGLA SEGURA:
-- - Si existe exactamente 1 scout_id distinto en eventos → setear attributed_scout_id
-- - Si hay >1 scout_id → NO tocar (mandar a conflicts)
--
-- IDEMPOTENTE: Solo actualiza si attributed_scout_id es NULL
-- ============================================================================

-- ============================================================================
-- PASO 1: Crear tabla de auditoría (si no existe)
-- ============================================================================

CREATE TABLE IF NOT EXISTS ops.lead_ledger_backfill_audit (
    id SERIAL PRIMARY KEY,
    person_key UUID NOT NULL,
    old_attributed_scout_id INTEGER,
    new_attributed_scout_id INTEGER,
    attribution_rule_old TEXT,
    attribution_rule_new TEXT,
    confidence_level_old TEXT,
    confidence_level_new TEXT,
    evidence_json_old JSONB,
    evidence_json_new JSONB,
    backfill_method TEXT NOT NULL,
    backfill_timestamp TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    notes TEXT
);

CREATE INDEX IF NOT EXISTS idx_lead_ledger_backfill_audit_person_key 
    ON ops.lead_ledger_backfill_audit(person_key);
CREATE INDEX IF NOT EXISTS idx_lead_ledger_backfill_audit_timestamp 
    ON ops.lead_ledger_backfill_audit(backfill_timestamp);

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
    c.total_events,
    ll.attributed_scout_id AS current_attributed_scout_id,
    ll.attribution_rule AS current_attribution_rule,
    ll.confidence_level AS current_confidence_level,
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
BEGIN
    FOR rec IN 
        SELECT * FROM v_candidates_with_ledger
    LOOP
        -- Actualizar lead_ledger
        UPDATE observational.lead_ledger
        SET 
            attributed_scout_id = rec.scout_id,
            attribution_rule = COALESCE(attribution_rule, 'BACKFILL_SINGLE_SCOUT_FROM_EVENTS'),
            confidence_level = CASE 
                WHEN confidence_level::TEXT = 'high' THEN confidence_level
                ELSE 'high'::attributionconfidence
            END,
            evidence_json = COALESCE(
                evidence_json,
                jsonb_build_object(
                    'backfill_method', 'BACKFILL_SINGLE_SCOUT_FROM_EVENTS',
                    'backfill_timestamp', NOW(),
                    'source_tables', rec.source_tables,
                    'total_events', rec.total_events,
                    'first_event_date', rec.first_event_date,
                    'last_event_date', rec.last_event_date
                )
            ) || jsonb_build_object(
                'backfill_applied', true,
                'backfill_timestamp', NOW()
            ),
            updated_at = NOW()
        WHERE person_key = rec.person_key
            AND attributed_scout_id IS NULL;  -- Solo si aún no tiene scout
        
        IF FOUND THEN
            updated_count := updated_count + 1;
            
            -- Registrar en auditoría
            INSERT INTO ops.lead_ledger_backfill_audit (
                person_key,
                old_attributed_scout_id,
                new_attributed_scout_id,
                attribution_rule_old,
                attribution_rule_new,
                confidence_level_old,
                confidence_level_new,
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
                rec.current_confidence_level::TEXT,
                'high',
                rec.current_evidence_json,
                (SELECT evidence_json FROM observational.lead_ledger WHERE person_key = rec.person_key),
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
    'RESUMEN BACKFILL LEAD_LEDGER' AS summary,
    (SELECT COUNT(*) FROM v_candidates_with_ledger) AS candidatos_con_scout_unico,
    (SELECT COUNT(*) FROM v_conflicts_multiple_scouts) AS conflictos_multiple_scout,
    (SELECT COUNT(*) FROM ops.lead_ledger_backfill_audit 
     WHERE backfill_method = 'BACKFILL_SINGLE_SCOUT_FROM_EVENTS'
       AND backfill_timestamp >= NOW() - INTERVAL '1 minute') AS registros_actualizados;

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

