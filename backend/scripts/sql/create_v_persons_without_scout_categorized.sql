-- ============================================================================
-- VISTA: ops.v_persons_without_scout_categorized
-- ============================================================================
-- Propósito: Clasificar personas sin scout canónico en categorías A, C, D
-- Categorías:
--   A - Eventos sin scout (lead_events sin scout_id)
--   C - Legacy (no clasificado aún)
--   D - Scout en eventos no propagado a lead_ledger
-- Ejecución: Idempotente (DROP + CREATE)
-- ============================================================================

DROP VIEW IF EXISTS ops.v_persons_without_scout_categorized CASCADE;

CREATE VIEW ops.v_persons_without_scout_categorized AS

-- CATEGORÍA A: Eventos sin scout
SELECT DISTINCT
    ir.person_key,
    'A' AS category,
    'EVENTOS_SIN_SCOUT' AS category_label,
    NULL::INTEGER AS scout_id,
    array_agg(DISTINCT le.source_table) AS source_tables,
    NULL::TEXT[] AS origin_tags,
    MIN(le.event_date) AS first_event_date,
    MAX(le.event_date) AS last_event_date,
    COUNT(DISTINCT le.id) AS event_count
FROM canon.identity_registry ir
INNER JOIN observational.lead_events le ON le.person_key = ir.person_key
WHERE NOT EXISTS (
    SELECT 1 FROM ops.v_scout_attribution sa
    WHERE sa.person_key = ir.person_key
)
AND (
    le.scout_id IS NULL 
    AND (le.payload_json IS NULL OR le.payload_json->>'scout_id' IS NULL)
)
GROUP BY ir.person_key

UNION ALL

-- CATEGORÍA C: Legacy (no clasificado aún - sin eventos y sin scout)
SELECT DISTINCT
    ir.person_key,
    'C' AS category,
    'LEGACY' AS category_label,
    NULL::INTEGER AS scout_id,
    array_agg(DISTINCT il.source_table) AS source_tables,
    NULL::TEXT[] AS origin_tags,
    MIN(il.snapshot_date::DATE) AS first_event_date,
    MAX(il.snapshot_date::DATE) AS last_event_date,
    COUNT(DISTINCT il.id) AS event_count
FROM canon.identity_registry ir
INNER JOIN canon.identity_links il ON il.person_key = ir.person_key
WHERE NOT EXISTS (
    SELECT 1 FROM ops.v_scout_attribution sa
    WHERE sa.person_key = ir.person_key
)
AND NOT EXISTS (
    SELECT 1 FROM observational.lead_events le
    WHERE le.person_key = ir.person_key
)
GROUP BY ir.person_key

UNION ALL

-- CATEGORÍA D: Scout en eventos no propagado a lead_ledger
SELECT DISTINCT
    ir.person_key,
    'D' AS category,
    'SCOUT_EN_EVENTOS_NO_PROPAGADO' AS category_label,
    MAX(COALESCE(le.scout_id, (le.payload_json->>'scout_id')::INTEGER)) AS scout_id,
    array_agg(DISTINCT le.source_table) AS source_tables,
    NULL::TEXT[] AS origin_tags,
    MIN(le.event_date) AS first_event_date,
    MAX(le.event_date) AS last_event_date,
    COUNT(DISTINCT le.id) AS event_count
FROM canon.identity_registry ir
INNER JOIN observational.lead_events le ON le.person_key = ir.person_key
WHERE NOT EXISTS (
    SELECT 1 FROM ops.v_scout_attribution sa
    WHERE sa.person_key = ir.person_key
)
AND (
    le.scout_id IS NOT NULL 
    OR (le.payload_json IS NOT NULL AND le.payload_json->>'scout_id' IS NOT NULL)
)
-- Verificar que NO está en lead_ledger con scout
AND NOT EXISTS (
    SELECT 1 FROM observational.lead_ledger ll
    WHERE ll.person_key = ir.person_key
        AND ll.attributed_scout_id IS NOT NULL
)
GROUP BY ir.person_key;

COMMENT ON VIEW ops.v_persons_without_scout_categorized IS 
'Personas sin scout canónico clasificadas: A=eventos sin scout, C=legacy, D=scout en eventos no propagado.';
