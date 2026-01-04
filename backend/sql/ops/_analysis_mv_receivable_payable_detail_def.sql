-- Definicion completa de ops.mv_yango_receivable_payable_detail
-- Generado por analisis de causa raiz M5 sin M1

 SELECT v_yango_receivable_payable_detail.pay_week_start_monday,
    v_yango_receivable_payable_detail.pay_iso_year_week,
    v_yango_receivable_payable_detail.payable_date,
    v_yango_receivable_payable_detail.achieved_date,
    v_yango_receivable_payable_detail.lead_date,
    v_yango_receivable_payable_detail.lead_origin,
    v_yango_receivable_payable_detail.payer,
    v_yango_receivable_payable_detail.milestone_type,
    v_yango_receivable_payable_detail.milestone_value,
    v_yango_receivable_payable_detail.window_days,
    v_yango_receivable_payable_detail.trips_in_window,
    v_yango_receivable_payable_detail.person_key,
    v_yango_receivable_payable_detail.driver_id,
    v_yango_receivable_payable_detail.amount,
    v_yango_receivable_payable_detail.currency,
    v_yango_receivable_payable_detail.created_at_export
   FROM ops.v_yango_receivable_payable_detail;