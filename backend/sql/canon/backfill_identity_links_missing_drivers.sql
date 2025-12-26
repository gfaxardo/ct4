-- ============================================================================
-- Backfill de identity_links para driver_id faltantes de module_ct_migrations
-- ============================================================================
-- Objetivo: Crear links faltantes en canon.identity_links para los 95 driver_id
-- que están en public.drivers pero no tienen identity_links(source_table='drivers')
-- ============================================================================

BEGIN;

-- Habilitar extensión UUID si no está habilitada
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- Crear tabla temporal para almacenar los datos
CREATE TEMP TABLE temp_driver_backfill AS
WITH missing_drivers AS (
  SELECT DISTINCT (le.payload_json->>'driver_id')::text AS driver_id
  FROM observational.lead_events le
  WHERE le.source_table = 'module_ct_migrations'
    AND (le.payload_json->>'driver_id') IS NOT NULL
    AND (le.payload_json->>'driver_id') <> ''
    AND NOT EXISTS (
      SELECT 1
      FROM canon.identity_links il
      WHERE il.source_table = 'drivers'
        AND il.source_pk::text = (le.payload_json->>'driver_id')::text
    )
),
existing_person_keys AS (
  SELECT DISTINCT ON (md.driver_id)
    md.driver_id,
    il.person_key
  FROM missing_drivers md
  JOIN canon.identity_links il
    ON il.source_pk::text = md.driver_id
  ORDER BY md.driver_id, il.linked_at DESC
),
drivers_with_person_keys AS (
  SELECT
    md.driver_id,
    COALESCE(epk.person_key, gen_random_uuid()::uuid) AS person_key,
    CASE 
      WHEN epk.person_key IS NOT NULL THEN 'reused_existing'
      ELSE 'new_generated'
    END AS person_key_source
  FROM missing_drivers md
  LEFT JOIN existing_person_keys epk ON epk.driver_id = md.driver_id
)
SELECT * FROM drivers_with_person_keys;

-- Paso 1: Crear registros en identity_registry (solo los que no existen)
INSERT INTO canon.identity_registry (person_key, confidence_level)
SELECT DISTINCT person_key, 'HIGH'::confidencelevel
FROM temp_driver_backfill
WHERE NOT EXISTS (
  SELECT 1 FROM canon.identity_registry ir WHERE ir.person_key = temp_driver_backfill.person_key
);

-- Paso 2: Insertar en identity_links (idempotente)
INSERT INTO canon.identity_links (
    person_key,
    source_table,
    source_pk,
    snapshot_date,
    match_rule,
    match_score,
    confidence_level,
    evidence,
    linked_at,
    run_id
)
SELECT
    tdb.person_key,
    'drivers' AS source_table,
    tdb.driver_id AS source_pk,
    NOW() AS snapshot_date,
    'drivers_backfill' AS match_rule,
    100 AS match_score,
    'HIGH'::confidencelevel AS confidence_level,
    jsonb_build_object(
        'driver_id', tdb.driver_id,
        'reason', 'missing_driver_link_backfill',
        'person_key_source', tdb.person_key_source
    ) AS evidence,
    NOW() AS linked_at,
    NULL AS run_id
FROM temp_driver_backfill tdb
WHERE NOT EXISTS (
    SELECT 1
    FROM canon.identity_links il
    WHERE il.source_table = 'drivers'
        AND il.source_pk::text = tdb.driver_id
);

-- Limpiar tabla temporal
DROP TABLE temp_driver_backfill;

-- Paso 3: Reporte post-inserción
SELECT 'inserted_links' AS metric, COUNT(*) AS value
FROM canon.identity_links
WHERE source_table = 'drivers'
    AND match_rule = 'drivers_backfill'
    AND evidence->>'reason' = 'missing_driver_link_backfill';

SELECT 'total_links_drivers' AS metric, COUNT(*) AS value
FROM canon.identity_links
WHERE source_table = 'drivers';

COMMIT;
