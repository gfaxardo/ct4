-- ============================================================================
-- VERIFICACIÓN DE VISTAS DE ATRIBUCIÓN DE SCOUTS
-- ============================================================================
-- Ejecutar después de crear las vistas para validar que funcionan correctamente
-- ============================================================================

-- Verificar que las vistas existen
SELECT 
    schemaname,
    viewname,
    viewowner
FROM pg_views
WHERE schemaname = 'ops'
    AND viewname IN ('v_scout_attribution_raw', 'v_scout_attribution', 'v_scout_attribution_conflicts')
ORDER BY viewname;

-- ============================================================================
-- VERIFICACIÓN 1: Cobertura de v_scout_attribution_raw
-- ============================================================================

SELECT 
    'v_scout_attribution_raw' AS view_name,
    COUNT(*) AS total_attributions,
    COUNT(DISTINCT person_key) AS distinct_persons,
    COUNT(DISTINCT driver_id) AS distinct_drivers,
    COUNT(DISTINCT scout_id) AS distinct_scouts,
    COUNT(*) FILTER (WHERE person_key IS NOT NULL) AS with_person_key,
    COUNT(*) FILTER (WHERE driver_id IS NOT NULL) AS with_driver_id,
    COUNT(*) FILTER (WHERE scout_id IS NOT NULL) AS with_scout_id
FROM ops.v_scout_attribution_raw;

-- Distribución por source_table
SELECT 
    source_table,
    COUNT(*) AS attribution_count,
    COUNT(DISTINCT person_key) AS distinct_persons,
    COUNT(DISTINCT driver_id) AS distinct_drivers,
    COUNT(DISTINCT scout_id) AS distinct_scouts
FROM ops.v_scout_attribution_raw
GROUP BY source_table
ORDER BY attribution_count DESC;

-- Distribución por acquisition_method
SELECT 
    acquisition_method,
    COUNT(*) AS attribution_count,
    COUNT(DISTINCT person_key) AS distinct_persons,
    COUNT(DISTINCT scout_id) AS distinct_scouts
FROM ops.v_scout_attribution_raw
GROUP BY acquisition_method
ORDER BY attribution_count DESC;

-- ============================================================================
-- VERIFICACIÓN 2: Cobertura de v_scout_attribution (1 fila por person_key/driver_id)
-- ============================================================================

SELECT 
    'v_scout_attribution' AS view_name,
    COUNT(*) AS total_attributions,
    COUNT(DISTINCT person_key) AS distinct_persons,
    COUNT(DISTINCT driver_id) AS distinct_drivers,
    COUNT(DISTINCT scout_id) AS distinct_scouts,
    COUNT(*) FILTER (WHERE person_key IS NOT NULL) AS with_person_key,
    COUNT(*) FILTER (WHERE driver_id IS NOT NULL) AS with_driver_id,
    COUNT(*) FILTER (WHERE scout_id IS NOT NULL) AS with_scout_id
FROM ops.v_scout_attribution;

-- Verificar que no hay duplicados por person_key
SELECT 
    'Verificación de duplicados por person_key' AS check_name,
    COUNT(*) AS total_rows,
    COUNT(DISTINCT person_key) AS distinct_persons,
    COUNT(*) - COUNT(DISTINCT person_key) AS duplicate_count
FROM ops.v_scout_attribution
WHERE person_key IS NOT NULL;

-- Verificar que no hay duplicados por driver_id
SELECT 
    'Verificación de duplicados por driver_id' AS check_name,
    COUNT(*) AS total_rows,
    COUNT(DISTINCT driver_id) AS distinct_drivers,
    COUNT(*) - COUNT(DISTINCT driver_id) AS duplicate_count
FROM ops.v_scout_attribution
WHERE driver_id IS NOT NULL;

-- Distribución por source_table (vista final)
SELECT 
    source_table,
    COUNT(*) AS attribution_count,
    COUNT(DISTINCT person_key) AS distinct_persons,
    COUNT(DISTINCT driver_id) AS distinct_drivers,
    COUNT(DISTINCT scout_id) AS distinct_scouts
FROM ops.v_scout_attribution
GROUP BY source_table
ORDER BY attribution_count DESC;

