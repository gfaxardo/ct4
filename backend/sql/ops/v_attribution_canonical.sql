-- Vista de Atribución Canónica
-- Determina la atribución de scouts a leads usando reglas de prioridad
-- 
-- Reglas de atribución:
-- R1 (HIGH): Si existe evento en observational.lead_events con source_table='module_ct_migrations'
--            => acquisition_scout_id desde payload_json->>'scout_id' o scout_id
--            confidence='high', rule='migrations_direct'
--
-- R2 (MEDIUM): Si NO hay R1 y existe evento source_table='module_ct_scouting_daily'
--             => acquisition_scout_id desde payload_json->>'scout_id' o scout_id
--             confidence='medium', rule='scouting_daily'
--
-- R3 (UNKNOWN): Si no hay nada => acquisition_scout_id NULL, confidence='unknown', rule='none'
--
-- Campos de salida:
-- - person_key
-- - lead_origin (mapeo desde origin_tag: cabinet/migration)
-- - acquisition_scout_id
-- - acquisition_scout_name (desde ops.v_dim_scouts)
-- - attribution_confidence
-- - attribution_rule
-- - attribution_evidence (JSONB con: chosen_source_table, chosen_source_pk, chosen_event_date, chosen_payload)

CREATE OR REPLACE VIEW ops.v_attribution_canonical AS
WITH base_metrics AS (
    -- Base: una fila por (person_key, origin_tag) desde v_conversion_metrics
    SELECT DISTINCT
        person_key,
        origin_tag,
        -- Mapear origin_tag a lead_origin
        CASE 
            WHEN origin_tag = 'cabinet' THEN 'cabinet'
            WHEN origin_tag = 'fleet_migration' THEN 'migration'
            WHEN origin_tag LIKE '%cabinet%' THEN 'cabinet'
            WHEN origin_tag LIKE '%migration%' THEN 'migration'
            ELSE 'unknown'
        END AS lead_origin
    FROM observational.v_conversion_metrics
    WHERE person_key IS NOT NULL
),
best_evidence AS (
    -- Usar LATERAL JOIN para encontrar el mejor evento por person_key con prioridad
    SELECT DISTINCT ON (bm.person_key)
        bm.person_key,
        bm.lead_origin,
        -- Extraer scout_id: primero desde payload_json->>'scout_id', luego desde scout_id directo
        COALESCE(
            NULLIF((le.payload_json->>'scout_id'), '')::int,
            le.scout_id
        ) AS acquisition_scout_id,
        -- Determinar confidence y rule según source_table
        CASE 
            WHEN le.source_table = 'module_ct_migrations' THEN 'high'
            WHEN le.source_table = 'module_ct_scouting_daily' THEN 'medium'
            ELSE 'unknown'
        END AS attribution_confidence,
        CASE 
            WHEN le.source_table = 'module_ct_migrations' THEN 'migrations_direct'
            WHEN le.source_table = 'module_ct_scouting_daily' THEN 'scouting_daily'
            ELSE 'none'
        END AS attribution_rule,
        -- Construir evidence JSONB
        jsonb_build_object(
            'chosen_source_table', le.source_table,
            'chosen_source_pk', le.source_pk,
            'chosen_event_date', le.event_date,
            'chosen_payload', le.payload_json
        ) AS attribution_evidence
    FROM base_metrics bm
    LEFT JOIN LATERAL (
        SELECT 
            le_inner.source_table,
            le_inner.source_pk,
            le_inner.event_date,
            le_inner.scout_id,
            le_inner.payload_json
        FROM observational.lead_events le_inner
        WHERE le_inner.person_key = bm.person_key
            AND (
                le_inner.source_table = 'module_ct_migrations'
                OR le_inner.source_table = 'module_ct_scouting_daily'
            )
        ORDER BY 
            -- Prioridad: migrations primero, luego scouting_daily
            CASE le_inner.source_table
                WHEN 'module_ct_migrations' THEN 1
                WHEN 'module_ct_scouting_daily' THEN 2
                ELSE 3
            END,
            -- Si hay múltiples del mismo tipo, usar el más reciente
            le_inner.event_date DESC,
            le_inner.created_at DESC
        LIMIT 1
    ) le ON true
)
-- Selección final con join a dim_scouts
SELECT 
    be.person_key,
    be.lead_origin,
    be.acquisition_scout_id,
    ds.scout_name_normalized AS acquisition_scout_name,
    COALESCE(be.attribution_confidence, 'unknown') AS attribution_confidence,
    COALESCE(be.attribution_rule, 'none') AS attribution_rule,
    COALESCE(be.attribution_evidence, jsonb_build_object()) AS attribution_evidence
FROM best_evidence be
LEFT JOIN ops.v_dim_scouts ds 
    ON ds.scout_id = be.acquisition_scout_id;

COMMENT ON VIEW ops.v_attribution_canonical IS 
'Vista de atribución canónica de scouts a leads. Aplica reglas de prioridad:
- R1 (HIGH): eventos de module_ct_migrations
- R2 (MEDIUM): eventos de module_ct_scouting_daily (solo si no hay R1)
- R3 (UNKNOWN): sin evidencia

Incluye join con ops.v_dim_scouts para obtener nombres normalizados de scouts.';

