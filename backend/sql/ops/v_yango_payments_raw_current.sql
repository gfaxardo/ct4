-- ============================================================================
-- Vista: Pagos Yango Raw Normalizados (Estado Actual)
-- ============================================================================
-- Lee public.module_ct_cabinet_payments y normaliza/expande los datos.
-- 
-- Expande cada fila en 3 filas (una por milestone: 1, 5, 25) basándose en
-- los flags trip_1, trip_5, trip_25.
--
-- Normaliza el nombre del driver y hace matching por nombre normalizado
-- (solo si el match es único).
--
-- Genera payment_key y state_hash para idempotencia en el ledger.
-- ============================================================================

CREATE OR REPLACE VIEW ops.v_yango_payments_raw_current AS
WITH raw_payments AS (
    SELECT 
        id AS source_pk,
        date AS pay_date,
        time AS pay_time,
        scout_id,
        driver AS raw_driver_name,
        -- Identidad desde fuente upstream (PRIORIDAD)
        driver_id AS driver_id_from_source,
        person_key AS person_key_from_source,
        trip_1,
        trip_5,
        trip_25,
        created_at,
        updated_at
    FROM public.module_ct_cabinet_payments
    WHERE driver IS NOT NULL
        AND TRIM(driver) != ''
),
normalized_payments AS (
    SELECT 
        rp.*,
        -- Normalización de nombre: misma lógica que normalize_name() en Python
        UPPER(
            TRIM(
                REGEXP_REPLACE(
                    REGEXP_REPLACE(
                        REGEXP_REPLACE(
                            REGEXP_REPLACE(
                                REGEXP_REPLACE(
                                    REGEXP_REPLACE(
                                        REGEXP_REPLACE(
                                            rp.raw_driver_name,
                                            '[ÀÁÂÃÄÅ]', 'A', 'g'
                                        ),
                                        '[ÈÉÊË]', 'E', 'g'
                                    ),
                                    '[ÌÍÎÏ]', 'I', 'g'
                                ),
                                '[ÒÓÔÕÖ]', 'O', 'g'
                            ),
                            '[ÙÚÛÜ]', 'U', 'g'
                        ),
                        '[Ñ]', 'N', 'g'
                    ),
                    '[Ç]', 'C', 'g'
                )
            )
        ) AS driver_name_normalized
    FROM raw_payments rp
),
expanded_milestones AS (
    -- Expander cada fila en 3 filas (una por milestone)
    SELECT 
        np.source_pk,
        np.pay_date,
        np.pay_time,
        np.scout_id,
        np.raw_driver_name,
        np.driver_name_normalized,
        np.driver_id_from_source,
        np.person_key_from_source,
        1 AS milestone_value,
        COALESCE(np.trip_1, false) AS is_paid,
        'trip_1' AS paid_flag_source
    FROM normalized_payments np
    WHERE np.trip_1 IS NOT NULL
    
    UNION ALL
    
    SELECT 
        np.source_pk,
        np.pay_date,
        np.pay_time,
        np.scout_id,
        np.raw_driver_name,
        np.driver_name_normalized,
        np.driver_id_from_source,
        np.person_key_from_source,
        5 AS milestone_value,
        COALESCE(np.trip_5, false) AS is_paid,
        'trip_5' AS paid_flag_source
    FROM normalized_payments np
    WHERE np.trip_5 IS NOT NULL
    
    UNION ALL
    
    SELECT 
        np.source_pk,
        np.pay_date,
        np.pay_time,
        np.scout_id,
        np.raw_driver_name,
        np.driver_name_normalized,
        np.driver_id_from_source,
        np.person_key_from_source,
        25 AS milestone_value,
        COALESCE(np.trip_25, false) AS is_paid,
        'trip_25' AS paid_flag_source
    FROM normalized_payments np
    WHERE np.trip_25 IS NOT NULL
),
-- Fallback informativo: matching por nombre con dos llaves (SOLO si no hay identidad upstream)
name_matching_fallback AS (
    SELECT 
        em.*,
        -- Normalizar nombre del pago
        ops.normalize_name_basic(em.raw_driver_name) AS name_norm_basic,
        ops.normalize_name_tokens_sorted(em.raw_driver_name) AS name_norm_tokens_sorted,
        -- Match por full_norm básico
        dni_full.driver_id AS driver_id_by_full_norm,
        dni_full.person_key AS person_key_by_full_norm,
        COUNT(*) OVER (PARTITION BY ops.normalize_name_basic(em.raw_driver_name)) AS match_count_full_norm,
        -- Match por tokens ordenados
        dni_tokens.driver_id AS driver_id_by_tokens,
        dni_tokens.person_key AS person_key_by_tokens,
        COUNT(*) OVER (PARTITION BY ops.normalize_name_tokens_sorted(em.raw_driver_name)) AS match_count_tokens
    FROM expanded_milestones em
    LEFT JOIN ops.v_driver_name_index_extended dni_full
        ON dni_full.full_name_normalized_basic = ops.normalize_name_basic(em.raw_driver_name)
    LEFT JOIN ops.v_driver_name_index_extended dni_tokens
        ON dni_tokens.full_name_normalized_tokens_sorted = ops.normalize_name_tokens_sorted(em.raw_driver_name)
        AND ops.normalize_name_tokens_sorted(em.raw_driver_name) IS NOT NULL  -- Solo si tokens_sorted no es NULL
    WHERE em.driver_id_from_source IS NULL
        AND em.person_key_from_source IS NULL
),
-- Determinar match final por fallback (con prioridad y seguridad)
matched_fallback AS (
    SELECT 
        nmf.*,
        -- Prioridad: full_norm único primero, luego tokens_sorted único
        -- Solo asignar si el match es ÚNICO (count=1)
        CASE 
            WHEN nmf.match_count_full_norm = 1 AND nmf.driver_id_by_full_norm IS NOT NULL THEN nmf.driver_id_by_full_norm
            WHEN nmf.match_count_tokens = 1 AND nmf.driver_id_by_tokens IS NOT NULL THEN nmf.driver_id_by_tokens
            ELSE NULL
        END AS driver_id_fallback,
        CASE 
            WHEN nmf.match_count_full_norm = 1 AND nmf.person_key_by_full_norm IS NOT NULL THEN nmf.person_key_by_full_norm
            WHEN nmf.match_count_tokens = 1 AND nmf.person_key_by_tokens IS NOT NULL THEN nmf.person_key_by_tokens
            ELSE NULL
        END AS person_key_fallback,
        -- match_rule detallado
        CASE 
            WHEN nmf.match_count_full_norm = 1 AND nmf.driver_id_by_full_norm IS NOT NULL THEN 'name_full_unique'
            WHEN nmf.match_count_tokens = 1 AND nmf.driver_id_by_tokens IS NOT NULL THEN 'name_tokens_unique'
            WHEN (nmf.match_count_full_norm > 1 OR nmf.match_count_tokens > 1) 
                 AND (nmf.driver_id_by_full_norm IS NOT NULL OR nmf.driver_id_by_tokens IS NOT NULL) THEN 'ambiguous'
            ELSE 'no_match'
        END AS match_rule_fallback,
        -- match_confidence
        CASE 
            WHEN nmf.match_count_full_norm = 1 AND nmf.driver_id_by_full_norm IS NOT NULL THEN 'medium'
            WHEN nmf.match_count_tokens = 1 AND nmf.driver_id_by_tokens IS NOT NULL THEN 'medium'
            WHEN (nmf.match_count_full_norm > 1 OR nmf.match_count_tokens > 1) THEN 'low'
            ELSE 'unknown'
        END AS match_confidence_fallback
    FROM name_matching_fallback nmf
),
matched_payments AS (
    SELECT 
        em.*,
        mf.driver_id_fallback,
        mf.person_key_fallback,
        mf.match_rule_fallback,
        mf.match_confidence_fallback,
        -- Usar identidad upstream si existe, sino usar fallback
        COALESCE(em.driver_id_from_source, mf.driver_id_fallback) AS driver_id,
        COALESCE(em.person_key_from_source, mf.person_key_fallback) AS person_key,
        -- match_rule: indicar source
        CASE 
            WHEN em.driver_id_from_source IS NOT NULL OR em.person_key_from_source IS NOT NULL THEN 'source_upstream'
            ELSE COALESCE(mf.match_rule_fallback, 'no_match')
        END AS match_rule,
        -- match_confidence: upstream es high, fallback es medium/low/unknown
        CASE 
            WHEN em.driver_id_from_source IS NOT NULL OR em.person_key_from_source IS NOT NULL THEN 'high'
            ELSE COALESCE(mf.match_confidence_fallback, 'unknown')
        END AS match_confidence
    FROM expanded_milestones em
    LEFT JOIN matched_fallback mf
        ON em.source_pk = mf.source_pk
        AND em.milestone_value = mf.milestone_value
)
SELECT 
    mp.source_pk,
    mp.pay_date,
    mp.pay_time,
    mp.scout_id,
    mp.raw_driver_name,
    mp.driver_name_normalized,
    'trips' AS milestone_type,
    mp.milestone_value,
    mp.is_paid,
    mp.paid_flag_source,
    -- driver_id/person_key: usar upstream si existe, sino fallback por nombre (solo si único)
    mp.driver_id,
    mp.person_key,
    mp.match_rule,
    mp.match_confidence,
    -- payment_key: hash estable para deduplicación
    MD5(mp.source_pk::text || mp.milestone_value::text || mp.driver_name_normalized) AS payment_key,
    -- state_hash: hash del estado para detectar cambios
    MD5(mp.is_paid::text) AS state_hash
FROM matched_payments mp;

COMMENT ON VIEW ops.v_yango_payments_raw_current IS 
'Vista que normaliza y expande pagos Yango desde public.module_ct_cabinet_payments. Expande cada fila en 3 filas (una por milestone: 1, 5, 25) basándose en los flags trip_1/trip_5/trip_25. PRIORIDAD: Usa driver_id/person_key desde module_ct_cabinet_payments si existen. FALLBACK INFORMATIVO: Matching por nombre normalizado (solo si match es único) cuando las columnas upstream están NULL. Genera payment_key y state_hash para idempotencia en el ledger.';

COMMENT ON COLUMN ops.v_yango_payments_raw_current.payment_key IS 
'Hash estable para deduplicación: md5(source_pk || milestone_value || driver_name_normalized). Identifica de forma única un pago específico.';

COMMENT ON COLUMN ops.v_yango_payments_raw_current.state_hash IS 
'Hash del estado actual: md5(is_paid::text). Permite detectar cambios de estado para el mismo payment_key.';

