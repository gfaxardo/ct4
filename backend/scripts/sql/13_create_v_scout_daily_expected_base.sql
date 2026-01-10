-- ============================================================================
-- VISTA: ops.v_scout_daily_expected_base
-- ============================================================================
-- Propósito: Base para liquidación diaria scout (pre-C2/C3 scout)
-- Grano: scout_id + date
-- Fuente: cobranza_yango_with_scout o funnel/trips según existan
-- Objetivo: Preparar dataset para liquidación con milestones alcanzados
-- Ejecución: Idempotente (DROP + CREATE)
-- NOTA: NO crea claims ni ledger de pagos scout todavía (solo base)
-- ============================================================================

DROP VIEW IF EXISTS ops.v_scout_daily_expected_base CASCADE;
CREATE VIEW ops.v_scout_daily_expected_base AS
WITH scout_claims AS (
    -- Fuente: cobranza Yango con scout (milestones 1, 5, 25)
    -- Si v_yango_collection_with_scout existe, usarla; sino, usar v_yango_cabinet_claims_for_collection y join manual
    SELECT 
        ll.attributed_scout_id AS scout_id,
        y.lead_date AS milestone_date,
        y.milestone_value,
        y.person_key,
        y.driver_id,
        y.expected_amount,
        CASE 
            WHEN ll.attributed_scout_id IS NOT NULL THEN 'SATISFACTORY_LEDGER' 
            ELSE 'MISSING' 
        END AS scout_quality_bucket,
        -- Ventana scout: 30 días desde lead_date (ajustar según reglas de negocio)
        y.lead_date AS scout_window_start,
        y.lead_date + INTERVAL '30 days' AS scout_window_end
    FROM ops.v_yango_cabinet_claims_for_collection y
    LEFT JOIN observational.lead_ledger ll ON ll.person_key = y.person_key AND ll.attributed_scout_id IS NOT NULL
    WHERE ll.attributed_scout_id IS NOT NULL
        AND y.milestone_value IN (1, 5, 25)
)
SELECT 
    scout_id,
    milestone_date::DATE AS date,
    milestone_value,
    COUNT(DISTINCT person_key) AS drivers_count,
    COUNT(DISTINCT driver_id) AS driver_ids_count,
    COUNT(*) AS milestone_occurrences,
    SUM(expected_amount) AS total_expected_amount,
    -- Counts por milestone
    COUNT(*) FILTER (WHERE milestone_value = 1) AS m1_count,
    COUNT(*) FILTER (WHERE milestone_value = 5) AS m5_count,
    COUNT(*) FILTER (WHERE milestone_value = 25) AS m25_count,
    -- Expected amounts incremental por milestone (20/25/55 según reglas)
    SUM(expected_amount) FILTER (WHERE milestone_value = 1) AS expected_amount_m1,
    SUM(expected_amount) FILTER (WHERE milestone_value = 5) AS expected_amount_m5,
    SUM(expected_amount) FILTER (WHERE milestone_value = 25) AS expected_amount_m25,
    -- Scout quality distribution
    COUNT(*) FILTER (WHERE scout_quality_bucket = 'SATISFACTORY_LEDGER') AS satisfactory_ledger_count,
    COUNT(*) FILTER (WHERE scout_quality_bucket = 'EVENTS_ONLY') AS events_only_count,
    COUNT(*) FILTER (WHERE scout_quality_bucket = 'SCOUTING_DAILY_ONLY') AS scouting_daily_only_count,
    -- Metadata
    MIN(scout_window_start) AS earliest_scout_window_start,
    MAX(scout_window_end) AS latest_scout_window_end
FROM scout_claims
GROUP BY scout_id, milestone_date::DATE, milestone_value;

COMMENT ON VIEW ops.v_scout_daily_expected_base IS 
'Base para liquidación diaria scout: grano scout_id + date + milestone_value. Fuente: cobranza Yango con scout (milestones 1, 5, 25). Preparado para construir C2/C3 scout claims en el futuro. NO crea claims ni ledger de pagos scout todavía.';

COMMENT ON COLUMN ops.v_scout_daily_expected_base.scout_id IS 
'ID del scout al que se atribuyen los milestones.';

COMMENT ON COLUMN ops.v_scout_daily_expected_base.date IS 
'Fecha del milestone (lead_date del claim).';

COMMENT ON COLUMN ops.v_scout_daily_expected_base.milestone_value IS 
'Valor del milestone alcanzado (1, 5, o 25).';

COMMENT ON COLUMN ops.v_scout_daily_expected_base.expected_amount_m1 IS 
'Monto esperado incremental para M1 (típicamente 20 según reglas).';

COMMENT ON COLUMN ops.v_scout_daily_expected_base.expected_amount_m5 IS 
'Monto esperado incremental para M5 (típicamente 25 según reglas).';

COMMENT ON COLUMN ops.v_scout_daily_expected_base.expected_amount_m25 IS 
'Monto esperado incremental para M25 (típicamente 55 según reglas).';

-- ============================================================================
-- RESUMEN POR SCOUT (ejemplo de uso)
-- ============================================================================

SELECT 
    'RESUMEN SCOUT DAILY EXPECTED BASE' AS section,
    COUNT(DISTINCT scout_id) AS distinct_scouts,
    COUNT(DISTINCT date) AS distinct_dates,
    COUNT(*) AS total_records,
    SUM(milestone_occurrences) AS total_milestone_occurrences,
    SUM(total_expected_amount) AS total_expected_amount_all
FROM ops.v_scout_daily_expected_base;

-- Top 20 scouts por monto esperado
SELECT 
    scout_id,
    COUNT(DISTINCT date) AS active_days,
    SUM(milestone_occurrences) AS total_milestones,
    SUM(total_expected_amount) AS total_expected_amount,
    SUM(expected_amount_m1) AS total_m1,
    SUM(expected_amount_m5) AS total_m5,
    SUM(expected_amount_m25) AS total_m25
FROM ops.v_scout_daily_expected_base
GROUP BY scout_id
ORDER BY total_expected_amount DESC
LIMIT 20;

