-- ============================================================================
-- Vista: ops.v_ct4_milestones_achieved_from_trips_eligible
-- ============================================================================
-- PROPÓSITO:
-- Vista que combina milestones ACHIEVED determinísticos (calculados desde viajes)
-- con el universo elegible CT4 (cabinet + fleet_migration). Filtra achieved
-- a solo drivers que son elegibles para recibir pagos.
--
-- ARQUITECTURA:
-- JOIN entre:
-- - ops.v_cabinet_milestones_achieved_from_trips: achieved determinístico desde summary_daily
-- - ops.v_ct4_eligible_drivers: universe elegible (cabinet + fleet_migration)
--
-- CAPA: C2 - Elegibilidad (ACHIEVED) - Versión Determinística + Filtro Elegible
-- ============================================================================
-- REGLAS:
-- 1. Achieved se calcula SOLO desde summary_daily (viajes reales)
-- 2. Se filtra SOLO a drivers elegibles (origin_tag IN ('cabinet', 'fleet_migration'))
-- 3. Read-only: NO corrige pasado, NO modifica pagos, NO modifica reconciliación
-- 4. Garantiza consistencia: si M5 achieved, M1 también está achieved
-- 5. Garantiza consistencia: si M25 achieved, M5 y M1 también están achieved
-- ============================================================================
-- FUENTES:
-- - Achieved: ops.v_cabinet_milestones_achieved_from_trips (summary_daily)
-- - Elegibilidad: ops.v_ct4_eligible_drivers (cabinet + fleet_migration)
-- ============================================================================
-- GRANO:
-- (driver_id, milestone_value) - 1 fila por milestone alcanzado por driver elegible
-- ============================================================================
-- USO:
-- - Consultar milestones achieved determinísticos solo para drivers elegibles
-- - Base para cálculos de pagos filtrados a elegibles
-- - Auditoría de consistencia (M5 sin M1, M25 sin M5/M1) - debe dar 0 filas
-- - Comparar con v_cabinet_milestones_achieved para detectar discrepancias
-- ============================================================================

CREATE OR REPLACE VIEW ops.v_ct4_milestones_achieved_from_trips_eligible AS
SELECT 
    e.origin_tag,
    e.person_key,
    e.identity_status,
    a.driver_id,
    a.milestone_value,
    a.achieved_flag,
    a.achieved_date,
    a.trips_at_achieved
FROM ops.v_cabinet_milestones_achieved_from_trips a
INNER JOIN ops.v_ct4_eligible_drivers e
    ON e.driver_id = a.driver_id
ORDER BY a.driver_id, a.milestone_value;

-- ============================================================================
-- Comentarios
-- ============================================================================
COMMENT ON VIEW ops.v_ct4_milestones_achieved_from_trips_eligible IS 
'Vista que combina milestones ACHIEVED determinísticos (calculados desde summary_daily viajes) con el universo elegible CT4 (cabinet + fleet_migration). Achieved se calcula SOLO desde summary_daily (viajes reales). Se filtra SOLO a drivers elegibles (cabinet + fleet_migration). Read-only: NO corrige pasado, NO modifica pagos, NO modifica reconciliación. Grano: (driver_id, milestone_value) - 1 fila por milestone alcanzado por driver elegible.';

COMMENT ON COLUMN ops.v_ct4_milestones_achieved_from_trips_eligible.origin_tag IS 
'Origen del driver: ''cabinet'' o ''fleet_migration''. Solo drivers elegibles aparecen en esta vista.';

COMMENT ON COLUMN ops.v_ct4_milestones_achieved_from_trips_eligible.person_key IS 
'Person key del conductor (identidad canónica). Puede ser NULL si el driver no tiene identidad confirmada aún.';

COMMENT ON COLUMN ops.v_ct4_milestones_achieved_from_trips_eligible.identity_status IS 
'Estado de identidad: ''confirmed'' (upstream), ''enriched'' (matching único), ''ambiguous'' (sin match único), ''no_match'' (sin datos), o NULL.';

COMMENT ON COLUMN ops.v_ct4_milestones_achieved_from_trips_eligible.driver_id IS 
'ID del conductor que alcanzó el milestone.';

