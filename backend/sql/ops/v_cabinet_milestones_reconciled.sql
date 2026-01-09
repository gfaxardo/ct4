-- ============================================================================
-- Vista: ops.v_cabinet_milestones_reconciled
-- ============================================================================
-- PROPÓSITO:
-- Vista de reconciliación que hace JOIN explícito entre ACHIEVED (operativo) y PAID (pagos Yango).
-- Expone reconciliation_status que categoriza cada milestone en 4 estados mutuamente excluyentes.
--
-- CAPA CANÓNICA: C3 - Claims (reconciled)
-- ============================================================================
-- REGLAS:
-- 1. JOIN explícito: ACHIEVED ⟕ PAID (LEFT JOIN desde ACHIEVED, RIGHT JOIN implícito para PAID sin ACHIEVED)
-- 2. Grano: (driver_id, milestone_value) - 1 fila por combinación posible
-- 3. Reconciliation status (mutuamente excluyente):
--    - ACHIEVED_NOT_PAID: Milestone alcanzado pero no pagado
--    - PAID_WITHOUT_ACHIEVEMENT: Milestone pagado pero no alcanzado
--    - OK: Milestone alcanzado y pagado
--    - NOT_APPLICABLE: Ni alcanzado ni pagado (no debería aparecer en producción)
-- 4. FULL OUTER JOIN para capturar ambos casos (ACHIEVED sin PAID y PAID sin ACHIEVED)
-- ============================================================================
-- USO:
-- - Diagnóstico de inconsistencias (M5 pagado sin M1 pagado, etc.)
-- - Reconciliación operativa entre milestones logrados y pagos
-- - Reportes de cobranza que necesitan cruzar ACHIEVED vs PAID
-- ============================================================================

CREATE OR REPLACE VIEW ops.v_cabinet_milestones_reconciled AS
WITH achieved_flattened AS (
    -- ACHIEVED: Una fila por (driver_id, milestone_value)
    SELECT 
        driver_id,
        person_key AS achieved_person_key,
        milestone_value,
        lead_date AS achieved_lead_date,
        achieved_date,
        achieved_trips_in_window,
        window_days,
        expected_amount,
        currency AS achieved_currency,
        rule_id,
        true AS achieved_flag
    FROM ops.v_cabinet_milestones_achieved
),
paid_flattened AS (
    -- PAID: Una fila por (driver_id, milestone_value)
    SELECT 
        driver_id,
        person_key AS paid_person_key,
        milestone_value,
        pay_date,
        payment_key,
        identity_status,
        match_rule,
        match_confidence,
        latest_snapshot_at,
        true AS paid_flag
    FROM ops.v_cabinet_milestones_paid
),
reconciled AS (
    -- FULL OUTER JOIN para capturar ambos casos
    SELECT 
        COALESCE(a.driver_id, p.driver_id) AS driver_id,
        a.milestone_value,
        
        -- Campos de ACHIEVED (NULL si no está alcanzado)
        a.achieved_person_key,
        a.achieved_lead_date,
        a.achieved_date,
        a.achieved_trips_in_window,
        a.window_days,
        a.expected_amount,
        a.achieved_currency,
        a.rule_id,
        a.achieved_flag,
        
        -- Campos de PAID (NULL si no está pagado)
        p.paid_person_key,
        p.pay_date,
        p.payment_key,
        p.identity_status,
        p.match_rule,
        p.match_confidence,
        p.latest_snapshot_at,
        p.paid_flag,
        
        -- Reconciliation status (categoría mutuamente excluyente)
        CASE 
            WHEN a.achieved_flag = true AND p.paid_flag = true THEN 'OK'
            WHEN a.achieved_flag = true AND (p.paid_flag IS NULL OR p.paid_flag = false) THEN 'ACHIEVED_NOT_PAID'
            WHEN (a.achieved_flag IS NULL OR a.achieved_flag = false) AND p.paid_flag = true THEN 'PAID_WITHOUT_ACHIEVEMENT'
            ELSE 'NOT_APPLICABLE'  -- No debería aparecer en producción
        END AS reconciliation_status
        
    FROM achieved_flattened a
    FULL OUTER JOIN paid_flattened p
        ON a.driver_id = p.driver_id
        AND a.milestone_value = p.milestone_value
)
SELECT 
    driver_id,
    milestone_value,
    
    -- ACHIEVED fields
    achieved_flag,
    achieved_person_key,
    achieved_lead_date,
    achieved_date,
    achieved_trips_in_window,
    window_days,
    expected_amount,
    achieved_currency,
    rule_id,
    
    -- PAID fields
    paid_flag,
    paid_person_key,
    pay_date,
    payment_key,
    identity_status,
    match_rule,
    match_confidence,
    latest_snapshot_at,
    
    -- Reconciliation
    reconciliation_status
    
