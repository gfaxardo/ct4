-- ============================================================================
-- Vistas de Reportes de Pagos - Scout y Partner (ACTUALIZADAS)
-- ============================================================================
-- Basadas en ops.v_payment_calculation con soporte para milestone_type/milestone_value
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
    pc.milestone_type,
    pc.milestone_value,
    pc.milestone_trips,  -- Legacy, mantener compatibilidad
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
'Vista detallada de pagos para scouts. Incluye milestone_type y milestone_value. Soporta milestones tipo trips y connection.';

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
    pc.milestone_type,
    pc.milestone_value,
    pc.milestone_trips,  -- Legacy
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
'Vista detallada de pagos para partners (Yango).';

-- ============================================================================
-- C) Vista resumen (agregado) - ACTUALIZADA
-- ============================================================================
-- Drop la vista existente antes de recrearla (necesario cuando cambia el nombre de columnas)
DROP VIEW IF EXISTS ops.v_payments_summary CASCADE;

CREATE VIEW ops.v_payments_summary AS
WITH unified_report AS (
    SELECT 
        rule_scope,
        origin_tag,
        lead_date,
        milestone_type,
        milestone_value,
        milestone_trips,  -- Legacy
        window_days,
        is_payable,
        milestone_achieved,
        amount
    FROM ops.v_payment_calculation
)
SELECT 
    rule_scope,
    origin_tag,
    date_trunc('week', lead_date)::date AS week_start_monday,
    to_char(lead_date, 'IYYY-IW') AS iso_year_week,
    milestone_type,
    milestone_value,
    milestone_trips,  -- Legacy
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
    date_trunc('week', lead_date)::date,
    to_char(lead_date, 'IYYY-IW'),
    milestone_type,
    milestone_value,
    milestone_trips,  -- Legacy
    window_days
ORDER BY 
    week_start_monday DESC,
    rule_scope,
    origin_tag,
    milestone_type,
    milestone_value,
    window_days;

COMMENT ON VIEW ops.v_payments_summary IS 
'Vista agregada de pagos por semana, rule_scope, origin_tag, milestone_type, milestone_value y window_days. Incluye métricas de totales, pagables y tasas.';

