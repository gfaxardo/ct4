-- ============================================================================
-- Vista: ops.v_cabinet_milestones_achieved_from_payment_calc
-- ============================================================================
-- PROPÓSITO:
-- Vista canónica que determina milestones ACHIEVED basándose en 
-- ops.v_payment_calculation (source-of-truth para achieved de claims).
-- 
-- Esta vista reemplaza la validación con v_cabinet_milestones_achieved_from_trips
-- para claims, ya que v_payment_calculation ya normaliza date_file con to_date
-- y es la fuente autoritativa para milestone_achieved.
-- ============================================================================
-- REGLAS DE NEGOCIO:
-- 1. Solo milestones con valores 1, 5, 25 (milestone_trips)
-- 2. Solo origin_tag='cabinet'
-- 3. achieved_flag = bool_or(milestone_achieved) por driver_id + milestone_value
-- 4. achieved_date = min(achieved_date) donde milestone_achieved=true
-- 5. NO castear lead_date ni date_file aquí; v_payment_calculation ya normaliza summary_daily.date_file con to_date
-- ============================================================================
-- GRANO:
-- (driver_id, milestone_value) - 1 fila por milestone alcanzado por driver
-- ============================================================================
-- USO:
-- - Validación de claims: verificar si un driver alcanzó un milestone
-- - Reemplaza validación con v_cabinet_milestones_achieved_from_trips para claims
-- - Source-of-truth para achieved en contexto de claims/pagos (basado en v_payment_calculation)
-- ============================================================================

CREATE OR REPLACE VIEW ops.v_cabinet_milestones_achieved_from_payment_calc AS
SELECT
    pc.driver_id,
    pc.milestone_trips AS milestone_value,
    bool_or(pc.milestone_achieved) AS achieved_flag,
    min(pc.achieved_date) FILTER (WHERE pc.milestone_achieved) AS achieved_date
FROM ops.v_payment_calculation pc
WHERE pc.origin_tag = 'cabinet'
    AND pc.milestone_trips IN (1, 5, 25)
    AND pc.driver_id IS NOT NULL
GROUP BY pc.driver_id, pc.milestone_trips;

-- ============================================================================
-- Comentarios
-- ============================================================================
COMMENT ON VIEW ops.v_cabinet_milestones_achieved_from_payment_calc IS 
'Vista canónica que determina milestones ACHIEVED basándose en ops.v_payment_calculation (source-of-truth para achieved de claims). Reemplaza validación con v_cabinet_milestones_achieved_from_trips para claims. Grano: (driver_id, milestone_value).';

COMMENT ON COLUMN ops.v_cabinet_milestones_achieved_from_payment_calc.driver_id IS 
'ID del conductor que alcanzó el milestone.';

COMMENT ON COLUMN ops.v_cabinet_milestones_achieved_from_payment_calc.milestone_value IS 
'Valor del milestone alcanzado (1, 5, o 25).';

COMMENT ON COLUMN ops.v_cabinet_milestones_achieved_from_payment_calc.achieved_flag IS 
'Flag indicando si se alcanzó el milestone (bool_or de milestone_achieved desde v_payment_calculation).';

COMMENT ON COLUMN ops.v_cabinet_milestones_achieved_from_payment_calc.achieved_date IS 
'Primera fecha en que se alcanzó el milestone (min de achieved_date donde milestone_achieved=true).';

