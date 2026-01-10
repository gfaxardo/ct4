-- ============================================================================
-- CATEGORIZACIÓN DE PERSONAS SIN SCOUT
-- ============================================================================
-- Objetivo: Crear vista ops.v_persons_without_scout_categorized con categorías
-- Ejecución: Idempotente (CREATE OR REPLACE VIEW)
-- ============================================================================

DROP VIEW IF EXISTS ops.v_persons_without_scout_categorized CASCADE;
CREATE VIEW ops.v_persons_without_scout_categorized AS
WITH persons_without_scout AS (
    SELECT DISTINCT
        ir.person_key,
        ir.primary_full_name,
        ir.primary_phone,
        ir.primary_license,
        ir.created_at AS identity_created_at,
        -- Verificar si tiene scout en eventos
        EXISTS (
            SELECT 1 FROM observational.lead_events le
            WHERE le.person_key = ir.person_key
                AND (le.scout_id IS NOT NULL OR (le.payload_json IS NOT NULL AND le.payload_json->>'scout_id' IS NOT NULL))
        ) AS has_scout_in_events,
        -- Verificar si tiene eventos
        EXISTS (SELECT 1 FROM observational.lead_events le WHERE le.person_key = ir.person_key) AS has_lead_events,
        -- Verificar si tiene ledger
        EXISTS (SELECT 1 FROM observational.lead_ledger ll WHERE ll.person_key = ir.person_key) AS has_lead_ledger,
        -- Verificar si tiene ledger con scout
        EXISTS (
            SELECT 1 FROM observational.lead_ledger ll
            WHERE ll.person_key = ir.person_key
                AND ll.attributed_scout_id IS NOT NULL
        ) AS has_scout_in_ledger,
        -- Contar eventos
        (SELECT COUNT(*) FROM observational.lead_events le WHERE le.person_key = ir.person_key) AS lead_events_count,
        -- Contar eventos con scout
        (SELECT COUNT(*) FROM observational.lead_events le 
         WHERE le.person_key = ir.person_key
            AND (le.scout_id IS NOT NULL OR (le.payload_json IS NOT NULL AND le.payload_json->>'scout_id' IS NOT NULL))
        ) AS events_with_scout_count,
        -- Scout ID desde eventos (si existe único)
        (SELECT DISTINCT COALESCE(le.scout_id, (le.payload_json->>'scout_id')::INTEGER)
         FROM observational.lead_events le
         WHERE le.person_key = ir.person_key
            AND (le.scout_id IS NOT NULL OR (le.payload_json IS NOT NULL AND le.payload_json->>'scout_id' IS NOT NULL))
         LIMIT 1
        ) AS scout_id_from_events,
        -- Attribution rule desde ledger (si existe)
        (SELECT ll.attribution_rule
         FROM observational.lead_ledger ll
         WHERE ll.person_key = ir.person_key
         LIMIT 1
        ) AS ledger_attribution_rule
    FROM canon.identity_registry ir
    LEFT JOIN observational.lead_ledger ll_with_scout 
        ON ll_with_scout.person_key = ir.person_key 
        AND ll_with_scout.attributed_scout_id IS NOT NULL
    WHERE ll_with_scout.person_key IS NULL
)
SELECT 
    person_key,
    primary_full_name,
    primary_phone,
    primary_license,
    identity_created_at,
    CASE 
        WHEN has_lead_events AND NOT has_scout_in_events THEN 
            'A: Tiene lead_events pero sin scout_id'
        WHEN has_lead_ledger AND NOT has_scout_in_ledger AND ledger_attribution_rule IS NOT NULL THEN 
            'B: Tiene lead_ledger sin scout (attribution_rule indica unassigned/bucket)'
        WHEN NOT has_lead_events AND NOT has_lead_ledger THEN 
            'C: Sin events ni ledger (legacy/externo)'
        WHEN has_scout_in_events AND NOT has_scout_in_ledger THEN 
            'D: Scout en events pero no en ledger'
        ELSE 
            'E: Otros (verificar manualmente)'
    END AS categoria,
    has_scout_in_events,
    has_lead_events,
    has_lead_ledger,
    has_scout_in_ledger,
    lead_events_count,
    events_with_scout_count,
    scout_id_from_events,
    ledger_attribution_rule,
    -- Agregar campos para ejemplos
    identity_created_at AS sample_date
FROM persons_without_scout;

COMMENT ON VIEW ops.v_persons_without_scout_categorized IS 
'Vista categorizando personas sin scout satisfactorio. Categorías: A (events sin scout), B (ledger sin scout), C (sin events ni ledger), D (scout en events pero no ledger), E (otros).';

-- ============================================================================
-- RESUMEN POR CATEGORÍA (ejecutar después de crear la vista)
-- ============================================================================

SELECT 
    categoria,
    COUNT(*) AS count,
    ROUND(COUNT(*)::NUMERIC / NULLIF((SELECT COUNT(*) FROM ops.v_persons_without_scout_categorized), 0) * 100, 2) AS pct
FROM ops.v_persons_without_scout_categorized
GROUP BY categoria
ORDER BY count DESC;

-- ============================================================================
-- MUESTRAS POR CATEGORÍA (top 50 por categoría)
-- ============================================================================

-- Categoría A
SELECT 
    'A: Tiene lead_events pero sin scout_id' AS categoria,
    person_key,
    primary_full_name,
    primary_phone,
    primary_license,
    lead_events_count,
    identity_created_at
FROM ops.v_persons_without_scout_categorized
WHERE categoria = 'A: Tiene lead_events pero sin scout_id'
ORDER BY lead_events_count DESC, identity_created_at DESC
LIMIT 50;

-- Categoría B
SELECT 
    'B: Tiene lead_ledger sin scout' AS categoria,
    person_key,
    primary_full_name,
    primary_phone,
    primary_license,
    ledger_attribution_rule,
    identity_created_at
FROM ops.v_persons_without_scout_categorized
WHERE categoria = 'B: Tiene lead_ledger sin scout (attribution_rule indica unassigned/bucket)'
ORDER BY identity_created_at DESC
LIMIT 50;

-- Categoría C
SELECT 
    'C: Sin events ni ledger' AS categoria,
    person_key,
    primary_full_name,
    primary_phone,
    primary_license,
    identity_created_at
FROM ops.v_persons_without_scout_categorized
WHERE categoria = 'C: Sin events ni ledger (legacy/externo)'
ORDER BY identity_created_at DESC
LIMIT 50;

-- Categoría D
SELECT 
    'D: Scout en events pero no en ledger' AS categoria,
    person_key,
    primary_full_name,
    primary_phone,
    primary_license,
    scout_id_from_events,
    events_with_scout_count,
    identity_created_at
FROM ops.v_persons_without_scout_categorized
WHERE categoria = 'D: Scout en events pero no en ledger'
ORDER BY events_with_scout_count DESC, identity_created_at DESC
LIMIT 50;

-- Categoría E
SELECT 
    'E: Otros' AS categoria,
    person_key,
    primary_full_name,
    primary_phone,
    primary_license,
    has_scout_in_events,
    has_lead_events,
    has_lead_ledger,
    has_scout_in_ledger,
    identity_created_at
FROM ops.v_persons_without_scout_categorized
WHERE categoria = 'E: Otros (verificar manualmente)'
ORDER BY identity_created_at DESC
LIMIT 50;

