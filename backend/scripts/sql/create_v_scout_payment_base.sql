-- ============================================================================
-- VISTA: ops.v_scout_payment_base
-- ============================================================================
-- Propósito: Vista FINAL para liquidación diaria de scouts
-- Incluye: person_key, driver_id, scout_id canónico, origin_tag, milestones, amounts
-- NO paga, solo declara verdad operativa
-- Ejecución: Idempotente (DROP + CREATE)
-- ============================================================================

DROP VIEW IF EXISTS ops.v_scout_payment_base CASCADE;

CREATE VIEW ops.v_scout_payment_base AS
WITH scout_attribution AS (
    SELECT 
        sa.person_key,
        sa.driver_id,
        sa.driver_license,
        sa.driver_phone,
        sa.scout_id,
        sa.acquisition_method,
        sa.source_table,
        sa.source_pk,
        sa.attribution_date,
        sa.created_at,
        sa.priority,
        CASE 
            WHEN sa.source_table = 'public.module_ct_migrations' THEN 'migration'
            WHEN sa.source_table = 'public.module_ct_scouting_daily' THEN 'scout_registration'
            ELSE NULL
        END AS origin_tag
    FROM ops.v_scout_attribution sa
)
-- Vista simplificada: solo declara verdad operativa de scout
-- Milestones y amounts se calculan en otra capa según reglas de negocio
SELECT 
    sa.person_key,
    sa.driver_id,
    sa.scout_id,
    sa.origin_tag,
    sa.source_table,
    sa.source_pk,
    sa.attribution_date,
    0::INTEGER AS milestone_reached,
    NULL::DATE AS milestone_date,
    false AS eligible_7d,
    0.00::NUMERIC(10,2) AS amount_payable,
    -- Payment status basado solo en scout
    CASE 
        WHEN sa.scout_id IS NULL THEN 'BLOCKED'
        WHEN EXISTS (SELECT 1 FROM ops.v_scout_attribution_conflicts sac WHERE sac.person_key = sa.person_key) THEN 'BLOCKED'
        WHEN NOT EXISTS (SELECT 1 FROM canon.identity_links il WHERE il.person_key = sa.person_key) THEN 'BLOCKED'
        ELSE 'PENDING'  -- Pending porque milestones se calculan aparte
    END AS payment_status,
    -- Block reason
    CASE 
        WHEN sa.scout_id IS NULL THEN 'NO_SCOUT'
        WHEN EXISTS (SELECT 1 FROM ops.v_scout_attribution_conflicts sac WHERE sac.person_key = sa.person_key) THEN 'CONFLICT'
        WHEN NOT EXISTS (SELECT 1 FROM canon.identity_links il WHERE il.person_key = sa.person_key) THEN 'NO_IDENTITY'
        ELSE NULL
    END AS block_reason
FROM scout_attribution sa
WHERE sa.scout_id IS NOT NULL;

COMMENT ON VIEW ops.v_scout_payment_base IS 
'Vista FINAL para liquidación diaria de scouts. Declara verdad operativa: person_key, driver_id, scout_id canónico, milestones, amounts, payment_status. NO ejecuta pagos, solo informa elegibilidad.';