FROM reconciled
ORDER BY driver_id, milestone_value;

-- ============================================================================
-- Comentarios
-- ============================================================================
COMMENT ON VIEW ops.v_cabinet_milestones_reconciled IS 
'Vista de reconciliación que hace JOIN explícito entre ACHIEVED (operativo) y PAID (pagos Yango). Expone reconciliation_status que categoriza cada milestone en 4 estados mutuamente excluyentes: OK, ACHIEVED_NOT_PAID, PAID_WITHOUT_ACHIEVEMENT, NOT_APPLICABLE. Grano: (driver_id, milestone_value).';

COMMENT ON COLUMN ops.v_cabinet_milestones_reconciled.driver_id IS 
'ID del conductor (coalesce de ACHIEVED y PAID).';

COMMENT ON COLUMN ops.v_cabinet_milestones_reconciled.milestone_value IS 
'Valor del milestone (1, 5, o 25).';

COMMENT ON COLUMN ops.v_cabinet_milestones_reconciled.achieved_flag IS 
'Flag indicando si el milestone fue alcanzado (TRUE si existe en v_cabinet_milestones_achieved).';

COMMENT ON COLUMN ops.v_cabinet_milestones_reconciled.achieved_person_key IS 
'Person key desde ACHIEVED (NULL si no está alcanzado).';

COMMENT ON COLUMN ops.v_cabinet_milestones_reconciled.achieved_lead_date IS 
'Lead date desde ACHIEVED (NULL si no está alcanzado).';

COMMENT ON COLUMN ops.v_cabinet_milestones_reconciled.achieved_date IS 
'Fecha en que se alcanzó el milestone según viajes reales (NULL si no está alcanzado).';

COMMENT ON COLUMN ops.v_cabinet_milestones_reconciled.achieved_trips_in_window IS 
'Viajes acumulados en achieved_date dentro de la ventana (NULL si no está alcanzado).';

COMMENT ON COLUMN ops.v_cabinet_milestones_reconciled.window_days IS 
'Días de ventana para alcanzar el milestone (NULL si no está alcanzado).';

COMMENT ON COLUMN ops.v_cabinet_milestones_reconciled.expected_amount IS 
'Monto esperado según regla de pago (NULL si no está alcanzado).';

COMMENT ON COLUMN ops.v_cabinet_milestones_reconciled.achieved_currency IS 
'Moneda del monto esperado (NULL si no está alcanzado).';

COMMENT ON COLUMN ops.v_cabinet_milestones_reconciled.rule_id IS 
'ID de la regla de pago aplicada (NULL si no está alcanzado).';

COMMENT ON COLUMN ops.v_cabinet_milestones_reconciled.paid_flag IS 
'Flag indicando si el milestone fue pagado (TRUE si existe en v_cabinet_milestones_paid).';

COMMENT ON COLUMN ops.v_cabinet_milestones_reconciled.paid_person_key IS 
'Person key desde PAID (NULL si no está pagado).';

COMMENT ON COLUMN ops.v_cabinet_milestones_reconciled.pay_date IS 
'Fecha del pago reconocido por Yango (NULL si no está pagado).';

COMMENT ON COLUMN ops.v_cabinet_milestones_reconciled.payment_key IS 
'Clave única del pago en el ledger (NULL si no está pagado).';

COMMENT ON COLUMN ops.v_cabinet_milestones_reconciled.identity_status IS 
'Estado de identidad del pago (NULL si no está pagado): confirmed, enriched, ambiguous, no_match.';

COMMENT ON COLUMN ops.v_cabinet_milestones_reconciled.match_rule IS 
'Regla de matching del pago (NULL si no está pagado): source_upstream, name_unique, ambiguous, no_match.';

COMMENT ON COLUMN ops.v_cabinet_milestones_reconciled.match_confidence IS 
'Confianza del matching del pago (NULL si no está pagado): high, medium, low.';

COMMENT ON COLUMN ops.v_cabinet_milestones_reconciled.latest_snapshot_at IS 
'Timestamp de la última snapshot del ledger (NULL si no está pagado).';

COMMENT ON COLUMN ops.v_cabinet_milestones_reconciled.reconciliation_status IS 
'Estado de reconciliación (mutuamente excluyente): OK (alcanzado y pagado), ACHIEVED_NOT_PAID (alcanzado pero no pagado), PAID_WITHOUT_ACHIEVEMENT (pagado pero no alcanzado), NOT_APPLICABLE (ni alcanzado ni pagado - no debería aparecer en producción).';









