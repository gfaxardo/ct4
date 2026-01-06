-- Vista Dimensional de Scouts
-- Proporciona una vista normalizada de los scouts desde public.module_ct_scouts_list
-- Columnas:
--   - scout_id: ID único del scout (desde id)
--   - scout_name_normalized: Nombre normalizado (lowercase, sin caracteres especiales)
--   - raw_name: Nombre original sin modificar
--   - is_active: Estado activo del scout (si existe)

CREATE OR REPLACE VIEW ops.v_dim_scouts AS
SELECT DISTINCT
    id AS scout_id,
    LOWER(TRIM(REGEXP_REPLACE(name, '[^a-zA-Z0-9\s]', '', 'g'))) AS scout_name_normalized,
    name AS raw_name,
    is_active
FROM public.module_ct_scouts_list
WHERE id IS NOT NULL;

























