-- Diagnóstico SQL: Matches entre drivers en cuarentena y lead_events
-- ===================================================================
-- Este script diagnostica si hay matches reales entre drivers en cuarentena
-- y eventos en lead_events usando normalización robusta con regexp_replace.

-- ============================================================================
-- MUESTRA 1: Matches por driver_id directo (migrations u otros)
-- ============================================================================
WITH quarantined_sample AS (
    SELECT driver_id, person_key
    FROM canon.driver_orphan_quarantine
    WHERE status = 'quarantined'
    LIMIT 20
),
driver_id_matches AS (
    SELECT 
        q.driver_id,
        q.person_key,
        le.id as event_id,
        le.source_table,
        le.source_pk,
        le.event_date,
        le.payload_json->>'driver_id' as event_driver_id,
        'driver_id_direct' as match_strategy
    FROM quarantined_sample q
    INNER JOIN observational.lead_events le ON (
        le.payload_json->>'driver_id' = q.driver_id
        OR le.payload_json->>'driverId' = q.driver_id
        OR le.payload_json->>'id' = q.driver_id
    )
    WHERE le.payload_json IS NOT NULL
)
SELECT 
    COUNT(DISTINCT driver_id) as drivers_with_driver_id_matches,
    COUNT(*) as total_driver_id_matches,
    COUNT(DISTINCT source_table) as source_tables_count
FROM driver_id_matches;

-- ============================================================================
-- MUESTRA 2: Matches por license/phone normalizado (scouting_daily)
-- ============================================================================
-- Paso 1: Obtener license/phone normalizados de drivers en cuarentena
WITH quarantined_sample AS (
    SELECT driver_id, person_key
    FROM canon.driver_orphan_quarantine
    WHERE status = 'quarantined'
    LIMIT 20
),
driver_normalized AS (
    SELECT 
        q.driver_id,
        q.person_key,
        -- Intentar desde drivers_index primero
        COALESCE(
            di.license_norm,
            -- Fallback a drivers con normalización
            UPPER(REGEXP_REPLACE(REGEXP_REPLACE(REGEXP_REPLACE(
                d.license_normalized_number::text,
                '[^A-Z0-9]', '', 'g'
            ), ' ', '', 'g'), '-', '', 'g'))
        ) as driver_license_norm,
        COALESCE(
            di.phone_norm,
            -- Fallback a drivers con normalización
            REGEXP_REPLACE(REGEXP_REPLACE(REGEXP_REPLACE(REGEXP_REPLACE(
                d.phone::text,
                '[^0-9]', '', 'g'
            ), ' ', '', 'g'), '-', '', 'g'), '\(', '', 'g')
        ) as driver_phone_norm
    FROM quarantined_sample q
    LEFT JOIN canon.drivers_index di ON di.driver_id = q.driver_id
    LEFT JOIN public.drivers d ON d.driver_id::text = q.driver_id
),
-- Paso 2: Obtener license/phone normalizados de lead_events (scouting_daily)
events_normalized AS (
    SELECT 
        le.id as event_id,
        le.source_table,
        le.source_pk,
        le.event_date,
        le.payload_json,
        -- Normalizar license del evento
        CASE 
            WHEN le.payload_json->>'driver_license' IS NOT NULL THEN
                UPPER(REGEXP_REPLACE(REGEXP_REPLACE(REGEXP_REPLACE(
                    le.payload_json->>'driver_license',
                    '[^A-Z0-9]', '', 'g'
                ), ' ', '', 'g'), '-', '', 'g'))
            ELSE NULL
        END as event_license_norm,
        -- Normalizar phone del evento
        CASE 
            WHEN le.payload_json->>'driver_phone' IS NOT NULL THEN
                REGEXP_REPLACE(REGEXP_REPLACE(REGEXP_REPLACE(REGEXP_REPLACE(
                    le.payload_json->>'driver_phone',
                    '[^0-9]', '', 'g'
                ), ' ', '', 'g'), '-', '', 'g'), '\(', '', 'g')
            ELSE NULL
        END as event_phone_norm
    FROM observational.lead_events le
    WHERE le.source_table = 'module_ct_scouting_daily'
      AND le.payload_json IS NOT NULL
      AND (le.payload_json ? 'driver_license' OR le.payload_json ? 'driver_phone')
),
-- Paso 3: Matches exactos normalizados
license_phone_matches AS (
    SELECT 
        dn.driver_id,
        dn.person_key,
        en.event_id,
        en.source_table,
        en.source_pk,
        en.event_date,
        en.payload_json,
        CASE 
            WHEN dn.driver_license_norm IS NOT NULL 
                 AND en.event_license_norm IS NOT NULL 
                 AND dn.driver_license_norm = en.event_license_norm THEN 'license_exact'
            WHEN dn.driver_phone_norm IS NOT NULL 
                 AND en.event_phone_norm IS NOT NULL 
                 AND dn.driver_phone_norm = en.event_phone_norm THEN 'phone_exact'
            WHEN dn.driver_license_norm IS NOT NULL 
                 AND dn.driver_phone_norm IS NOT NULL 
                 AND en.event_license_norm IS NOT NULL 
                 AND en.event_phone_norm IS NOT NULL 
                 AND dn.driver_license_norm = en.event_license_norm 
                 AND dn.driver_phone_norm = en.event_phone_norm THEN 'both_exact'
            ELSE NULL
        END as match_strategy,
        dn.driver_license_norm,
        dn.driver_phone_norm,
        en.event_license_norm,
        en.event_phone_norm
    FROM driver_normalized dn
    INNER JOIN events_normalized en ON (
        (dn.driver_license_norm IS NOT NULL 
         AND en.event_license_norm IS NOT NULL 
         AND dn.driver_license_norm = en.event_license_norm)
        OR
        (dn.driver_phone_norm IS NOT NULL 
         AND en.event_phone_norm IS NOT NULL 
         AND dn.driver_phone_norm = en.event_phone_norm)
    )
    WHERE dn.driver_license_norm IS NOT NULL 
       OR dn.driver_phone_norm IS NOT NULL
)
SELECT 
    COUNT(DISTINCT driver_id) as drivers_with_license_phone_matches,
    COUNT(*) as total_license_phone_matches,
    COUNT(DISTINCT CASE WHEN match_strategy = 'license_exact' THEN driver_id END) as drivers_license_match,
    COUNT(DISTINCT CASE WHEN match_strategy = 'phone_exact' THEN driver_id END) as drivers_phone_match,
    COUNT(DISTINCT CASE WHEN match_strategy = 'both_exact' THEN driver_id END) as drivers_both_match
