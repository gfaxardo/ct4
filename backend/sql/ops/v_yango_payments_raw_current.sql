-- ============================================================================
-- Vista: Pagos Yango Raw Normalizados (Estado Actual)
-- ============================================================================
-- Lee public.module_ct_cabinet_payments y normaliza/expande los datos.
-- 
-- Expande cada fila en 3 filas (una por milestone: 1, 5, 25) basándose en
-- los flags trip_1, trip_5, trip_25.
--
-- Normaliza el nombre del driver y hace matching por name_key
-- (solo si el match es único - exactamente 1 candidato).
--
-- Genera payment_key y state_hash para idempotencia en el ledger.
-- ============================================================================

-- Función auxiliar: ops.person_name_key
-- Crea una clave determinística a partir de un nombre normalizado

-- Primero eliminar la vista (que depende de la función)
DROP VIEW IF EXISTS ops.v_yango_payments_raw_current CASCADE;

-- Luego eliminar la función
DROP FUNCTION IF EXISTS ops.person_name_key(TEXT);

-- Crear la función
CREATE FUNCTION ops.person_name_key(p_name TEXT)
RETURNS TEXT
LANGUAGE sql
IMMUTABLE
AS $$
  SELECT CASE
    WHEN p_name IS NULL OR btrim(p_name) = '' THEN NULL
    ELSE COALESCE(
      ops.normalize_person_tokens_sorted(p_name),
      ops.normalize_person_name(p_name)
    )
  END;
$$;

COMMENT ON FUNCTION ops.person_name_key(text) IS
'Name key determinístico: usa tokens sorted (order-invariant) y fallback a normalize_person_name.';