-- Top 20 scouts por número de atribuciones
SELECT 
    scout_id,
    COUNT(*) AS attribution_count,
    COUNT(DISTINCT person_key) AS distinct_persons,
    COUNT(DISTINCT driver_id) AS distinct_drivers
FROM ops.v_scout_attribution
WHERE scout_id IS NOT NULL
GROUP BY scout_id
ORDER BY attribution_count DESC
LIMIT 20;

-- ============================================================================
-- VERIFICACIÓN 3: Conflictos detectados
-- ============================================================================

SELECT 
    'v_scout_attribution_conflicts' AS view_name,
    COUNT(*) AS total_conflicts,
    COUNT(DISTINCT driver_identifier) AS distinct_conflicted_entities
FROM ops.v_scout_attribution_conflicts;

-- Muestra de conflictos (top 10)
SELECT 
    driver_identifier,
    person_key,
    driver_id,
    distinct_scout_count,
    scout_ids,
    source_tables,
    acquisition_methods,
    first_attribution,
    last_attribution,
    total_attributions
FROM ops.v_scout_attribution_conflicts
ORDER BY distinct_scout_count DESC, total_attributions DESC
LIMIT 10;

-- ============================================================================
-- VERIFICACIÓN 4: Comparación con vista existente v_attribution_canonical
-- ============================================================================

-- Verificar si existe la vista
SELECT 
    CASE 
        WHEN EXISTS (
            SELECT 1 FROM pg_views 
            WHERE schemaname = 'ops' AND viewname = 'v_attribution_canonical'
        ) THEN 'EXISTS'
        ELSE 'NOT_EXISTS'
    END AS v_attribution_canonical_status;

-- Comparar cobertura (si existe)
SELECT 
    'Comparación de cobertura' AS comparison,
    (SELECT COUNT(DISTINCT person_key) FROM ops.v_attribution_canonical WHERE acquisition_scout_id IS NOT NULL) AS v_attribution_canonical_count,
    (SELECT COUNT(DISTINCT person_key) FROM ops.v_scout_attribution WHERE person_key IS NOT NULL AND scout_id IS NOT NULL) AS v_scout_attribution_count
WHERE EXISTS (
    SELECT 1 FROM pg_views 
    WHERE schemaname = 'ops' AND viewname = 'v_attribution_canonical'
);

-- ============================================================================
-- VERIFICACIÓN 5: Muestras de datos
-- ============================================================================

-- Muestra de v_scout_attribution_raw (10 filas)
SELECT 
    person_key,
    driver_id,
    driver_license,
    driver_phone,
    scout_id,
    acquisition_method,
    source_table,
    attribution_date
FROM ops.v_scout_attribution_raw
WHERE scout_id IS NOT NULL
ORDER BY attribution_date DESC NULLS LAST, created_at DESC
LIMIT 10;

-- Muestra de v_scout_attribution (10 filas)
SELECT 
    driver_identifier,
    person_key,
    driver_id,
    driver_license,
    driver_phone,
    scout_id,
    acquisition_method,
    source_table,
    attribution_date
FROM ops.v_scout_attribution
WHERE scout_id IS NOT NULL
ORDER BY attribution_date DESC NULLS LAST, created_at DESC
LIMIT 10;

-- ============================================================================
-- RESUMEN FINAL
-- ============================================================================

SELECT 
    'RESUMEN FINAL' AS summary,
    (SELECT COUNT(*) FROM ops.v_scout_attribution_raw) AS total_raw_attributions,
    (SELECT COUNT(DISTINCT person_key) FROM ops.v_scout_attribution WHERE person_key IS NOT NULL) AS distinct_persons_with_scout,
    (SELECT COUNT(DISTINCT driver_id) FROM ops.v_scout_attribution WHERE driver_id IS NOT NULL) AS distinct_drivers_with_scout,
    (SELECT COUNT(DISTINCT scout_id) FROM ops.v_scout_attribution WHERE scout_id IS NOT NULL) AS distinct_scouts,
    (SELECT COUNT(*) FROM ops.v_scout_attribution_conflicts) AS total_conflicts;



