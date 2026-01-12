-- ============================================================================
-- VISTA: ops.v_scout_attribution (CANÓNICA)
-- ============================================================================
-- Propósito: 1 fila por person_key (y driver_id si aplica) con scout_id canónico
-- Regla: ROW_NUMBER por priority ASC, attribution_date DESC, created_at DESC
-- Ejecución: Idempotente (DROP + CREATE)
-- ============================================================================

DROP VIEW IF EXISTS ops.v_scout_attribution CASCADE;
CREATE VIEW ops.v_scout_attribution AS
WITH ranked_attribution AS (
    SELECT 
        raw.person_key,
        raw.driver_id,
        raw.driver_license,
        raw.driver_phone,
        raw.scout_id,
        raw.acquisition_method,
        raw.source_table,
        raw.source_pk,
        raw.attribution_date,
        raw.created_at,
        raw.priority,
        ROW_NUMBER() OVER (
            PARTITION BY raw.person_key 
            ORDER BY raw.priority ASC, raw.attribution_date DESC, raw.created_at DESC
        ) AS rn
    FROM ops.v_scout_attribution_raw raw
    WHERE raw.person_key IS NOT NULL
)
SELECT 
    person_key,
    driver_id,
    driver_license,
    driver_phone,
    scout_id,
    acquisition_method,
    source_table,
    source_pk,
    attribution_date,
    created_at,
    priority
FROM ranked_attribution
WHERE rn = 1;

COMMENT ON VIEW ops.v_scout_attribution IS 
'Vista canónica de atribución scout: 1 fila por person_key usando la fuente de mayor prioridad. Prioridad: 1=lead_ledger (source-of-truth), 2=lead_events, 3=migrations, 4=scouting_daily, 5=cabinet_payments. Desempate por attribution_date DESC, created_at DESC.';

COMMENT ON COLUMN ops.v_scout_attribution.scout_id IS 
'Scout ID canónico para el person_key, seleccionado según prioridad de fuente.';
