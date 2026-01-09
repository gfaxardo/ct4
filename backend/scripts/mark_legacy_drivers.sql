-- Script para marcar como legacy_external los drivers sin leads
-- que tienen first_seen_at anterior a LEAD_SYSTEM_START_DATE
--
-- IMPORTANTE: Ajustar la fecha según tu LEAD_SYSTEM_START_DATE real
-- Default: 2024-01-01

-- Paso 1: Crear registros de origen para drivers sin leads que son legacy
INSERT INTO canon.identity_origin (
    person_key,
    origin_tag,
    origin_source_id,
    origin_confidence,
    origin_created_at,
    ruleset_version,
    evidence,
    decided_by,
    decided_at,
    resolution_status,
    notes
)
SELECT 
    ir.person_key,
    'legacy_external'::origin_tag,
    COALESCE(
        (SELECT source_pk FROM canon.identity_links 
         WHERE person_key = ir.person_key 
         AND source_table = 'drivers' 
         ORDER BY linked_at LIMIT 1),
        ir.person_key::text
    ) AS origin_source_id,
    50.0 AS origin_confidence,  -- Baja confianza para legacy
    COALESCE(
        (SELECT MIN(linked_at) FROM canon.identity_links WHERE person_key = ir.person_key),
        ir.created_at
    ) AS origin_created_at,
    'origin_rules_v1' AS ruleset_version,
    jsonb_build_object(
        'reason', 'legacy_external',
        'first_seen_at', COALESCE(
            (SELECT MIN(linked_at) FROM canon.identity_links WHERE person_key = ir.person_key),
            ir.created_at
        )::text,
        'lead_system_start_date', '2024-01-01',  -- Ajustar según tu fecha real
        'driver_link', (
            SELECT jsonb_build_object(
                'source_pk', source_pk,
                'linked_at', linked_at::text
            )
            FROM canon.identity_links
            WHERE person_key = ir.person_key
            AND source_table = 'drivers'
            ORDER BY linked_at
            LIMIT 1
        )
    ) AS evidence,
    'system'::decided_by_type AS decided_by,
    NOW() AS decided_at,
    'marked_legacy'::origin_resolution_status AS resolution_status,
    'Marcado automáticamente como legacy: driver sin lead, first_seen_at anterior a sistema de leads' AS notes
FROM canon.identity_registry ir
WHERE NOT EXISTS (
    SELECT 1 FROM canon.identity_origin io WHERE io.person_key = ir.person_key
)
AND EXISTS (
    SELECT 1 FROM canon.identity_links il
    WHERE il.person_key = ir.person_key
    AND il.source_table = 'drivers'
)
AND NOT EXISTS (
    SELECT 1 FROM canon.identity_links il
    WHERE il.person_key = ir.person_key
    AND il.source_table IN ('module_ct_cabinet_leads', 'module_ct_scouting_daily', 'module_ct_migrations')
)
AND COALESCE(
    (SELECT MIN(linked_at) FROM canon.identity_links WHERE person_key = ir.person_key),
    ir.created_at
) < '2024-01-01'::date  -- Ajustar según tu LEAD_SYSTEM_START_DATE real
ON CONFLICT (person_key) DO NOTHING;

-- Paso 2: Verificar cuántos se marcaron
SELECT 
    COUNT(*) as total_marcados,
    COUNT(*) FILTER (WHERE resolution_status = 'marked_legacy') as marcados_como_legacy
FROM canon.identity_origin
WHERE origin_tag = 'legacy_external'
AND resolution_status = 'marked_legacy';

-- Paso 3: Ver muestra de casos marcados
SELECT 
    person_key,
    origin_tag,
    origin_source_id,
    origin_confidence,
    origin_created_at,
    resolution_status,
    notes
FROM canon.identity_origin
WHERE origin_tag = 'legacy_external'
AND resolution_status = 'marked_legacy'
ORDER BY origin_created_at
LIMIT 10;

