-- ============================================================================
-- Vista: Índice de Nombres de Drivers Normalizados
-- ============================================================================
-- Vista auxiliar para matching por nombre de driver.
-- Proporciona driver_id, person_key (via canon.identity_links), y nombres
-- normalizados para matching con pagos Yango.
-- ============================================================================

CREATE OR REPLACE VIEW ops.v_driver_name_index AS
WITH driver_names AS (
    SELECT 
        d.driver_id,
        d.full_name AS full_name_raw,
        -- Normalización de nombre: replicar lógica de normalize_name() en Python
        -- UPPER, trim, reemplazo acentos, remover caracteres especiales, normalizar espacios
        UPPER(
            TRIM(
                REGEXP_REPLACE(
                    REGEXP_REPLACE(
                        REGEXP_REPLACE(
                            REGEXP_REPLACE(
                                REGEXP_REPLACE(
                                    REGEXP_REPLACE(
                                        REGEXP_REPLACE(
                                            COALESCE(d.full_name, 
                                                TRIM(COALESCE(d.first_name, '') || ' ' || 
                                                     COALESCE(d.middle_name, '') || ' ' || 
                                                     COALESCE(d.last_name, ''))
                                            ),
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
        ) AS full_name_normalized
    FROM public.drivers d
    WHERE d.driver_id IS NOT NULL
        AND (
            d.full_name IS NOT NULL 
            OR (d.first_name IS NOT NULL OR d.last_name IS NOT NULL)
        )
),
driver_with_person_key AS (
    SELECT 
        dn.driver_id,
        dn.full_name_raw,
        dn.full_name_normalized,
        il.person_key
    FROM driver_names dn
    LEFT JOIN canon.identity_links il
        ON il.source_table = 'drivers'
        AND il.source_pk = dn.driver_id
)
SELECT 
    driver_id,
    person_key,
    full_name_raw,
    full_name_normalized
FROM driver_with_person_key
WHERE full_name_normalized IS NOT NULL
    AND TRIM(full_name_normalized) != '';

COMMENT ON VIEW ops.v_driver_name_index IS 
'Vista auxiliar para matching por nombre de driver. Proporciona driver_id, person_key (via canon.identity_links), y nombres normalizados usando la misma lógica que normalize_name() en Python. Solo incluye drivers con nombre normalizado válido.';

COMMENT ON COLUMN ops.v_driver_name_index.full_name_normalized IS 
'Nombre normalizado: UPPER, sin acentos (À→A, È→E, etc.), solo letras y espacios, espacios normalizados. Coincide con la normalización usada en el sistema de matching.';


















