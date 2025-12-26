-- ============================================================================
-- Vistas UI-Friendly para Reportes de Pagos
-- ============================================================================
-- Versiones con nombres más amigables para usuarios finales
-- Sin cambiar las vistas core
-- ============================================================================

-- ============================================================================
-- A) Vista resumen UI-friendly
-- ============================================================================
CREATE OR REPLACE VIEW ops.v_payments_summary_ui AS
SELECT 
    CASE 
        WHEN rule_scope = 'partner' THEN 'yango'
        WHEN rule_scope = 'scout' THEN 'yego_scouts'
        ELSE rule_scope
    END AS payer,
    CASE 
        WHEN origin_tag = 'fleet_migration' THEN 'migration'
        ELSE origin_tag
    END AS lead_origin,
    week_start_monday,
    iso_year_week,
    milestone_type,
    milestone_value,
    milestone_trips,  -- Legacy
    window_days,
    rows_total,
    rows_payable,
    rows_pending,
    rows_not_eligible,
    amount_total_payable,
    amount_total_all,
    payable_rate
FROM ops.v_payments_summary
ORDER BY week_start_monday DESC, payer, lead_origin, milestone_type, milestone_value;

COMMENT ON VIEW ops.v_payments_summary_ui IS 
'Vista resumen UI-friendly: payer (yango/yego_scouts) y lead_origin (migration/cabinet). Basada en ops.v_payments_summary.';

-- ============================================================================
-- B) Vista detalle partner UI-friendly
-- ============================================================================
CREATE OR REPLACE VIEW ops.v_partner_payments_report_ui AS
SELECT 
    person_key,
    CASE 
        WHEN origin_tag = 'fleet_migration' THEN 'migration'
        ELSE origin_tag
    END AS lead_origin,
    scout_id,
    driver_id,
    hire_date,
    lead_date,
    first_connection_date,
    rule_id,
    milestone_type,
    milestone_value,
    milestone_trips,
    window_days,
    trips_in_window,
    milestone_achieved,
    achieved_date,
    is_payable,
    payable_date,
    amount,
    currency,
    payment_status,
    created_at_report
FROM ops.v_partner_payments_report;

COMMENT ON VIEW ops.v_partner_payments_report_ui IS 
'Vista detalle partner UI-friendly: lead_origin (migration/cabinet). Basada en ops.v_partner_payments_report.';

-- ============================================================================
-- C) Vista detalle scout UI-friendly (ENRIQUECIDA con atribución)
-- ============================================================================
CREATE OR REPLACE VIEW ops.v_scout_payments_report_ui AS
SELECT 
    spr.person_key,
    CASE 
        WHEN spr.origin_tag = 'fleet_migration' THEN 'migration'
        ELSE spr.origin_tag
    END AS lead_origin,
    spr.scout_id,
    spr.driver_id,
    spr.hire_date,
    spr.lead_date,
    spr.first_connection_date,
    spr.rule_id,
    spr.milestone_type,
    spr.milestone_value,
    spr.milestone_trips,
    spr.window_days,
    spr.trips_in_window,
    spr.milestone_achieved,
    spr.achieved_date,
    spr.is_payable,
    spr.payable_date,
    spr.amount,
    spr.currency,
    spr.payment_status,
    spr.created_at_report,
    -- Columnas de atribución
    attr.acquisition_scout_id,
    attr.acquisition_scout_name,
    attr.attribution_confidence,
    attr.attribution_rule
FROM ops.v_scout_payments_report spr
LEFT JOIN ops.v_attribution_canonical attr
    ON attr.person_key = spr.person_key;

COMMENT ON VIEW ops.v_scout_payments_report_ui IS 
'Vista detalle scout UI-friendly: lead_origin (migration/cabinet). Basada en ops.v_scout_payments_report. Enriquecida con columnas de atribución desde ops.v_attribution_canonical.';

