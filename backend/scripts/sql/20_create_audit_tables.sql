-- ============================================================================
-- TABLAS DE AUDITORÍA: Scout Attribution
-- ============================================================================
-- Propósito: Tablas append-only para auditar todos los backfills y jobs
-- Ejecución: Idempotente (CREATE IF NOT EXISTS)
-- ============================================================================

-- ============================================================================
-- 1. AUDITORÍA: Identity Links Backfill (scouting_daily)
-- ============================================================================

-- Crear tabla si no existe, o agregar columnas faltantes si ya existe
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.tables 
        WHERE table_schema = 'ops' AND table_name = 'identity_links_backfill_audit'
    ) THEN
        CREATE TABLE ops.identity_links_backfill_audit (
            id SERIAL PRIMARY KEY,
            source_table TEXT NOT NULL,
            source_pk TEXT NOT NULL,
            person_key UUID,
            driver_id TEXT,
            match_method TEXT NOT NULL,
            match_confidence TEXT NOT NULL,
            match_score INTEGER,
            evidence_json JSONB,
            action_type TEXT NOT NULL,  -- 'CREATED', 'SKIPPED', 'AMBIGUOUS', 'ERROR'
            error_message TEXT,
            backfill_timestamp TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
            ingestion_run_id INTEGER,  -- FK a ops.ingestion_runs.id
            notes TEXT
        );
    ELSE
        -- Agregar columnas faltantes si la tabla ya existe
        IF NOT EXISTS (
            SELECT 1 FROM information_schema.columns 
            WHERE table_schema = 'ops' AND table_name = 'identity_links_backfill_audit' 
            AND column_name = 'ingestion_run_id'
        ) THEN
            ALTER TABLE ops.identity_links_backfill_audit 
            ADD COLUMN ingestion_run_id INTEGER;
        END IF;
        IF NOT EXISTS (
            SELECT 1 FROM information_schema.columns 
            WHERE table_schema = 'ops' AND table_name = 'identity_links_backfill_audit' 
            AND column_name = 'notes'
        ) THEN
            ALTER TABLE ops.identity_links_backfill_audit 
            ADD COLUMN notes TEXT;
        END IF;
    END IF;
END $$;

CREATE INDEX IF NOT EXISTS idx_identity_links_backfill_audit_source 
    ON ops.identity_links_backfill_audit(source_table, source_pk);
CREATE INDEX IF NOT EXISTS idx_identity_links_backfill_audit_person_key 
    ON ops.identity_links_backfill_audit(person_key);
CREATE INDEX IF NOT EXISTS idx_identity_links_backfill_audit_timestamp 
    ON ops.identity_links_backfill_audit(backfill_timestamp);
CREATE INDEX IF NOT EXISTS idx_identity_links_backfill_audit_run_id 
    ON ops.identity_links_backfill_audit(ingestion_run_id);

COMMENT ON TABLE ops.identity_links_backfill_audit IS 
'Auditoría append-only para backfills de identity_links (ej: scouting_daily). Cada intento queda registrado.';

-- ============================================================================
-- 2. AUDITORÍA: Lead Ledger Scout Backfill (ya existe, verificar)
-- ============================================================================

-- Crear tabla si no existe, o agregar columnas faltantes si ya existe
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.tables 
        WHERE table_schema = 'ops' AND table_name = 'lead_ledger_scout_backfill_audit'
    ) THEN
        CREATE TABLE ops.lead_ledger_scout_backfill_audit (
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
            ingestion_run_id INTEGER,  -- FK a ops.ingestion_runs.id
            notes TEXT
        );
    ELSE
        IF NOT EXISTS (
            SELECT 1 FROM information_schema.columns 
            WHERE table_schema = 'ops' AND table_name = 'lead_ledger_scout_backfill_audit' 
            AND column_name = 'ingestion_run_id'
        ) THEN
            ALTER TABLE ops.lead_ledger_scout_backfill_audit 
            ADD COLUMN ingestion_run_id INTEGER;
        END IF;
        IF NOT EXISTS (
            SELECT 1 FROM information_schema.columns 
            WHERE table_schema = 'ops' AND table_name = 'lead_ledger_scout_backfill_audit' 
            AND column_name = 'notes'
        ) THEN
            ALTER TABLE ops.lead_ledger_scout_backfill_audit 
            ADD COLUMN notes TEXT;
        END IF;
    END IF;
END $$;

CREATE INDEX IF NOT EXISTS idx_lead_ledger_scout_backfill_audit_person_key 
    ON ops.lead_ledger_scout_backfill_audit(person_key);
CREATE INDEX IF NOT EXISTS idx_lead_ledger_scout_backfill_audit_timestamp 
    ON ops.lead_ledger_scout_backfill_audit(backfill_timestamp);
CREATE INDEX IF NOT EXISTS idx_lead_ledger_scout_backfill_audit_run_id 
    ON ops.lead_ledger_scout_backfill_audit(ingestion_run_id);

COMMENT ON TABLE ops.lead_ledger_scout_backfill_audit IS 
'Auditoría append-only para backfills de attributed_scout_id en lead_ledger.';

-- ============================================================================
-- 3. AUDITORÍA: Lead Events Scout Backfill (desde cabinet_leads)
-- ============================================================================

