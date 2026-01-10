-- ============================================================================
-- VISTA: ops.v_scout_attribution
-- ============================================================================
-- Propósito: 1 fila por person_key con el scout_id canónico (más alta prioridad)
-- Regla: ROW_NUMBER por priority + event_date (más antiguo primero)
-- Ejecución: Idempotente (DROP + CREATE)
-- ============================================================================

DROP VIEW IF EXISTS ops.v_scout_attribution CASCADE;

CREATE VIEW ops.v_scout_attribution AS
SELECT 
    person_key,
    driver_id,
    driver_license,
    driver_phone,
    scout_id,
    origin_tag,
    acquisition_method,
    source_table,
    source_pk,
    attribution_date,
    created_at,
    priority
FROM (
    SELECT 
        person_key,
        driver_id,
        driver_license,
        driver_phone,
        scout_id,
        origin_tag,
        acquisition_method,
        source_table,
        source_pk,
        attribution_date,
        created_at,
        priority,
        ROW_NUMBER() OVER (
            PARTITION BY person_key 
            ORDER BY priority ASC, attribution_date ASC, created_at ASC
        ) AS rn
    FROM ops.v_scout_attribution_raw
    WHERE person_key IS NOT NULL
) ranked
WHERE rn = 1;

COMMENT ON VIEW ops.v_scout_attribution IS 
'1 fila por person_key con el scout_id canónico (mayor prioridad, fecha más antigua). Prioridad: 1=lead_ledger, 2=lead_events, 3=migrations, 4=scouting_daily.';
