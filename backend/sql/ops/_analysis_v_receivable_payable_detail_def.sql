-- Definicion completa de ops.v_yango_receivable_payable_detail
-- Generado por analisis de causa raiz M5 sin M1

 SELECT date_trunc('week'::text, v_partner_payments_report_ui.payable_date::timestamp with time zone)::date AS pay_week_start_monday,
    to_char(v_partner_payments_report_ui.payable_date::timestamp with time zone, 'IYYY-IW'::text) AS pay_iso_year_week,
    v_partner_payments_report_ui.payable_date,
    v_partner_payments_report_ui.achieved_date,
    v_partner_payments_report_ui.lead_date,
    v_partner_payments_report_ui.lead_origin,
    'yango'::text AS payer,
    v_partner_payments_report_ui.milestone_type,
    v_partner_payments_report_ui.milestone_value,
    v_partner_payments_report_ui.window_days,
    v_partner_payments_report_ui.trips_in_window,
    v_partner_payments_report_ui.person_key,
    v_partner_payments_report_ui.driver_id,
    v_partner_payments_report_ui.amount,
    v_partner_payments_report_ui.currency,
    now() AS created_at_export
   FROM ops.v_partner_payments_report_ui
  WHERE v_partner_payments_report_ui.is_payable = true AND v_partner_payments_report_ui.amount > 0::numeric
  ORDER BY v_partner_payments_report_ui.payable_date DESC, v_partner_payments_report_ui.person_key;