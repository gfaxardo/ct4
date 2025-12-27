-- ============================================================================
-- Vista: Ledger Yango con Identidad Enriquecida (Matching por Nombre)
-- ============================================================================
-- Enriquece ops.v_yango_payments_ledger_latest con identidad usando matching
-- determinístico por nombre contra public.drivers.
--
-- Estrategia:
-- 1. Si driver_id ya existe en ledger (upstream) → identity_status='confirmed'
-- 2. Si driver_id es NULL → intentar matching por nombre:
--    A) Match por nombre completo normalizado (si único)
--    B) Match por tokens ordenados (si único, permite orden invertido)
--    C) Si ambos métodos matchean a drivers distintos → 'ambiguous'
--    D) Si count>1 en cualquier método → 'ambiguous'
--    E) Si no hay match → 'no_match'
--
-- Campos expuestos:
-- - driver_id_original: driver_id desde ledger (puede ser NULL)
-- - driver_id_enriched: driver_id derivado por matching (solo si único)
-- - driver_id_final: COALESCE(original, enriched)
-- - identity_status: 'confirmed' | 'enriched' | 'ambiguous' | 'no_match'
-- - match_rule: 'source_upstream' | 'name_full_unique' | 'name_tokens_unique' | 'ambiguous' | 'no_match'
-- - match_confidence: 'high' (confirmed) | 'medium' (enriched único) | 'low' (ambiguous/no_match)
-- - identity_enriched: boolean (true si fue enriquecido)
-- ============================================================================

DROP VIEW IF EXISTS ops.v_yango_payments_ledger_latest_enriched CASCADE;

CREATE VIEW ops.v_yango_payments_ledger_latest_enriched AS
WITH ledger_base AS (
    -- Base: último estado del ledger
    SELECT 
        id,
        latest_snapshot_at,
        source_table,
        source_pk,
        pay_date,
        pay_time,
        raw_driver_name,
        driver_name_normalized,
        milestone_type,
        milestone_value,
        is_paid,
        paid_flag_source,
        driver_id AS driver_id_original,
        person_key AS person_key_original,
        payment_key,
        state_hash,
        created_at
    FROM ops.v_yango_payments_ledger_latest
),
-- Normalizar nombres del ledger
ledger_normalized AS (
    SELECT 
        lb.*,
        ops.normalize_name_basic(lb.raw_driver_name) AS ledger_full_norm,
        ops.normalize_name_tokens_sorted(lb.raw_driver_name) AS ledger_tokens_sorted
    FROM ledger_base lb
),
-- Normalizar nombres de drivers desde public.drivers
drivers_normalized AS (
    SELECT 
        d.driver_id,
        d.full_name AS driver_full_name_raw,
        ops.normalize_name_basic(COALESCE(d.full_name, 
            TRIM(COALESCE(d.first_name, '') || ' ' || 
                 COALESCE(d.middle_name, '') || ' ' || 
                 COALESCE(d.last_name, '')))) AS driver_full_norm,
        ops.normalize_name_tokens_sorted(COALESCE(d.full_name,
            TRIM(COALESCE(d.first_name, '') || ' ' || 
                 COALESCE(d.middle_name, '') || ' ' || 
                 COALESCE(d.last_name, '')))) AS driver_tokens_sorted
    FROM public.drivers d
    WHERE d.driver_id IS NOT NULL
        AND (d.full_name IS NOT NULL 
             OR d.first_name IS NOT NULL 
             OR d.last_name IS NOT NULL)
),
-- Matching por nombre completo normalizado (solo cuando driver_id_original es NULL)
match_full_norm AS (
    SELECT 
        ln.*,
        dn_full.driver_id AS driver_id_by_full_norm,
        COUNT(*) OVER (PARTITION BY ln.ledger_full_norm) AS match_count_full_norm
    FROM ledger_normalized ln
    LEFT JOIN drivers_normalized dn_full
        ON dn_full.driver_full_norm = ln.ledger_full_norm
        AND ln.ledger_full_norm IS NOT NULL
        AND ln.driver_id_original IS NULL  -- Solo cuando no hay identidad upstream
),
-- Matching por tokens ordenados (solo cuando driver_id_original es NULL)
match_tokens AS (
    SELECT 
        mfn.*,
        dn_tokens.driver_id AS driver_id_by_tokens,
        COUNT(*) OVER (PARTITION BY mfn.ledger_tokens_sorted) AS match_count_tokens
    FROM match_full_norm mfn
    LEFT JOIN drivers_normalized dn_tokens
        ON dn_tokens.driver_tokens_sorted = mfn.ledger_tokens_sorted
        AND mfn.ledger_tokens_sorted IS NOT NULL
        AND mfn.driver_id_original IS NULL  -- Solo cuando no hay identidad upstream
),
-- Determinar match final (con prioridad y validación de unicidad)
match_final AS (
    SELECT 
        mt.*,
        -- Prioridad: full_norm único primero, luego tokens_sorted único
        CASE 
            WHEN mt.driver_id_original IS NOT NULL THEN NULL  -- Ya tiene identidad upstream
            WHEN mt.match_count_full_norm = 1 AND mt.driver_id_by_full_norm IS NOT NULL THEN mt.driver_id_by_full_norm
            WHEN mt.match_count_tokens = 1 AND mt.driver_id_by_tokens IS NOT NULL THEN mt.driver_id_by_tokens
            ELSE NULL
        END AS driver_id_enriched,
        -- match_rule
        CASE 
            WHEN mt.driver_id_original IS NOT NULL THEN 'source_upstream'
            WHEN mt.match_count_full_norm = 1 AND mt.driver_id_by_full_norm IS NOT NULL THEN 'name_full_unique'
            WHEN mt.match_count_tokens = 1 AND mt.driver_id_by_tokens IS NOT NULL THEN 'name_tokens_unique'
            WHEN (mt.match_count_full_norm > 1 OR mt.match_count_tokens > 1)
                 AND (mt.driver_id_by_full_norm IS NOT NULL OR mt.driver_id_by_tokens IS NOT NULL)
                 -- Verificar si ambos métodos matchean al mismo driver o a drivers distintos
                 AND NOT (mt.match_count_full_norm = 1 AND mt.match_count_tokens = 1 
                          AND mt.driver_id_by_full_norm = mt.driver_id_by_tokens)
            THEN 'ambiguous'
            ELSE 'no_match'
        END AS match_rule,
        -- match_confidence
        CASE 
            WHEN mt.driver_id_original IS NOT NULL THEN 'high'
            WHEN (mt.match_count_full_norm = 1 AND mt.driver_id_by_full_norm IS NOT NULL)
                 OR (mt.match_count_tokens = 1 AND mt.driver_id_by_tokens IS NOT NULL) THEN 'medium'
            ELSE 'low'
        END AS match_confidence
    FROM match_tokens mt
)
SELECT 
    mf.id,
    mf.latest_snapshot_at,
    mf.source_table,
    mf.source_pk,
    mf.pay_date,
    mf.pay_time,
    mf.raw_driver_name,
    mf.driver_name_normalized,
    mf.milestone_type,
    mf.milestone_value,
    mf.is_paid,
    mf.paid_flag_source,
    -- Campos originales preservados para auditoría
    mf.driver_id_original,
    mf.person_key_original,
    -- Campos enriquecidos
    mf.driver_id_enriched,
    -- Campos finales
    COALESCE(mf.driver_id_original, mf.driver_id_enriched) AS driver_id_final,
    -- identity_status
    CASE 
        WHEN mf.driver_id_original IS NOT NULL THEN 'confirmed'
        WHEN mf.driver_id_enriched IS NOT NULL THEN 'enriched'
        WHEN mf.match_rule = 'ambiguous' THEN 'ambiguous'
        ELSE 'no_match'
    END AS identity_status,
    -- match_rule y match_confidence
    mf.match_rule,
    mf.match_confidence,
    -- Flag de enriquecimiento
    (mf.driver_id_original IS NULL AND mf.driver_id_enriched IS NOT NULL) AS identity_enriched,
    -- Campos de auditoría preservados
    mf.payment_key,
    mf.state_hash,
    mf.created_at
