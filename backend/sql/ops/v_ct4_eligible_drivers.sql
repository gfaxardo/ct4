-- ============================================================================
-- Vista: ops.v_ct4_eligible_drivers
-- ============================================================================
-- PROPÓSITO:
-- Vista canónica que define el "universo elegible CT4" de drivers que pueden
-- recibir pagos por milestones. Combina información de origen (cabinet/fleet_migration)
-- e identidad confirmada (person_key + identity_status).
--
-- USO:
-- - Filtrar cálculos de ACHIEVED a solo drivers elegibles
-- - Filtrar cálculos de pagos a solo drivers elegibles
-- - Base para reconciliación y reportes operativos
-- - Auditoría de drivers que deberían estar en el sistema
-- ============================================================================
-- REGLAS DE ELEGIBILIDAD:
-- 1. origin_tag IN ('cabinet', 'fleet_migration') - Solo estos orígenes son elegibles
-- 2. identity_status = 'confirmed' O NULL - Drivers con identidad confirmada o sin status
--    (NOTA: NULL se permite porque algunos drivers pueden tener person_key sin status explícito)
-- 3. driver_id IS NOT NULL - Requiere driver_id válido
-- ============================================================================
-- FUENTES CANÓNICAS:
-- - origin_tag: observational.v_conversion_metrics (fuente canónica de origen)
-- - person_key: canon.identity_links (source_table='drivers') o v_conversion_metrics
-- - identity_status: ops.v_yango_payments_ledger_latest_enriched o canon.identity_links
-- - match_rule/match_confidence: canon.identity_links (confidence_level, match_rule)
-- - first_seen_at: MIN(snapshot_date) desde canon.identity_links
-- - latest_snapshot_at: MAX(latest_snapshot_at) desde v_yango_payments_ledger_latest_enriched
-- ============================================================================
-- GRANO:
-- (driver_id) - 1 fila por driver elegible
-- ============================================================================
-- NOTA IMPORTANTE:
-- Esta vista es READ-ONLY y no modifica lógica de pagos existente.
-- Es una capa de filtrado canónica para asegurar consistencia en cálculos.
-- ============================================================================

CREATE OR REPLACE VIEW ops.v_ct4_eligible_drivers AS
WITH conversion_metrics_base AS (
    -- Fuente canónica de origin_tag: observational.v_conversion_metrics
    SELECT DISTINCT
        cm.person_key,
        cm.origin_tag,
        cm.driver_id,
        cm.lead_date
    FROM observational.v_conversion_metrics cm
    WHERE cm.origin_tag IN ('cabinet', 'fleet_migration')
        AND cm.driver_id IS NOT NULL
),
identity_links_info AS (
    -- Información de identidad desde canon.identity_links (source_table='drivers')
    SELECT 
        il.person_key,
        il.source_pk AS driver_id,
        il.confidence_level,
        il.match_rule,
        il.match_score,
        MIN(il.snapshot_date) AS first_seen_at,
        MAX(il.linked_at) AS latest_linked_at
    FROM canon.identity_links il
    WHERE il.source_table = 'drivers'
    GROUP BY il.person_key, il.source_pk, il.confidence_level, il.match_rule, il.match_score
),
ledger_identity_status AS (
    -- identity_status desde ledger enriquecido (último estado conocido)
    SELECT DISTINCT ON (driver_id_final)
        driver_id_final AS driver_id,
        person_key_final AS person_key,
        identity_status,
        match_rule AS ledger_match_rule,
        match_confidence AS ledger_match_confidence,
        latest_snapshot_at
    FROM ops.v_yango_payments_ledger_latest_enriched
    WHERE driver_id_final IS NOT NULL
    ORDER BY driver_id_final, latest_snapshot_at DESC
),
eligible_drivers_base AS (
    -- Combinar todas las fuentes
    SELECT DISTINCT
        cmb.driver_id,
        COALESCE(li.person_key, cmb.person_key) AS person_key,
        cmb.origin_tag,
        -- identity_status: prioridad a ledger, luego confidence_level desde identity_links
        COALESCE(
            lis.identity_status,
            CASE 
                WHEN li.confidence_level = 'HIGH' THEN 'confirmed'
                WHEN li.confidence_level = 'MEDIUM' THEN 'enriched'
                WHEN li.confidence_level = 'LOW' THEN 'ambiguous'
                ELSE NULL
            END
        ) AS identity_status,
        -- match_rule: prioridad a ledger, luego identity_links
        COALESCE(lis.ledger_match_rule, li.match_rule) AS match_rule,
        -- match_confidence: prioridad a ledger, luego mapear desde confidence_level
        COALESCE(
            lis.ledger_match_confidence,
            CASE 
                WHEN li.confidence_level = 'HIGH' THEN 'high'
                WHEN li.confidence_level = 'MEDIUM' THEN 'medium'
                WHEN li.confidence_level = 'LOW' THEN 'low'
                ELSE NULL
            END
        ) AS match_confidence,
        -- first_seen_at: desde identity_links o lead_date
        COALESCE(li.first_seen_at::date, cmb.lead_date) AS first_seen_at,
        -- latest_snapshot_at: desde ledger o latest_linked_at
        COALESCE(lis.latest_snapshot_at, li.latest_linked_at) AS latest_snapshot_at
    FROM conversion_metrics_base cmb
    LEFT JOIN identity_links_info li
        ON li.driver_id = cmb.driver_id
    LEFT JOIN ledger_identity_status lis
        ON lis.driver_id = cmb.driver_id
)
SELECT 
    driver_id,
    person_key,
    origin_tag,
    identity_status,
    match_rule,
    match_confidence,
    first_seen_at,
    latest_snapshot_at
