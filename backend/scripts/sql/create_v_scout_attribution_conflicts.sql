-- ============================================================================
-- VISTA: ops.v_scout_attribution_conflicts
-- ============================================================================
-- Propósito: Identificar person_keys con >1 scout_id distinto
-- Ejecución: Idempotente (DROP + CREATE)
-- ============================================================================

DROP VIEW IF EXISTS ops.v_scout_attribution_conflicts CASCADE;

CREATE VIEW ops.v_scout_attribution_conflicts AS
SELECT 
    person_key,
    COUNT(DISTINCT scout_id) AS distinct_scout_count,
    array_agg(DISTINCT scout_id ORDER BY scout_id) AS scout_ids,
    array_agg(DISTINCT source_table ORDER BY source_table) AS sources,
    array_agg(DISTINCT origin_tag) FILTER (WHERE origin_tag IS NOT NULL) AS origin_tags,
    MIN(attribution_date) AS first_event_date,
    MAX(attribution_date) AS last_event_date,
    COUNT(*) AS total_sources
FROM ops.v_scout_attribution_raw
WHERE scout_id IS NOT NULL
GROUP BY person_key
HAVING COUNT(DISTINCT scout_id) > 1;

COMMENT ON VIEW ops.v_scout_attribution_conflicts IS 
'Person_keys con múltiples scout_id distintos. Requieren revisión manual.';