COMMENT ON COLUMN ops.v_ct4_milestones_achieved_from_trips_eligible.milestone_value IS 
'Valor del milestone alcanzado (1, 5, o 25).';

COMMENT ON COLUMN ops.v_ct4_milestones_achieved_from_trips_eligible.achieved_flag IS 
'Flag indicando si se alcanzó el milestone (siempre true en esta vista).';

COMMENT ON COLUMN ops.v_ct4_milestones_achieved_from_trips_eligible.achieved_date IS 
'Primer día en que trips acumulados >= milestone_value según summary_daily.';

COMMENT ON COLUMN ops.v_ct4_milestones_achieved_from_trips_eligible.trips_at_achieved IS 
'Cantidad de trips acumulados en achieved_date (puede ser >= milestone_value si se alcanza en un día con múltiples viajes).';

-- ============================================================================
-- Queries de Validación (comentados para referencia)
-- ============================================================================
/*
-- 1. Conteo por origin_tag y milestone_value
SELECT 
    origin_tag,
    milestone_value,
    COUNT(*) AS count_achieved,
    COUNT(DISTINCT driver_id) AS count_drivers
FROM ops.v_ct4_milestones_achieved_from_trips_eligible
GROUP BY origin_tag, milestone_value
ORDER BY origin_tag, milestone_value;

-- 2. Validación de consistencia: NO debe existir M5 sin M1
-- Esta query debe devolver 0 filas (garantía de consistencia)
SELECT 
    'M5 sin M1' AS inconsistency_type,
    m5.driver_id,
    m5.origin_tag,
    m5.milestone_value AS m5_milestone,
    m5.achieved_date AS m5_achieved_date,
    m1.milestone_value AS m1_milestone,
    m1.achieved_date AS m1_achieved_date
FROM ops.v_ct4_milestones_achieved_from_trips_eligible m5
LEFT JOIN ops.v_ct4_milestones_achieved_from_trips_eligible m1
    ON m1.driver_id = m5.driver_id
    AND m1.milestone_value = 1
WHERE m5.milestone_value = 5
    AND m1.milestone_value IS NULL;

-- 3. Validación de consistencia: NO debe existir M25 sin M5
-- Esta query debe devolver 0 filas (garantía de consistencia)
SELECT 
    'M25 sin M5' AS inconsistency_type,
    m25.driver_id,
    m25.origin_tag,
    m25.milestone_value AS m25_milestone,
    m25.achieved_date AS m25_achieved_date,
    m5.milestone_value AS m5_milestone,
    m5.achieved_date AS m5_achieved_date
FROM ops.v_ct4_milestones_achieved_from_trips_eligible m25
LEFT JOIN ops.v_ct4_milestones_achieved_from_trips_eligible m5
    ON m5.driver_id = m25.driver_id
    AND m5.milestone_value = 5
WHERE m25.milestone_value = 25
    AND m5.milestone_value IS NULL;

-- 4. Validación de consistencia: NO debe existir M25 sin M1
-- Esta query debe devolver 0 filas (garantía de consistencia)
SELECT 
    'M25 sin M1' AS inconsistency_type,
    m25.driver_id,
    m25.origin_tag,
    m25.milestone_value AS m25_milestone,
    m25.achieved_date AS m25_achieved_date,
    m1.milestone_value AS m1_milestone,
    m1.achieved_date AS m1_achieved_date
FROM ops.v_ct4_milestones_achieved_from_trips_eligible m25
LEFT JOIN ops.v_ct4_milestones_achieved_from_trips_eligible m1
    ON m1.driver_id = m25.driver_id
    AND m1.milestone_value = 1
WHERE m25.milestone_value = 25
    AND m1.milestone_value IS NULL;

-- 5. Validación combinada: M25 sin M5 o M1 (debe dar 0 filas)
-- Esta query debe devolver 0 filas (garantía de consistencia completa)
SELECT 
    'M25 sin M5 o M1' AS inconsistency_type,
    m25.driver_id,
    m25.origin_tag,
    m25.milestone_value AS m25_milestone,
    m25.achieved_date AS m25_achieved_date,
    CASE WHEN m5.milestone_value IS NULL THEN 'FALTA M5' ELSE 'OK' END AS m5_status,
    CASE WHEN m1.milestone_value IS NULL THEN 'FALTA M1' ELSE 'OK' END AS m1_status
FROM ops.v_ct4_milestones_achieved_from_trips_eligible m25
LEFT JOIN ops.v_ct4_milestones_achieved_from_trips_eligible m5
    ON m5.driver_id = m25.driver_id
    AND m5.milestone_value = 5
LEFT JOIN ops.v_ct4_milestones_achieved_from_trips_eligible m1
    ON m1.driver_id = m25.driver_id
    AND m1.milestone_value = 1
WHERE m25.milestone_value = 25
    AND (m5.milestone_value IS NULL OR m1.milestone_value IS NULL);

-- 6. Resumen de validación de consistencia (todas deben dar 0)
SELECT 
    'M5 sin M1' AS check_name,
    COUNT(*) AS inconsistency_count
FROM ops.v_ct4_milestones_achieved_from_trips_eligible m5
LEFT JOIN ops.v_ct4_milestones_achieved_from_trips_eligible m1
    ON m1.driver_id = m5.driver_id
    AND m1.milestone_value = 1
WHERE m5.milestone_value = 5
    AND m1.milestone_value IS NULL
UNION ALL
SELECT 
    'M25 sin M5' AS check_name,
    COUNT(*) AS inconsistency_count
FROM ops.v_ct4_milestones_achieved_from_trips_eligible m25
LEFT JOIN ops.v_ct4_milestones_achieved_from_trips_eligible m5
    ON m5.driver_id = m25.driver_id
    AND m5.milestone_value = 5
WHERE m25.milestone_value = 25
    AND m5.milestone_value IS NULL
UNION ALL
SELECT 
    'M25 sin M1' AS check_name,
    COUNT(*) AS inconsistency_count
FROM ops.v_ct4_milestones_achieved_from_trips_eligible m25
LEFT JOIN ops.v_ct4_milestones_achieved_from_trips_eligible m1
    ON m1.driver_id = m25.driver_id
    AND m1.milestone_value = 1
WHERE m25.milestone_value = 25
    AND m1.milestone_value IS NULL
UNION ALL
SELECT 
    'M25 sin M5 o M1' AS check_name,
    COUNT(*) AS inconsistency_count
FROM ops.v_ct4_milestones_achieved_from_trips_eligible m25
LEFT JOIN ops.v_ct4_milestones_achieved_from_trips_eligible m5
    ON m5.driver_id = m25.driver_id
    AND m5.milestone_value = 5
LEFT JOIN ops.v_ct4_milestones_achieved_from_trips_eligible m1
    ON m1.driver_id = m25.driver_id
    AND m1.milestone_value = 1
WHERE m25.milestone_value = 25
    AND (m5.milestone_value IS NULL OR m1.milestone_value IS NULL);

-- 7. Distribución de milestones por origin_tag
SELECT 
    origin_tag,
    milestone_value,
    COUNT(*) AS count_achieved,
    COUNT(DISTINCT driver_id) AS count_drivers,
    MIN(achieved_date) AS earliest_achieved,
    MAX(achieved_date) AS latest_achieved
FROM ops.v_ct4_milestones_achieved_from_trips_eligible
GROUP BY origin_tag, milestone_value
ORDER BY origin_tag, milestone_value;

-- 8. Top 20 drivers con más milestones achieved
SELECT 
    driver_id,
    origin_tag,
    person_key,
    COUNT(*) AS milestones_count,
    STRING_AGG(milestone_value::text, ', ' ORDER BY milestone_value) AS milestones_list,
    MIN(achieved_date) AS first_milestone_date,
    MAX(achieved_date) AS latest_milestone_date
FROM ops.v_ct4_milestones_achieved_from_trips_eligible
GROUP BY driver_id, origin_tag, person_key
ORDER BY milestones_count DESC, latest_milestone_date DESC
LIMIT 20;
*/








