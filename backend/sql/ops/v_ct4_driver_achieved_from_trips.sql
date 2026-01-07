-- ============================================================================
-- Vista: ops.v_ct4_driver_achieved_from_trips
-- ============================================================================
-- PROPÓSITO:
-- Vista pivot que transforma milestones achieved determinísticos (1 fila por milestone)
-- en 1 fila por driver con flags y fechas por milestone (M1, M5, M25).
--
-- ARQUITECTURA:
-- Pivotea ops.v_ct4_milestones_achieved_from_trips_eligible de formato largo
-- (driver_id, milestone_value) a formato ancho (driver_id con columnas m1_*, m5_*, m25_*).
--
-- CAPA: C2 - Elegibilidad (ACHIEVED) - Versión Pivot Determinística
-- ============================================================================
-- REGLAS:
-- 1. Fuente: ops.v_ct4_milestones_achieved_from_trips_eligible
-- 2. Grano: (driver_id) - 1 fila por driver
-- 3. Flags booleanos usando BOOL_OR (más eficiente que MAX(boolean))
-- 4. Fechas usando MAX(CASE WHEN ...) para obtener la fecha de achieved
-- 5. Garantiza consistencia: si M5=true, entonces M1=true (por diseño de fuente)
-- ============================================================================
-- USO:
-- - Base para Driver Matrix CT4 (v_payments_driver_matrix_ct4)
-- - Consultas rápidas de achieved por driver sin necesidad de pivotear
-- - Comparación con achieved legacy (v_payments_driver_matrix_cabinet)
-- ============================================================================

CREATE OR REPLACE VIEW ops.v_ct4_driver_achieved_from_trips AS
SELECT 
    a.driver_id,
    a.origin_tag,
    a.person_key,
    a.identity_status,
    -- Milestone M1
    BOOL_OR(a.milestone_value = 1) AS m1_achieved_flag,
    MAX(CASE WHEN a.milestone_value = 1 THEN a.achieved_date END) AS m1_achieved_date,
    -- Milestone M5
    BOOL_OR(a.milestone_value = 5) AS m5_achieved_flag,
    MAX(CASE WHEN a.milestone_value = 5 THEN a.achieved_date END) AS m5_achieved_date,
    -- Milestone M25
    BOOL_OR(a.milestone_value = 25) AS m25_achieved_flag,
    MAX(CASE WHEN a.milestone_value = 25 THEN a.achieved_date END) AS m25_achieved_date
FROM ops.v_ct4_milestones_achieved_from_trips_eligible a
GROUP BY a.driver_id, a.origin_tag, a.person_key, a.identity_status
ORDER BY a.driver_id;

-- ============================================================================
-- Comentarios
-- ============================================================================
COMMENT ON VIEW ops.v_ct4_driver_achieved_from_trips IS 
'Vista pivot que transforma milestones achieved determinísticos (1 fila por milestone) en 1 fila por driver con flags y fechas por milestone (M1, M5, M25). Fuente: ops.v_ct4_milestones_achieved_from_trips_eligible. Garantiza consistencia: si M5=true, entonces M1=true. Grano: (driver_id) - 1 fila por driver.';

COMMENT ON COLUMN ops.v_ct4_driver_achieved_from_trips.driver_id IS 
'ID del conductor.';

COMMENT ON COLUMN ops.v_ct4_driver_achieved_from_trips.origin_tag IS 
'Origen del driver: ''cabinet'' o ''fleet_migration''.';

COMMENT ON COLUMN ops.v_ct4_driver_achieved_from_trips.person_key IS 
'Person key del conductor (identidad canónica).';

COMMENT ON COLUMN ops.v_ct4_driver_achieved_from_trips.identity_status IS 
'Estado de identidad: ''confirmed'', ''enriched'', ''ambiguous'', ''no_match'', o NULL.';

COMMENT ON COLUMN ops.v_ct4_driver_achieved_from_trips.m1_achieved_flag IS 
'Flag indicando si M1 está achieved (true si existe milestone_value=1 en fuente).';

COMMENT ON COLUMN ops.v_ct4_driver_achieved_from_trips.m1_achieved_date IS 
'Fecha en que se alcanzó M1 según summary_daily (primer día con trips >= 1).';

COMMENT ON COLUMN ops.v_ct4_driver_achieved_from_trips.m5_achieved_flag IS 
'Flag indicando si M5 está achieved (true si existe milestone_value=5 en fuente).';

COMMENT ON COLUMN ops.v_ct4_driver_achieved_from_trips.m5_achieved_date IS 
'Fecha en que se alcanzó M5 según summary_daily (primer día con trips >= 5).';

COMMENT ON COLUMN ops.v_ct4_driver_achieved_from_trips.m25_achieved_flag IS 
'Flag indicando si M25 está achieved (true si existe milestone_value=25 en fuente).';

COMMENT ON COLUMN ops.v_ct4_driver_achieved_from_trips.m25_achieved_date IS 
'Fecha en que se alcanzó M25 según summary_daily (primer día con trips >= 25).';







