-- ============================================================================
-- Vista: ops.v_cabinet_milestones_achieved
-- ============================================================================
-- PROPÓSITO:
-- Vista canónica C2 que expone SOLO milestones ACHIEVED (operativos - viajes logrados)
-- sin mezclar con información de pagos. Separación semántica clara: ACHIEVED ≠ PAID.
--
-- CAPA CANÓNICA: C2 - Elegibilidad (ACHIEVED)
-- ============================================================================
-- REGLAS:
-- 1. Fuente única: ops.v_payment_calculation (vista canónica C2)
-- 2. Sin campos de pago (no JOIN con ledger ni module_ct_cabinet_payments)
-- 3. Grano: (driver_id, milestone_value) - 1 fila por milestone alcanzado
-- 4. Solo milestones alcanzados: milestone_achieved = true
-- 5. Solo cabinet: origin_tag = 'cabinet'
-- 6. Solo partner: rule_scope = 'partner' (Yango, no scouts)
-- 7. Solo milestones 1, 5, 25
-- 8. Deduplicación: DISTINCT ON (driver_id, milestone_value) quedarse con lead_date más reciente
-- ============================================================================
-- USO:
-- - Consultar milestones operativos logrados por conductores
-- - NO usar para consultar pagos (usar v_cabinet_milestones_paid)
-- - Para reconciliación: usar v_cabinet_milestones_reconciled
-- ============================================================================

CREATE OR REPLACE VIEW ops.v_cabinet_milestones_achieved AS
WITH base_achieved AS (
    -- Fuente: ops.v_payment_calculation (vista canónica C2)
    SELECT 
        pc.driver_id,
        pc.person_key,
        pc.lead_date,
        pc.milestone_trips AS milestone_value,
        pc.milestone_achieved,
        pc.achieved_date,
        pc.achieved_trips_in_window,
        pc.window_days,
        pc.amount AS expected_amount,  -- Monto según regla (no pago real)
        pc.currency,
        pc.rule_id,
        pc.rule_scope,
        pc.rule_valid_from,
        pc.rule_valid_to
    FROM ops.v_payment_calculation pc
    WHERE pc.origin_tag = 'cabinet'
        AND pc.rule_scope = 'partner'  -- Solo Yango (partner), no scouts
        AND pc.milestone_trips IN (1, 5, 25)
        AND pc.milestone_achieved = true  -- Solo milestones alcanzados
        AND pc.driver_id IS NOT NULL
),
dedup_achieved AS (
    -- Deduplicación: 1 fila por (driver_id + milestone_value), quedarse con lead_date más reciente
    SELECT DISTINCT ON (driver_id, milestone_value)
        driver_id,
        person_key,
        lead_date,
        milestone_value,
        milestone_achieved,
        achieved_date,
        achieved_trips_in_window,
        window_days,
        expected_amount,
        currency,
        rule_id,
        rule_scope,
        rule_valid_from,
        rule_valid_to
    FROM base_achieved
    ORDER BY driver_id, milestone_value, lead_date DESC
)
SELECT 
    driver_id,
    person_key,
    milestone_value,
    lead_date,
    milestone_achieved,
    achieved_date,
    achieved_trips_in_window,
    window_days,
    expected_amount,
    currency,
    rule_id,
    rule_scope,
    rule_valid_from,
    rule_valid_to
FROM dedup_achieved;

-- ============================================================================
-- Comentarios
-- ============================================================================
COMMENT ON VIEW ops.v_cabinet_milestones_achieved IS 
'Vista canónica C2 que expone SOLO milestones ACHIEVED (operativos - viajes logrados) sin mezclar con información de pagos. Separación semántica clara: ACHIEVED ≠ PAID. Grano: (driver_id, milestone_value) - 1 fila por milestone alcanzado. Fuente: ops.v_payment_calculation.';

COMMENT ON COLUMN ops.v_cabinet_milestones_achieved.driver_id IS 
'ID del conductor que alcanzó el milestone.';

COMMENT ON COLUMN ops.v_cabinet_milestones_achieved.person_key IS 
'Person key del conductor (identidad canónica).';

COMMENT ON COLUMN ops.v_cabinet_milestones_achieved.milestone_value IS 
'Valor del milestone alcanzado (1, 5, o 25).';

COMMENT ON COLUMN ops.v_cabinet_milestones_achieved.lead_date IS 
'Fecha del lead (lead_date más reciente si hay duplicados).';

COMMENT ON COLUMN ops.v_cabinet_milestones_achieved.milestone_achieved IS 
'Flag indicando si se alcanzó el milestone (siempre true en esta vista).';

COMMENT ON COLUMN ops.v_cabinet_milestones_achieved.achieved_date IS 
'Fecha en que se alcanza el milestone según viajes reales (summary_daily).';

COMMENT ON COLUMN ops.v_cabinet_milestones_achieved.achieved_trips_in_window IS 
'Cantidad de viajes acumulados en achieved_date dentro de la ventana especificada.';

COMMENT ON COLUMN ops.v_cabinet_milestones_achieved.window_days IS 
'Días de ventana para alcanzar el milestone (según regla de pago).';

COMMENT ON COLUMN ops.v_cabinet_milestones_achieved.expected_amount IS 
'Monto esperado según regla de pago (milestone 1=25, 5=35, 25=100). NO es el pago real, solo el monto según regla.';

COMMENT ON COLUMN ops.v_cabinet_milestones_achieved.currency IS 
'Moneda del monto esperado (generalmente PEN).';

COMMENT ON COLUMN ops.v_cabinet_milestones_achieved.rule_id IS 
'ID de la regla de pago aplicada (desde ops.partner_payment_rules).';

COMMENT ON COLUMN ops.v_cabinet_milestones_achieved.rule_scope IS 
'Alcance de la regla: siempre ''partner'' (Yango, no scouts) en esta vista.';

COMMENT ON COLUMN ops.v_cabinet_milestones_achieved.rule_valid_from IS 
'Fecha desde la cual la regla es válida.';

COMMENT ON COLUMN ops.v_cabinet_milestones_achieved.rule_valid_to IS 
'Fecha hasta la cual la regla es válida (NULL si no tiene fecha de fin).';