FROM match_final mf
ORDER BY mf.latest_snapshot_at DESC, mf.payment_key;

COMMENT ON VIEW ops.v_yango_payments_ledger_latest_enriched IS 
'Vista que enriquece ops.v_yango_payments_ledger_latest con identidad usando matching determinístico por nombre contra public.drivers. Usa dos llaves: nombre completo normalizado y tokens ordenados. Solo asigna identidad si el match es único (count=1).';

COMMENT ON COLUMN ops.v_yango_payments_ledger_latest_enriched.driver_id_original IS 
'Driver ID original desde ledger (puede ser NULL si no viene desde upstream).';

COMMENT ON COLUMN ops.v_yango_payments_ledger_latest_enriched.driver_id_enriched IS 
'Driver ID derivado por matching por nombre (solo si el match es único).';

COMMENT ON COLUMN ops.v_yango_payments_ledger_latest_enriched.driver_id_final IS 
'Driver ID final: COALESCE(driver_id_original, driver_id_enriched).';

COMMENT ON COLUMN ops.v_yango_payments_ledger_latest_enriched.identity_status IS 
'Estado de identidad: confirmed (desde upstream), enriched (derivado por nombre único), ambiguous (múltiples matches), no_match (sin match).';

COMMENT ON COLUMN ops.v_yango_payments_ledger_latest_enriched.match_rule IS 
'Regla de matching: source_upstream (desde upstream), name_full_unique (match único por nombre completo), name_tokens_unique (match único por tokens ordenados), ambiguous (múltiples matches), no_match (sin match).';

COMMENT ON COLUMN ops.v_yango_payments_ledger_latest_enriched.match_confidence IS 
'Confianza del match: high (confirmed desde upstream), medium (match único por nombre), low (ambiguous/no_match).';

COMMENT ON COLUMN ops.v_yango_payments_ledger_latest_enriched.identity_enriched IS 
'Flag que indica si la identidad fue enriquecida por matching por nombre (TRUE) o ya existía upstream (FALSE).';