-- Crear tabla si no existe, o agregar columnas faltantes si ya existe
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.tables 
        WHERE table_schema = 'ops' AND table_name = 'lead_events_scout_backfill_audit'
    ) THEN
        CREATE TABLE ops.lead_events_scout_backfill_audit (
            id SERIAL PRIMARY KEY,
            source_table TEXT NOT NULL,
            source_pk TEXT NOT NULL,
            person_key UUID,
            old_scout_id INTEGER,
            new_scout_id INTEGER,
            mapping_method TEXT NOT NULL,  -- 'referral_link_id', 'recruiter_id', 'utm', 'payload_json'
            mapping_confidence TEXT NOT NULL,  -- 'high', 'medium', 'low'
            evidence_json JSONB,
            action_type TEXT NOT NULL,  -- 'UPDATED', 'SKIPPED', 'NO_MAPPING', 'ERROR'
            error_message TEXT,
            backfill_timestamp TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
            ingestion_run_id INTEGER,  -- FK a ops.ingestion_runs.id
            notes TEXT
        );
    ELSE
        IF NOT EXISTS (
            SELECT 1 FROM information_schema.columns 
            WHERE table_schema = 'ops' AND table_name = 'lead_events_scout_backfill_audit' 
            AND column_name = 'ingestion_run_id'
        ) THEN
            ALTER TABLE ops.lead_events_scout_backfill_audit 
            ADD COLUMN ingestion_run_id INTEGER;
        END IF;
        IF NOT EXISTS (
            SELECT 1 FROM information_schema.columns 
            WHERE table_schema = 'ops' AND table_name = 'lead_events_scout_backfill_audit' 
            AND column_name = 'notes'
        ) THEN
            ALTER TABLE ops.lead_events_scout_backfill_audit 
            ADD COLUMN notes TEXT;
        END IF;
    END IF;
END $$;

CREATE INDEX IF NOT EXISTS idx_lead_events_scout_backfill_audit_source 
    ON ops.lead_events_scout_backfill_audit(source_table, source_pk);
CREATE INDEX IF NOT EXISTS idx_lead_events_scout_backfill_audit_person_key 
    ON ops.lead_events_scout_backfill_audit(person_key);
CREATE INDEX IF NOT EXISTS idx_lead_events_scout_backfill_audit_timestamp 
    ON ops.lead_events_scout_backfill_audit(backfill_timestamp);
CREATE INDEX IF NOT EXISTS idx_lead_events_scout_backfill_audit_run_id 
    ON ops.lead_events_scout_backfill_audit(ingestion_run_id);

COMMENT ON TABLE ops.lead_events_scout_backfill_audit IS 
'Auditoría append-only para backfills de scout_id en lead_events desde cabinet_leads.';

-- ============================================================================
-- 4. AUDITORÍA: Job Runs (extender ops.ingestion_runs si existe, o crear nueva)
-- ============================================================================

-- Nota: Si ops.ingestion_runs ya existe con job_type, usaremos esa tabla
-- Si no, crear ops.job_runs_audit como tabla dedicada

DO $$
BEGIN
    -- Verificar si ops.ingestion_runs existe y tiene job_type
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.tables 
        WHERE table_schema = 'ops' AND table_name = 'ingestion_runs'
    ) THEN
        -- Crear tabla de jobs si no existe
        CREATE TABLE IF NOT EXISTS ops.job_runs_audit (
            id SERIAL PRIMARY KEY,
            job_name TEXT NOT NULL,
            job_type TEXT NOT NULL,  -- 'scout_attribution_refresh', 'identity_run', etc.
            started_at TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL,
            ended_at TIMESTAMP WITH TIME ZONE,
            status TEXT NOT NULL,  -- 'RUNNING', 'COMPLETED', 'FAILED'
            summary_json JSONB,
            error_message TEXT,
            scope_date_from DATE,
            scope_date_to DATE,
            incremental BOOLEAN DEFAULT true
        );
        
        CREATE INDEX IF NOT EXISTS idx_job_runs_audit_job_name 
            ON ops.job_runs_audit(job_name, started_at DESC);
        CREATE INDEX IF NOT EXISTS idx_job_runs_audit_status 
            ON ops.job_runs_audit(status);
            
        COMMENT ON TABLE ops.job_runs_audit IS 
        'Auditoría de ejecuciones de jobs recurrentes. Append-only.';
    END IF;
    
    -- Extender job_type enum si es necesario (solo si existe ops.ingestion_runs)
    IF EXISTS (
        SELECT 1 FROM information_schema.tables 
        WHERE table_schema = 'ops' AND table_name = 'ingestion_runs'
    ) THEN
        -- job_type ya está como texto en el modelo Python, así que no necesitamos alterar enum
        -- Solo añadir índice si no existe
        IF NOT EXISTS (
            SELECT 1 FROM pg_indexes 
            WHERE schemaname = 'ops' 
            AND tablename = 'ingestion_runs' 
            AND indexname = 'idx_ingestion_runs_job_type'
        ) THEN
            CREATE INDEX idx_ingestion_runs_job_type 
            ON ops.ingestion_runs(job_type, started_at DESC);
        END IF;
    END IF;
END $$;