CREATE VIEW ops.v_yango_payments_raw_current AS
WITH raw_payments AS (
    SELECT 
        id AS source_pk,
        date AS pay_date,
        "time" AS pay_time,
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
        -- Normalización de nombre: MAYÚSCULAS quitando tildes
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
    -- Expander cada fila en 3 filas (una por milestone: 1, 5, 25)
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
-- Agregar driver_name_key (name_key) calculado con ops.person_name_key
payments AS (
    SELECT
        p.*,
        ops.person_name_key(p.driver_name_normalized) AS driver_name_key
    FROM expanded_milestones p
),
-- Índice de drivers con name_key
driver_idx AS (
    SELECT
        d.driver_id,
        d.person_key,
        d.full_name_normalized,
        ops.person_name_key(d.full_name_normalized) AS full_name_key
    FROM ops.v_driver_name_index d
),
-- Contar candidatos por name_key
key_counts AS (
    SELECT
        full_name_key,
        COUNT(*) AS candidates
    FROM driver_idx
    GROUP BY 1
),
-- Match único: solo cuando name_key tiene exactamente 1 candidato
unique_match AS (
    SELECT
        p.source_pk,
        p.milestone_value,
        d.driver_id,
        d.person_key
    FROM payments p
    JOIN key_counts kc
        ON kc.full_name_key = p.driver_name_key
       AND kc.candidates = 1
    JOIN driver_idx d
        ON d.full_name_key = p.driver_name_key
    WHERE p.driver_name_key IS NOT NULL
),
-- Combinar matches únicos
matched_payments AS (
    SELECT 
        p.*,
        -- Usar match único por name_key
        um.driver_id,
        um.person_key,
        -- Indicador de match único por name_key
        um.driver_id IS NOT NULL AS has_name_key_match
    FROM payments p
    LEFT JOIN unique_match um
        ON um.source_pk = p.source_pk
        AND um.milestone_value = p.milestone_value
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
    -- driver_id/person_key: solo si hay match único por name_key
    mp.driver_id::TEXT AS driver_id,
    mp.person_key::UUID AS person_key,
    -- match_rule: solo 'driver_name_unique' o 'none'
    CASE
        -- Si hay match único por name_key
        WHEN mp.has_name_key_match = true AND mp.driver_id IS NOT NULL THEN 'driver_name_unique'
        -- Si no hay match o hay ambigüedad
        ELSE 'none'
    END AS match_rule,
    -- match_confidence: solo 'medium' o 'unknown'
    CASE
        -- Si hay match único por name_key
        WHEN mp.has_name_key_match = true AND mp.driver_id IS NOT NULL THEN 'medium'
        -- Si no hay match o hay ambigüedad
        ELSE 'unknown'
    END AS match_confidence,
    -- payment_key: hash estable para deduplicación
    MD5(mp.source_pk::text || mp.milestone_value::text || COALESCE(mp.driver_name_normalized, '')) AS payment_key,
    -- state_hash: hash del estado para detectar cambios
    MD5(mp.is_paid::text) AS state_hash
FROM matched_payments mp;

COMMENT ON VIEW ops.v_yango_payments_raw_current IS 
'Vista que normaliza y expande pagos Yango desde public.module_ct_cabinet_payments. Expande cada fila en 3 filas (una por milestone: 1, 5, 25) basándose en los flags trip_1/trip_5/trip_25. GARANTIZA: Devuelve TODAS las filas expandidas, incluso si driver_id/person_key son NULL. MATCHING: Usa name_key (ops.person_name_key) para matching contra v_driver_name_index. SOLO enriquece cuando el name_key tiene exactamente 1 candidato. match_rule solo usa ''driver_name_unique'' o ''none''. match_confidence solo usa ''medium'' o ''unknown''. Genera payment_key y state_hash para idempotencia en el ledger.';

COMMENT ON COLUMN ops.v_yango_payments_raw_current.source_pk IS 
'ID del registro fuente en public.module_ct_cabinet_payments (columna id).';

COMMENT ON COLUMN ops.v_yango_payments_raw_current.pay_date IS 
'Fecha del pago desde public.module_ct_cabinet_payments (columna date).';

COMMENT ON COLUMN ops.v_yango_payments_raw_current.pay_time IS 
'Hora del pago desde public.module_ct_cabinet_payments (columna time).';

COMMENT ON COLUMN ops.v_yango_payments_raw_current.raw_driver_name IS 
'Nombre del driver en formato crudo desde public.module_ct_cabinet_payments (columna driver).';

COMMENT ON COLUMN ops.v_yango_payments_raw_current.driver_name_normalized IS 
'Nombre del driver normalizado: MAYÚSCULAS, sin tildes, espacios colapsados.';

COMMENT ON COLUMN ops.v_yango_payments_raw_current.milestone_type IS 
'Tipo de milestone: siempre ''trips'' para pagos Yango.';

COMMENT ON COLUMN ops.v_yango_payments_raw_current.milestone_value IS 
'Valor del milestone: 1, 5 o 25 (expandido desde flags trip_1, trip_5, trip_25).';

COMMENT ON COLUMN ops.v_yango_payments_raw_current.is_paid IS 
'Indicador de pago: true si el flag correspondiente (trip_1/trip_5/trip_25) es true.';

COMMENT ON COLUMN ops.v_yango_payments_raw_current.paid_flag_source IS 
'Fuente del flag de pago: ''trip_1'', ''trip_5'' o ''trip_25''.';

COMMENT ON COLUMN ops.v_yango_payments_raw_current.driver_id IS 
'ID del driver (TEXT). Solo poblado si hay match único por name_key.';

COMMENT ON COLUMN ops.v_yango_payments_raw_current.person_key IS 
'Clave canónica de la persona (UUID). Solo poblado si hay match único por name_key.';

COMMENT ON COLUMN ops.v_yango_payments_raw_current.match_rule IS 
'Regla de matching: ''driver_name_unique'' (match único por name_key), ''none'' (sin match o ambigüedad). Cumple CHECK constraint del ledger.';

COMMENT ON COLUMN ops.v_yango_payments_raw_current.match_confidence IS 
'Nivel de confianza: ''medium'' (match único por name_key), ''unknown'' (sin match o ambigüedad). Cumple CHECK constraint del ledger.';

COMMENT ON COLUMN ops.v_yango_payments_raw_current.payment_key IS 
'Hash estable para deduplicación: md5(source_pk || milestone_value || coalesce(driver_name_normalized, '''')). Identifica de forma única un pago específico.';

COMMENT ON COLUMN ops.v_yango_payments_raw_current.state_hash IS 
'Hash del estado actual: md5(is_paid::text). Permite detectar cambios de estado para el mismo payment_key.';