FROM license_phone_matches
WHERE match_strategy IS NOT NULL;

-- ============================================================================
-- MUESTRA DETALLADA: Ejemplos de matches encontrados
-- ============================================================================
WITH quarantined_sample AS (
    SELECT driver_id, person_key
    FROM canon.driver_orphan_quarantine
    WHERE status = 'quarantined'
    LIMIT 5
),
driver_normalized AS (
    SELECT 
        q.driver_id,
        q.person_key,
        COALESCE(
            di.license_norm,
            UPPER(REGEXP_REPLACE(REGEXP_REPLACE(REGEXP_REPLACE(
                d.license_normalized_number::text,
                '[^A-Z0-9]', '', 'g'
            ), ' ', '', 'g'), '-', '', 'g'))
        ) as driver_license_norm,
        COALESCE(
            di.phone_norm,
            REGEXP_REPLACE(REGEXP_REPLACE(REGEXP_REPLACE(REGEXP_REPLACE(
                d.phone::text,
                '[^0-9]', '', 'g'
            ), ' ', '', 'g'), '-', '', 'g'), '\(', '', 'g')
        ) as driver_phone_norm
    FROM quarantined_sample q
    LEFT JOIN canon.drivers_index di ON di.driver_id = q.driver_id
    LEFT JOIN public.drivers d ON d.driver_id::text = q.driver_id
),
events_normalized AS (
    SELECT 
        le.id as event_id,
        le.source_table,
        le.source_pk,
        le.event_date,
        le.payload_json,
        UPPER(REGEXP_REPLACE(REGEXP_REPLACE(REGEXP_REPLACE(
            le.payload_json->>'driver_license',
            '[^A-Z0-9]', '', 'g'
        ), ' ', '', 'g'), '-', '', 'g')) as event_license_norm,
        REGEXP_REPLACE(REGEXP_REPLACE(REGEXP_REPLACE(REGEXP_REPLACE(
            le.payload_json->>'driver_phone',
            '[^0-9]', '', 'g'
        ), ' ', '', 'g'), '-', '', 'g'), '\(', '', 'g') as event_phone_norm
    FROM observational.lead_events le
    WHERE le.source_table = 'module_ct_scouting_daily'
      AND le.payload_json IS NOT NULL
      AND (le.payload_json ? 'driver_license' OR le.payload_json ? 'driver_phone')
),
matches_detail AS (
    SELECT 
        dn.driver_id,
        en.event_id,
        en.source_table,
        en.source_pk,
        en.event_date,
        CASE 
            WHEN dn.driver_license_norm = en.event_license_norm 
                 AND dn.driver_phone_norm = en.event_phone_norm THEN 'both_exact'
            WHEN dn.driver_license_norm = en.event_license_norm THEN 'license_exact'
            WHEN dn.driver_phone_norm = en.event_phone_norm THEN 'phone_exact'
            ELSE NULL
        END as match_strategy,
        -- Masked para seguridad
        LEFT(dn.driver_license_norm, 3) || '***' || RIGHT(dn.driver_license_norm, 2) as driver_license_masked,
        LEFT(dn.driver_phone_norm, 3) || '***' || RIGHT(dn.driver_phone_norm, 2) as driver_phone_masked,
        LEFT(en.event_license_norm, 3) || '***' || RIGHT(en.event_license_norm, 2) as event_license_masked,
        LEFT(en.event_phone_norm, 3) || '***' || RIGHT(en.event_phone_norm, 2) as event_phone_masked
    FROM driver_normalized dn
    INNER JOIN events_normalized en ON (
        (dn.driver_license_norm IS NOT NULL 
         AND en.event_license_norm IS NOT NULL 
         AND dn.driver_license_norm = en.event_license_norm)
        OR
        (dn.driver_phone_norm IS NOT NULL 
         AND en.event_phone_norm IS NOT NULL 
         AND dn.driver_phone_norm = en.event_phone_norm)
    )
    WHERE (dn.driver_license_norm IS NOT NULL OR dn.driver_phone_norm IS NOT NULL)
)
SELECT *
FROM matches_detail
WHERE match_strategy IS NOT NULL
ORDER BY driver_id, event_date DESC
LIMIT 10;


