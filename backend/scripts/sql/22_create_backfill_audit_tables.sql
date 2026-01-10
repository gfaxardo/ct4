-- ============================================================================
-- CREAR TABLAS DE AUDITORÍA PARA BACKFILLS
-- ============================================================================
-- Objetivo: Crear todas las tablas de auditoría necesarias (append-only)
-- Ejecución: Idempotente (CREATE TABLE IF NOT EXISTS)
-- ============================================================================

-- ============================================================================
-- TABLA 1: identity_links_backfill_audit
-- ============================================================================

CREATE TABLE IF NOT EXISTS ops.identity_links_backfill_audit (
    id SERIAL PRIMARY KEY,
    source_table TEXT NOT NULL,
    source_pk TEXT NOT NULL,
    person_key UUID,
    match_method TEXT,
    match_confidence TEXT,
    driver_id TEXT,
    driver_license TEXT,
    driver_phone TEXT,
    match_result TEXT NOT NULL, -- 'created', 'skipped_exists', 'ambiguous', 'not_found'
    reason TEXT,
    backfill_timestamp TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_identity_links_backfill_audit_source 
    ON ops.identity_links_backfill_audit(source_table, source_pk);
CREATE INDEX IF NOT EXISTS idx_identity_links_backfill_audit_timestamp 
    ON ops.identity_links_backfill_audit(backfill_timestamp);
CREATE INDEX IF NOT EXISTS idx_identity_links_backfill_audit_match_result 
    ON ops.identity_links_backfill_audit(match_result);

COMMENT ON TABLE ops.identity_links_backfill_audit IS 
'Tabla de auditoría append-only para backfills de identity_links desde scouting_daily.';

-- ============================================================================
-- TABLA 2: lead_ledger_scout_backfill_audit (ya creada en 20_backfill_lead_ledger_attributed_scout.sql)
-- ============================================================================

-- Verificar si existe, si no crear
CREATE TABLE IF NOT EXISTS ops.lead_ledger_scout_backfill_audit (
    id SERIAL PRIMARY KEY,
    person_key UUID NOT NULL,
    old_attributed_scout_id INTEGER,
    new_attributed_scout_id INTEGER,
    attribution_rule_old TEXT,
    attribution_rule_new TEXT,
    attribution_confidence_old TEXT,
    attribution_confidence_new TEXT,
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
-- TABLA 3: lead_events_scout_backfill_audit (ya creada en 21_backfill_lead_events_scout_from_cabinet_leads.sql)
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
-- RESUMEN DE TABLAS CREADAS
-- ============================================================================

SELECT 
    schemaname,
    tablename,
    'OK' AS status
FROM pg_tables
WHERE schemaname = 'ops'
    AND tablename IN (
        'identity_links_backfill_audit',
        'lead_ledger_scout_backfill_audit',
        'lead_events_scout_backfill_audit'
    )
ORDER BY tablename;