FROM eligible_drivers_base
WHERE driver_id IS NOT NULL
    -- Filtrar por elegibilidad: origin_tag válido y (identity_status confirmado o NULL)
    -- NOTA: NULL se permite porque algunos drivers pueden tener person_key sin status explícito
    -- pero están en el sistema y pueden recibir pagos
    AND (
        identity_status = 'confirmed' 
        OR identity_status IS NULL
        OR identity_status = 'enriched'  -- enriched también es elegible (matching por nombre único)
    )
ORDER BY driver_id;

-- ============================================================================
-- Comentarios
-- ============================================================================
COMMENT ON VIEW ops.v_ct4_eligible_drivers IS 
'Vista canónica que define el universo elegible CT4 de drivers que pueden recibir pagos por milestones. Combina información de origen (cabinet/fleet_migration) e identidad confirmada. Se usa para filtrar cálculos de ACHIEVED y pagos. Read-only. Grano: (driver_id) - 1 fila por driver elegible.';

COMMENT ON COLUMN ops.v_ct4_eligible_drivers.driver_id IS 
'ID del conductor (driver_id). Requerido para elegibilidad.';

COMMENT ON COLUMN ops.v_ct4_eligible_drivers.person_key IS 
'Person key del conductor (identidad canónica). Puede ser NULL si el driver no tiene identidad confirmada aún.';

COMMENT ON COLUMN ops.v_ct4_eligible_drivers.origin_tag IS 
'Origen del lead: ''cabinet'' o ''fleet_migration''. Solo estos orígenes son elegibles para pagos CT4.';

COMMENT ON COLUMN ops.v_ct4_eligible_drivers.identity_status IS 
'Estado de identidad: ''confirmed'' (upstream), ''enriched'' (matching único), ''ambiguous'' (sin match único), ''no_match'' (sin datos), o NULL. Drivers con status ''confirmed'' o NULL son elegibles. ''enriched'' también es elegible.';

COMMENT ON COLUMN ops.v_ct4_eligible_drivers.match_rule IS 
'Regla de matching: ''source_upstream'', ''name_unique'', ''ambiguous'', ''no_match'', o NULL.';

