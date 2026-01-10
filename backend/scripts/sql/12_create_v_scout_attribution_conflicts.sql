-- ============================================================================
-- VISTA: ops.v_scout_attribution_conflicts
-- ============================================================================
-- Propósito: Identificar person_key con >1 scout_id distinto
-- Ejecución: Idempotente (DROP + CREATE)
-- ============================================================================

DROP VIEW IF EXISTS ops.v_scout_attribution_conflicts CASCADE;
CREATE VIEW ops.v_scout_attribution_conflicts AS
WITH conflicts_raw AS (
    SELECT 
        person_key,
        scout_id,
        source_table,
        source_pk,
        attribution_date,
        created_at,
        priority
    FROM ops.v_scout_attribution_raw
    WHERE person_key IS NOT NULL
)
SELECT 
    person_key,
    COUNT(DISTINCT scout_id) AS distinct_scout_count,
    array_agg(DISTINCT scout_id ORDER BY scout_id) AS scout_ids,
    array_agg(DISTINCT source_table) AS source_tables,
    NULL::TEXT[] AS origin_tags,
    MIN(attribution_date) AS first_attribution_date,
    MAX(attribution_date) AS last_attribution_date,
    MIN(created_at) AS first_created_at,
    MAX(created_at) AS last_created_at,
    COUNT(*) AS total_records,
    -- Agregar detalles de cada scout
    jsonb_agg(
        jsonb_build_object(
            'scout_id', scout_id,
            'source_table', source_table,
            'source_pk', source_pk,
            'attribution_date', attribution_date,
            'created_at', created_at,
            'priority', priority
        ) ORDER BY priority ASC, attribution_date DESC
    ) AS conflict_details
FROM conflicts_raw
GROUP BY person_key
HAVING COUNT(DISTINCT scout_id) > 1;

COMMENT ON VIEW ops.v_scout_attribution_conflicts IS 
'Vista de conflictos: person_key con múltiples scout_ids distintos. Muestra todos los scouts y fuentes para revisión manual.';

COMMENT ON COLUMN ops.v_scout_attribution_conflicts.conflict_details IS 
'JSONB array con detalles de cada scout_id conflictivo: scout_id, source_table, source_pk, origin_tag, attribution_date, created_at, priority.';

-- ============================================================================
-- RESUMEN DE CONFLICTOS
-- ============================================================================

SELECT 
    'RESUMEN CONFLICTOS' AS section,
    COUNT(*) AS total_conflicts,
    (SELECT COUNT(DISTINCT unnest_scout_id) FROM ops.v_scout_attribution_conflicts, unnest(scout_ids) AS unnest_scout_id) AS distinct_scouts_in_conflicts,
    SUM(total_records) AS total_conflict_records
FROM ops.v_scout_attribution_conflicts;

-- ============================================================================
-- TOP 50 CONFLICTOS (para revisión manual)
-- ============================================================================

SELECT 
    person_key,
    distinct_scout_count,
    scout_ids,
    source_tables,
    origin_tags,
    first_attribution_date,
    last_attribution_date,
    total_records
FROM ops.v_scout_attribution_conflicts
ORDER BY distinct_scout_count DESC, total_records DESC
LIMIT 50;

