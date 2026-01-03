-- ============================================================================
-- Vistas Export-Ready para Liquidaciones de Pagos
-- ============================================================================
-- Vistas optimizadas para exportación y liquidación de pagos
-- ============================================================================

-- ============================================================================
-- 1) Vista detalle de liquidación scout payable
-- ============================================================================
CREATE OR REPLACE VIEW ops.v_scout_liquidation_payable_detail AS
SELECT 
    scout_id,
    date_trunc('week', payable_date)::date AS pay_week_start_monday,
    to_char(payable_date, 'IYYY-IW') AS pay_iso_year_week,
    payable_date,
    achieved_date,
    lead_date,
    lead_origin,
    'yego_scouts' AS payer,
    milestone_type,
    milestone_value,
    window_days,
    trips_in_window,
    person_key,
    driver_id,
    amount,
    currency,
    NOW() AS created_at_export
FROM ops.v_scout_payments_report_ui
WHERE is_payable = true
  AND amount > 0
ORDER BY payable_date DESC, scout_id, person_key;

COMMENT ON VIEW ops.v_scout_liquidation_payable_detail IS 
'Vista detalle de pagos scout elegibles para liquidación. Filtra is_payable=true y amount>0. Incluye semana de pago basada en payable_date.';

-- ============================================================================
-- 2) Vista agregada de liquidación scout payable
-- ============================================================================
CREATE OR REPLACE VIEW ops.v_scout_liquidation_payable AS
SELECT 
    scout_id,
    pay_week_start_monday,
    pay_iso_year_week,
    currency,
    SUM(amount) AS total_amount_payable,
    COUNT(*) AS count_payments,
    COUNT(DISTINCT driver_id) AS count_drivers
FROM ops.v_scout_liquidation_payable_detail
GROUP BY 
    scout_id,
    pay_week_start_monday,
    pay_iso_year_week,
    currency
ORDER BY pay_week_start_monday DESC, total_amount_payable DESC, scout_id;

COMMENT ON VIEW ops.v_scout_liquidation_payable IS 
'Vista agregada de pagos scout por scout_id, semana de pago y moneda. Suma montos, cuenta pagos y conductores únicos.';

-- ============================================================================
-- 3) Vista detalle de receivables Yango payable
-- ============================================================================
CREATE OR REPLACE VIEW ops.v_yango_receivable_payable_detail AS
SELECT 
    date_trunc('week', payable_date)::date AS pay_week_start_monday,
    to_char(payable_date, 'IYYY-IW') AS pay_iso_year_week,
    payable_date,
    achieved_date,
    lead_date,
    lead_origin,
    'yango' AS payer,
    milestone_type,
    milestone_value,
    window_days,
    trips_in_window,
    person_key,
    driver_id,
    amount,
    currency,
    NOW() AS created_at_export
FROM ops.v_partner_payments_report_ui
WHERE is_payable = true
  AND amount > 0
ORDER BY payable_date DESC, person_key;

COMMENT ON VIEW ops.v_yango_receivable_payable_detail IS 
'Vista detalle de receivables Yango elegibles para liquidación. Filtra is_payable=true y amount>0. Incluye semana de pago basada en payable_date.';

-- ============================================================================
-- 4) Vista agregada de receivables Yango payable
-- ============================================================================
CREATE OR REPLACE VIEW ops.v_yango_receivable_payable AS
SELECT 
    pay_week_start_monday,
    pay_iso_year_week,
    currency,
    SUM(amount) AS total_amount_payable,
    COUNT(*) AS count_payments,
    COUNT(DISTINCT driver_id) AS count_drivers
FROM ops.v_yango_receivable_payable_detail
GROUP BY 
    pay_week_start_monday,
    pay_iso_year_week,
    currency
ORDER BY pay_week_start_monday DESC, total_amount_payable DESC;

COMMENT ON VIEW ops.v_yango_receivable_payable IS 
'Vista agregada de receivables Yango por semana de pago y moneda. Suma montos, cuenta pagos y conductores únicos.';



