COMMENT ON COLUMN ops.v_ct4_eligible_drivers.match_confidence IS 
'Confianza del match: ''high'', ''medium'', ''low'', o NULL.';

COMMENT ON COLUMN ops.v_ct4_eligible_drivers.first_seen_at IS 
'Primera fecha en que se vio este driver en el sistema (desde identity_links.snapshot_date o conversion_metrics.lead_date).';

COMMENT ON COLUMN ops.v_ct4_eligible_drivers.latest_snapshot_at IS 
'Último snapshot conocido del driver (desde ledger o identity_links.linked_at).';

-- ============================================================================
-- Queries de Validación (comentados para referencia)
-- ============================================================================
/*
-- 1. Conteo total de drivers elegibles
SELECT COUNT(*) AS total_eligible_drivers
FROM ops.v_ct4_eligible_drivers;

-- 2. Conteo por origin_tag
SELECT 
    origin_tag,
    COUNT(*) AS count_drivers,
    ROUND(100.0 * COUNT(*) / NULLIF((SELECT COUNT(*) FROM ops.v_ct4_eligible_drivers), 0), 2) AS pct_total
FROM ops.v_ct4_eligible_drivers
GROUP BY origin_tag
ORDER BY count_drivers DESC;

-- 3. Conteo por identity_status
SELECT 
    COALESCE(identity_status, 'NULL') AS identity_status,
    COUNT(*) AS count_drivers,
    ROUND(100.0 * COUNT(*) / NULLIF((SELECT COUNT(*) FROM ops.v_ct4_eligible_drivers), 0), 2) AS pct_total
FROM ops.v_ct4_eligible_drivers
GROUP BY identity_status
ORDER BY count_drivers DESC;

-- 4. Top 20 drivers más recientes
SELECT 
    driver_id,
    person_key,
    origin_tag,
    identity_status,
    match_rule,
    match_confidence,
    first_seen_at,
    latest_snapshot_at
FROM ops.v_ct4_eligible_drivers
ORDER BY latest_snapshot_at DESC NULLS LAST, first_seen_at DESC NULLS LAST
LIMIT 20;

-- 5. Distribución por match_confidence
SELECT 
    COALESCE(match_confidence, 'NULL') AS match_confidence,
    COUNT(*) AS count_drivers,
    ROUND(100.0 * COUNT(*) / NULLIF((SELECT COUNT(*) FROM ops.v_ct4_eligible_drivers), 0), 2) AS pct_total
FROM ops.v_ct4_eligible_drivers
GROUP BY match_confidence
ORDER BY 
    CASE match_confidence
        WHEN 'high' THEN 1
        WHEN 'medium' THEN 2
        WHEN 'low' THEN 3
        ELSE 4
    END;

-- 6. Drivers sin person_key (deberían ser pocos)
SELECT 
    COUNT(*) AS drivers_without_person_key,
    ROUND(100.0 * COUNT(*) / NULLIF((SELECT COUNT(*) FROM ops.v_ct4_eligible_drivers), 0), 2) AS pct_total
FROM ops.v_ct4_eligible_drivers
WHERE person_key IS NULL;

-- 7. Comparación con v_payments_driver_matrix_cabinet (drivers en matrix vs elegibles)
SELECT 
    'En matrix pero no elegible' AS category,
    COUNT(*) AS count_drivers
FROM ops.v_payments_driver_matrix_cabinet dm
WHERE NOT EXISTS (
    SELECT 1 
    FROM ops.v_ct4_eligible_drivers ed
    WHERE ed.driver_id = dm.driver_id
)
UNION ALL
SELECT 
    'Elegible pero no en matrix' AS category,
    COUNT(*) AS count_drivers
FROM ops.v_ct4_eligible_drivers ed
WHERE NOT EXISTS (
    SELECT 1 
    FROM ops.v_payments_driver_matrix_cabinet dm
    WHERE dm.driver_id = ed.driver_id
);
*/







