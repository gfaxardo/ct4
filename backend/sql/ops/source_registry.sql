-- ============================================================================
-- Tabla: ops.source_registry
-- ============================================================================
-- Registry canónico de fuentes de datos con metadatos y overrides manuales.
-- Poblada automáticamente por populate_source_registry.py pero permite
-- overrides manuales en columnas: is_expected, is_critical, health_enabled, notes.
-- ============================================================================

CREATE TABLE IF NOT EXISTS ops.source_registry (
    id bigserial PRIMARY KEY,
    schema_name text NOT NULL,
    object_name text NOT NULL,
    object_type text NOT NULL, -- 'table', 'view', 'matview'
    layer text, -- 'RAW', 'DERIVED', 'MV', 'CANON'
    role text, -- 'PRIMARY', 'SECONDARY'
    criticality text, -- 'critical', 'important', 'normal'
    should_monitor boolean,
    is_expected boolean, -- override manual (NO se pisa si tiene valor)
    is_critical boolean, -- override manual (NO se pisa si tiene valor)
    health_enabled boolean, -- override manual (NO se pisa si tiene valor)
    description text,
    usage_context text, -- 'endpoint', 'script', 'both', null
    refresh_schedule text, -- para MVs
    depends_on jsonb, -- array de {schema, name}
    discovered_at timestamptz,
    last_verified_at timestamptz,
    notes text, -- override manual (NO se pisa si tiene valor)
    created_at timestamptz DEFAULT now(),
    updated_at timestamptz DEFAULT now(),
    UNIQUE(schema_name, object_name)
);

CREATE INDEX IF NOT EXISTS idx_source_registry_schema_object 
    ON ops.source_registry(schema_name, object_name);
CREATE INDEX IF NOT EXISTS idx_source_registry_layer 
    ON ops.source_registry(layer);
CREATE INDEX IF NOT EXISTS idx_source_registry_criticality 
    ON ops.source_registry(criticality);
CREATE INDEX IF NOT EXISTS idx_source_registry_should_monitor 
    ON ops.source_registry(should_monitor);

COMMENT ON TABLE ops.source_registry IS 
'Registry canónico de fuentes de datos. Poblado automáticamente pero permite overrides manuales.';

COMMENT ON COLUMN ops.source_registry.schema_name IS 
'Schema donde reside el objeto (public, ops, canon, raw, observational).';

COMMENT ON COLUMN ops.source_registry.object_name IS 
'Nombre del objeto (tabla, vista, materialized view).';

COMMENT ON COLUMN ops.source_registry.object_type IS 
'Tipo de objeto: table, view, matview.';

COMMENT ON COLUMN ops.source_registry.layer IS 
'Capa del objeto: RAW (schema raw), CANON (schema canon), MV (matview), DERIVED (default).';

COMMENT ON COLUMN ops.source_registry.role IS 
'Rol: PRIMARY (RAW/CANON), SECONDARY (MV/DERIVED).';

COMMENT ON COLUMN ops.source_registry.criticality IS 
'Criticidad: critical (MV en refresh_ops_mvs.py o usado por endpoint), important (usado por endpoint), normal.';

COMMENT ON COLUMN ops.source_registry.should_monitor IS 
'Si debe monitorearse en health checks (derivado de criticality y health_enabled).';

COMMENT ON COLUMN ops.source_registry.is_expected IS 
'Override manual: si se espera que este objeto exista. NO se pisa si tiene valor.';

COMMENT ON COLUMN ops.source_registry.is_critical IS 
'Override manual: si este objeto es crítico. NO se pisa si tiene valor.';

COMMENT ON COLUMN ops.source_registry.health_enabled IS 
'Override manual: si health checks están habilitados para este objeto. NO se pisa si tiene valor.';

COMMENT ON COLUMN ops.source_registry.usage_context IS 
'Contexto de uso: endpoint, script, both, null.';

COMMENT ON COLUMN ops.source_registry.depends_on IS 
'Dependencias: array JSONB de {schema, name}.';

COMMENT ON COLUMN ops.source_registry.discovered_at IS 
'Primera vez que se descubrió este objeto (solo se setea si es NULL).';

COMMENT ON COLUMN ops.source_registry.last_verified_at IS 
'Última vez que se verificó este objeto (siempre se actualiza).';

COMMENT ON COLUMN ops.source_registry.notes IS 
'Notas manuales. NO se pisa si tiene valor.';




