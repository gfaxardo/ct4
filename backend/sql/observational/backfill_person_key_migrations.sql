-- ============================================================================
-- Backfill de person_key para lead_events de module_ct_migrations
-- ============================================================================
-- Objetivo: Resolver person_key usando driver_id desde payload_json
-- y matching con canon.identity_links para desbloquear fleet_migration
-- ============================================================================

BEGIN;

WITH src AS (
  SELECT
    le.id AS lead_event_id,
    (le.payload_json->>'driver_id')::text AS driver_id
  FROM observational.lead_events le
  WHERE le.source_table='module_ct_migrations'
    AND le.person_key IS NULL
    AND (le.payload_json->>'driver_id') IS NOT NULL
    AND (le.payload_json->>'driver_id') <> ''
),
matched AS (
  SELECT
    s.lead_event_id,
    il.person_key
  FROM src s
  JOIN canon.identity_links il
    ON il.source_table = 'drivers'
    AND il.source_pk::text = s.driver_id
)
UPDATE observational.lead_events le
SET person_key = m.person_key
FROM matched m
WHERE le.id = m.lead_event_id;

-- Reporte post update
SELECT
  COUNT(*) AS remaining_null_person_key
FROM observational.lead_events
WHERE source_table='module_ct_migrations'
  AND person_key IS NULL;

COMMIT;

