-- ============================================================================
-- Vistas de Reportes de Pagos - Scout y Partner
-- ============================================================================
-- Basadas en ops.v_payment_calculation con enriquecimiento de datos
-- ============================================================================

-- ============================================================================
-- A) Vista detalle scout
-- ============================================================================
CREATE OR REPLACE VIEW ops.v_scout_payments_report AS
SELECT 
    pc.person_key,
    pc.origin_tag,
    pc.scout_id,
    pc.driver_id,
    vcm.hire_date,
    pc.lead_date,
    vcm.first_connection_date,
    pc.rule_id,
    pc.milestone_trips,
    pc.window_days,
    pc.achieved_trips_in_window AS trips_in_window,
    pc.milestone_achieved,
    pc.achieved_date,
    pc.is_payable,
    pc.payable_date,
    pc.amount,
    pc.currency,
    -- Payment_status
    CASE 
        WHEN pc.is_payable = true THEN 'payable'
        WHEN pc.milestone_achieved = true AND pc.is_payable = false THEN 'pending'
        WHEN pc.milestone_achieved = false THEN 'not_eligible'
        ELSE 'unknown'
    END AS payment_status,
    NOW() AS created_at_report
FROM ops.v_payment_calculation pc
LEFT JOIN observational.v_conversion_metrics vcm
    ON vcm.person_key = pc.person_key
    AND vcm.origin_tag = pc.origin_tag
WHERE pc.rule_scope = 'scout';

COMMENT ON VIEW ops.v_scout_payments_report IS 
'Vista detallada de pagos para scouts. Incluye estado de pago (payable/pending/not_eligible) y datos enriquecidos desde v_conversion_metrics.';

-- ============================================================================
-- B) Vista detalle partner
-- ============================================================================
CREATE OR REPLACE VIEW ops.v_partner_payments_report AS
SELECT 
    pc.person_key,
    pc.origin_tag,
    pc.scout_id,
    pc.driver_id,
    vcm.hire_date,
    pc.lead_date,
    vcm.first_connection_date,
    pc.rule_id,
    pc.milestone_trips,
    pc.window_days,
    pc.achieved_trips_in_window AS trips_in_window,
    pc.milestone_achieved,
    pc.achieved_date,
    pc.is_payable,
    pc.payable_date,
    pc.amount,
    pc.currency,
    -- Payment_status
    CASE 
        WHEN pc.is_payable = true THEN 'payable'
        WHEN pc.milestone_achieved = true AND pc.is_payable = false THEN 'pending'
        WHEN pc.milestone_achieved = false THEN 'not_eligible'
        ELSE 'unknown'
    END AS payment_status,
    NOW() AS created_at_report
FROM ops.v_payment_calculation pc
LEFT JOIN observational.v_conversion_metrics vcm
    ON vcm.person_key = pc.person_key
    AND vcm.origin_tag = pc.origin_tag
WHERE pc.rule_scope = 'partner';

COMMENT ON VIEW ops.v_partner_payments_report IS 
'Vista detallada de pagos para partners (Yango). Incluye estado de pago (payable/pending/not_eligible) y datos enriquecidos desde v_conversion_metrics.';

-- ============================================================================
-- C) Vista resumen (agregado)
-- ============================================================================
CREATE OR REPLACE VIEW ops.v_payments_summary AS
WITH unified_report AS (
    SELECT 
        rule_scope,
        origin_tag,
        lead_date,
        milestone_trips,
        window_days,
        is_payable,
        milestone_achieved,
        amount
    FROM ops.v_payment_calculation
)
SELECT 
    rule_scope,
    origin_tag,
    DATE_TRUNC('week', lead_date) AS lead_week,
    milestone_trips,
    window_days,
    COUNT(*) AS rows_total,
    COUNT(*) FILTER (WHERE is_payable = true) AS rows_payable,
    COUNT(*) FILTER (WHERE milestone_achieved = true AND is_payable = false) AS rows_pending,
    COUNT(*) FILTER (WHERE milestone_achieved = false) AS rows_not_eligible,
    SUM(amount) FILTER (WHERE is_payable = true) AS amount_total_payable,
    SUM(amount) AS amount_total_all,
    CASE 
        WHEN COUNT(*) > 0 THEN 
            COUNT(*) FILTER (WHERE is_payable = true)::decimal / NULLIF(COUNT(*), 0)
        ELSE NULL
    END AS payable_rate
FROM unified_report
GROUP BY 
    rule_scope,
    origin_tag,
    DATE_TRUNC('week', lead_date),
    milestone_trips,
    window_days
ORDER BY 
    lead_week DESC,
    rule_scope,
    origin_tag,
    milestone_trips,
    window_days;

COMMENT ON VIEW ops.v_payments_summary IS 
'Vista agregada de pagos por semana, rule_scope, origin_tag, milestone_trips y window_days. Incluye métricas de totales, pagables y tasas.';

