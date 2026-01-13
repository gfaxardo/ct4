-- ============================================================================
-- Vista: Índice de Nombres de Drivers con Normalizaciones Extendidas
-- ============================================================================
-- Extiende ops.v_driver_name_index agregando normalizaciones con tokens ordenados
-- para permitir matching cuando el orden de nombres varía.
--
-- Agrega campos:
-- - full_name_normalized_basic: normalización básica (ya existe en v_driver_name_index)
-- - full_name_normalized_tokens_sorted: tokens ordenados alfabéticamente
-- ============================================================================

CREATE OR REPLACE VIEW ops.v_driver_name_index_extended AS
SELECT 
    dni.driver_id,
    dni.person_key,
    dni.full_name_raw,
    dni.full_name_normalized AS full_name_normalized_basic,
    ops.normalize_name_tokens_sorted(dni.full_name_raw) AS full_name_normalized_tokens_sorted
FROM ops.v_driver_name_index dni
WHERE dni.full_name_normalized IS NOT NULL
    AND TRIM(dni.full_name_normalized) != '';

COMMENT ON VIEW ops.v_driver_name_index_extended IS 
'Extensión de ops.v_driver_name_index que agrega normalización con tokens ordenados. Permite matching cuando el orden de nombres varía (ej: "Luis Fabio Quispe" vs "Quispe Luis Fabio").';

COMMENT ON COLUMN ops.v_driver_name_index_extended.full_name_normalized_basic IS 
'Normalización básica (mismo que full_name_normalized en v_driver_name_index): UPPER, sin tildes, espacios colapsados.';

COMMENT ON COLUMN ops.v_driver_name_index_extended.full_name_normalized_tokens_sorted IS 
'Normalización con tokens ordenados alfabéticamente: permite matching cuando el orden varía. Determinístico.';









