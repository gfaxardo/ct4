-- Definicion completa de ops.v_claims_payment_status_cabinet
-- Generado por analisis de causa raiz M5 sin M1

 WITH base_claims_raw AS (
         SELECT mv_yango_receivable_payable_detail.driver_id,
            mv_yango_receivable_payable_detail.person_key,
            mv_yango_receivable_payable_detail.lead_date,
            mv_yango_receivable_payable_detail.milestone_value,
            mv_yango_receivable_payable_detail.amount AS expected_amount_raw
           FROM ops.mv_yango_receivable_payable_detail
          WHERE mv_yango_receivable_payable_detail.lead_origin = 'cabinet'::text AND (mv_yango_receivable_payable_detail.milestone_value = ANY (ARRAY[1, 5, 25]))
        ), base_claims_dedup AS (
         SELECT DISTINCT ON (base_claims_raw.driver_id, base_claims_raw.milestone_value) base_claims_raw.driver_id,
            base_claims_raw.person_key,
            base_claims_raw.lead_date,
            base_claims_raw.milestone_value,
            base_claims_raw.expected_amount_raw,
                CASE
                    WHEN base_claims_raw.milestone_value = 1 THEN 25::numeric(12,2)
                    WHEN base_claims_raw.milestone_value = 5 THEN 35::numeric(12,2)
                    WHEN base_claims_raw.milestone_value = 25 THEN 100::numeric(12,2)
                    ELSE base_claims_raw.expected_amount_raw
                END AS expected_amount
           FROM base_claims_raw
          ORDER BY base_claims_raw.driver_id, base_claims_raw.milestone_value, base_claims_raw.lead_date DESC
        ), base_claims AS (
         SELECT base_claims_dedup.driver_id,
            base_claims_dedup.person_key,
            base_claims_dedup.lead_date,
            base_claims_dedup.milestone_value,
            base_claims_dedup.expected_amount
           FROM base_claims_dedup
        )
 SELECT c.driver_id,
    c.person_key,
    c.milestone_value,
    c.lead_date,
    c.lead_date + '14 days'::interval AS due_date,
    c.expected_amount,
    GREATEST(0, CURRENT_DATE - (c.lead_date + '14 days'::interval)::date) AS days_overdue,
        CASE
            WHEN (c.lead_date + '14 days'::interval)::date >= CURRENT_DATE THEN '0_not_due'::text
            WHEN (CURRENT_DATE - (c.lead_date + '14 days'::interval)::date) >= 1 AND (CURRENT_DATE - (c.lead_date + '14 days'::interval)::date) <= 7 THEN '1_1_7'::text
            WHEN (CURRENT_DATE - (c.lead_date + '14 days'::interval)::date) >= 8 AND (CURRENT_DATE - (c.lead_date + '14 days'::interval)::date) <= 14 THEN '2_8_14'::text
            WHEN (CURRENT_DATE - (c.lead_date + '14 days'::interval)::date) >= 15 AND (CURRENT_DATE - (c.lead_date + '14 days'::interval)::date) <= 30 THEN '3_15_30'::text
            WHEN (CURRENT_DATE - (c.lead_date + '14 days'::interval)::date) >= 31 AND (CURRENT_DATE - (c.lead_date + '14 days'::interval)::date) <= 60 THEN '4_31_60'::text
            ELSE '5_60_plus'::text
        END AS bucket_overdue,
    p_exact.payment_key IS NOT NULL AS paid_flag,
    COALESCE(p_exact.pay_date, p_other_milestone.pay_date, p_person_key.pay_date) AS paid_date,
    COALESCE(p_exact.payment_key, p_other_milestone.payment_key, p_person_key.payment_key) AS payment_key,
    COALESCE(p_exact.identity_status, p_other_milestone.identity_status, p_person_key.identity_status) AS payment_identity_status,
    COALESCE(p_exact.match_rule, p_other_milestone.match_rule, p_person_key.match_rule) AS payment_match_rule,
    COALESCE(p_exact.match_confidence, p_other_milestone.match_confidence, p_person_key.match_confidence) AS payment_match_confidence,
        CASE
            WHEN p_exact.payment_key IS NOT NULL THEN 'paid'::text
            ELSE 'not_paid'::text
        END AS payment_status,
        CASE
            WHEN p_exact.payment_key IS NOT NULL THEN 'payment_found'::text
            ELSE 'no_payment_found'::text
        END AS payment_reason,
        CASE
            WHEN p_exact.payment_key IS NOT NULL THEN 'paid'::text
            WHEN c.driver_id IS NULL THEN 'missing_driver_id'::text
            WHEN c.milestone_value IS NULL THEN 'missing_milestone'::text
            WHEN p_other_milestone.payment_key IS NOT NULL THEN 'payment_found_other_milestone'::text
            WHEN p_person_key.payment_key IS NOT NULL THEN 'payment_found_person_key_only'::text
            ELSE 'no_payment_found'::text
        END AS reason_code,
        CASE
            WHEN p_exact.payment_key IS NOT NULL THEN 'P0_confirmed_paid'::text
            WHEN (c.lead_date + '14 days'::interval)::date >= CURRENT_DATE THEN 'P2_not_due'::text
            WHEN (CURRENT_DATE - (c.lead_date + '14 days'::interval)::date) >= 8 AND (CURRENT_DATE - (c.lead_date + '14 days'::interval)::date) <= 14 THEN 'P1_watch'::text
            WHEN (CURRENT_DATE - (c.lead_date + '14 days'::interval)::date) >= 15 THEN 'P0_collect_now'::text
            ELSE 'P2_not_due'::text
        END AS action_priority
   FROM base_claims c
     LEFT JOIN LATERAL ( SELECT mv_yango_payments_ledger_latest_enriched.payment_key,
            mv_yango_payments_ledger_latest_enriched.pay_date,
            mv_yango_payments_ledger_latest_enriched.identity_status,
            mv_yango_payments_ledger_latest_enriched.match_rule,
            mv_yango_payments_ledger_latest_enriched.match_confidence
           FROM ops.mv_yango_payments_ledger_latest_enriched
          WHERE mv_yango_payments_ledger_latest_enriched.driver_id_final = c.driver_id::text AND mv_yango_payments_ledger_latest_enriched.milestone_value = c.milestone_value AND mv_yango_payments_ledger_latest_enriched.is_paid = true
          ORDER BY mv_yango_payments_ledger_latest_enriched.pay_date DESC, mv_yango_payments_ledger_latest_enriched.payment_key DESC
         LIMIT 1) p_exact ON true
     LEFT JOIN LATERAL ( SELECT p.payment_key,
            p.pay_date,
            p.identity_status,
            p.match_rule,
            p.match_confidence
           FROM ops.mv_yango_payments_ledger_latest_enriched p
          WHERE p.driver_id_final = c.driver_id::text AND p.milestone_value <> c.milestone_value AND p.is_paid = true
          ORDER BY p.pay_date DESC, p.payment_key DESC
         LIMIT 1) p_other_milestone ON p_exact.payment_key IS NULL AND c.driver_id IS NOT NULL AND c.milestone_value IS NOT NULL
     LEFT JOIN LATERAL ( SELECT p.payment_key,
            p.pay_date,
            p.identity_status,
            p.match_rule,
            p.match_confidence
           FROM ops.mv_yango_payments_ledger_latest_enriched p
          WHERE p.milestone_value = c.milestone_value AND p.is_paid = true AND p.person_key_final = c.person_key AND (p.driver_id_final IS NULL OR p.driver_id_final <> c.driver_id::text)
          ORDER BY p.pay_date DESC, p.payment_key DESC
         LIMIT 1) p_person_key ON p_exact.payment_key IS NULL AND p_other_milestone.payment_key IS NULL AND c.person_key IS NOT NULL AND c.driver_id IS NOT NULL AND c.milestone_value IS NOT NULL;