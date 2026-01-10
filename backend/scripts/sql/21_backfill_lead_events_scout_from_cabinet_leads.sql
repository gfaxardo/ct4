-- ============================================================================
-- BACKFILL: Scout_id en lead_events desde cabinet_leads (si mapping 1:1)
-- ============================================================================
-- Objetivo: Para eventos originados en cabinet_leads sin scout_id,
-- inferir desde referral_link_id si hay mapping 1:1 con scouts_list
-- Ejecución: Solo si se puede inferir 1:1 (verificar primero)
-- ============================================================================

-- ============================================================================
-- PASO 1: Verificar si existe mapping 1:1 referral_link_id -> scout_id
-- ============================================================================

-- Verificar si module_ct_cabinet_leads tiene referral_link_id
DO $$
DECLARE
    has_referral_link BOOLEAN;
    has_scouts_list BOOLEAN;
    can_infer BOOLEAN := false;
    mapping_count BIGINT;
    distinct_referral_links BIGINT;
    distinct_scouts BIGINT;
BEGIN
    -- Verificar si cabinet_leads tiene referral_link_id
    SELECT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_schema = 'public' 
            AND table_name = 'module_ct_cabinet_leads'
            AND column_name ILIKE '%referral%link%'
    ) INTO has_referral_link;
    
    -- Verificar si existe scouts_list
    SELECT EXISTS (
        SELECT 1 FROM information_schema.tables 
        WHERE table_schema = 'public' 
            AND table_name IN ('module_ct_scouts_list', 'scouts_list')
    ) INTO has_scouts_list;
    
    IF has_referral_link AND has_scouts_list THEN
        -- Verificar mapping 1:1
        -- (Ejemplo genérico - ajustar según schema real)
        -- SELECT COUNT(*) INTO mapping_count FROM ...
        -- Si mapping_count = distinct_referral_links = distinct_scouts, entonces es 1:1
        RAISE NOTICE 'WARN: Verificar manualmente mapping referral_link_id -> scout_id';
        RAISE NOTICE 'Si mapping es 1:1, ejecutar backfill. Si no, crear vista de alertas.';
    ELSE
        RAISE NOTICE 'INFO: No se puede inferir scout desde cabinet_leads. Crear vista de alertas.';
    END IF;
END $$;

-- ============================================================================
-- PASO 2: Crear tabla de auditoría (si no existe)
-- ============================================================================

CREATE TABLE IF NOT EXISTS ops.lead_events_scout_backfill_audit (
    id SERIAL PRIMARY KEY,
    lead_event_id INTEGER NOT NULL,
    person_key UUID,
    old_scout_id INTEGER,
    new_scout_id INTEGER,
    source_table TEXT,
    source_pk TEXT,
    backfill_method TEXT NOT NULL,
    backfill_timestamp TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    notes TEXT
);

CREATE INDEX IF NOT EXISTS idx_lead_events_scout_backfill_audit_event_id 
    ON ops.lead_events_scout_backfill_audit(lead_event_id);
CREATE INDEX IF NOT EXISTS idx_lead_events_scout_backfill_audit_timestamp 
    ON ops.lead_events_scout_backfill_audit(backfill_timestamp);

COMMENT ON TABLE ops.lead_events_scout_backfill_audit IS 
'Tabla de auditoría append-only para backfills de scout_id en lead_events desde cabinet_leads.';

-- ============================================================================
-- PASO 3: Crear vista de alertas si NO se puede inferir 1:1
-- ============================================================================

DROP VIEW IF EXISTS ops.v_cabinet_leads_missing_scout_alerts CASCADE;
CREATE VIEW ops.v_cabinet_leads_missing_scout_alerts AS
SELECT 
    DATE(le.event_date) AS event_date,
    le.source_table,
    COUNT(*) AS events_without_scout,
    COUNT(DISTINCT le.person_key) AS distinct_persons,
    COUNT(DISTINCT le.source_pk) AS distinct_source_pks,
    array_agg(DISTINCT le.source_pk) FILTER (WHERE le.source_pk IS NOT NULL) AS sample_source_pks
FROM observational.lead_events le
WHERE le.source_table = 'module_ct_cabinet_leads'
    AND le.scout_id IS NULL
    AND (le.payload_json IS NULL OR le.payload_json->>'scout_id' IS NULL)
    AND le.person_key IS NOT NULL
GROUP BY DATE(le.event_date), le.source_table
ORDER BY event_date DESC;

COMMENT ON VIEW ops.v_cabinet_leads_missing_scout_alerts IS 
'Vista de alertas: eventos de cabinet_leads sin scout_id agrupados por día. Para revisión manual.';

-- ============================================================================
-- NOTA: El backfill real se implementaría aquí si se verifica mapping 1:1
-- Por ahora, dejar la vista de alertas
-- ============================================================================

SELECT 
    'INFO: Backfill desde cabinet_leads requiere verificación manual de mapping 1:1' AS status,
    'Ver ops.v_cabinet_leads_missing_scout_alerts para eventos sin scout' AS action;

