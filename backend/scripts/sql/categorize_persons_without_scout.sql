-- ============================================================================
-- CATEGORIZACIÓN DE PERSONAS SIN SCOUT
-- ============================================================================

CREATE OR REPLACE VIEW ops.v_persons_without_scout_categorized AS
WITH persons_without_scout AS (
    SELECT DISTINCT
        ir.person_key,
        ir.primary_full_name,
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
        ) AS events_with_scout_count
    FROM canon.identity_registry ir
    LEFT JOIN observational.lead_ledger ll_with_scout 
        ON ll_with_scout.person_key = ir.person_key 
        AND ll_with_scout.attributed_scout_id IS NOT NULL
    WHERE ll_with_scout.person_key IS NULL
)
SELECT 
    person_key,
    primary_full_name,
    identity_created_at,
    CASE 
        WHEN has_scout_in_events AND NOT has_scout_in_ledger THEN 
            'D: Scout en eventos, no en ledger'
        WHEN has_lead_events AND NOT has_scout_in_events THEN 
            'A: Tienen eventos pero sin scout_id'
        WHEN has_lead_ledger AND NOT has_scout_in_ledger THEN 
            'B: Tienen ledger pero sin scout'
        ELSE 
            'C: Sin eventos ni ledger (legacy/externo)'
    END AS categoria,
    has_scout_in_events,
    has_lead_events,
    has_lead_ledger,
    has_scout_in_ledger,
    lead_events_count,
    events_with_scout_count
FROM persons_without_scout;

-- Resumen por categoría
SELECT 
    categoria,
    COUNT(*) AS count,
    ROUND(COUNT(*)::NUMERIC / (SELECT COUNT(*) FROM ops.v_persons_without_scout_categorized) * 100, 2) AS pct
FROM ops.v_persons_without_scout_categorized
GROUP BY categoria
ORDER BY count DESC;


