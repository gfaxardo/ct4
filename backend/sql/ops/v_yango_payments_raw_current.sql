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
        25 AS milestone_value,
        COALESCE(np.trip_25, false) AS is_paid,
        'trip_25' AS paid_flag_source
    FROM normalized_payments np
    WHERE np.trip_25 IS NOT NULL
),
name_matching AS (
    -- Matching por nombre normalizado (solo si es único)
    SELECT 
        em.*,
        dni.driver_id,
        dni.person_key,
        COUNT(*) OVER (PARTITION BY em.driver_name_normalized) AS name_match_count
    FROM expanded_milestones em
    LEFT JOIN ops.v_driver_name_index dni
        ON dni.full_name_normalized = em.driver_name_normalized
),
matched_payments AS (
    SELECT 
        nm.*,
        CASE 
            WHEN nm.driver_id IS NOT NULL AND nm.name_match_count = 1 THEN 'driver_name_unique'
            WHEN nm.driver_id IS NOT NULL AND nm.name_match_count > 1 THEN 'none'  -- Múltiples matches, no confiable
            ELSE 'none'
        END AS match_rule,
        CASE 
            WHEN nm.driver_id IS NOT NULL AND nm.name_match_count = 1 THEN 'medium'
            ELSE 'unknown'
        END AS match_confidence
    FROM name_matching nm
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
    -- Solo incluir driver_id/person_key si el match es único
    CASE WHEN mp.name_match_count = 1 THEN mp.driver_id ELSE NULL END AS driver_id,
    CASE WHEN mp.name_match_count = 1 THEN mp.person_key ELSE NULL END AS person_key,
    mp.match_rule,
    mp.match_confidence,
    -- payment_key: hash estable para deduplicación
    MD5(mp.source_pk::text || mp.milestone_value::text || mp.driver_name_normalized) AS payment_key,
    -- state_hash: hash del estado para detectar cambios
    MD5(mp.is_paid::text) AS state_hash
FROM matched_payments mp;

COMMENT ON VIEW ops.v_yango_payments_raw_current IS 
'Vista que normaliza y expande pagos Yango desde public.module_ct_cabinet_payments. Expande cada fila en 3 filas (una por milestone: 1, 5, 25) basándose en los flags trip_1/trip_5/trip_25. Normaliza nombres de drivers y hace matching por nombre (solo si el match es único). Genera payment_key y state_hash para idempotencia en el ledger.';

COMMENT ON COLUMN ops.v_yango_payments_raw_current.payment_key IS 
'Hash estable para deduplicación: md5(source_pk || milestone_value || driver_name_normalized). Identifica de forma única un pago específico.';

COMMENT ON COLUMN ops.v_yango_payments_raw_current.state_hash IS 
'Hash del estado actual: md5(is_paid::text). Permite detectar cambios de estado para el mismo payment_key.';

