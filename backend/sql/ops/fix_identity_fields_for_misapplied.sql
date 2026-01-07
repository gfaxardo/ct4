-- ============================================================================
-- Fix: Obtener campos de identidad para PAID_MISAPPLIED
-- ============================================================================
-- PROBLEMA: Cuando reason_code = 'payment_found_other_milestone', los campos
-- payment_identity_status, payment_match_rule, payment_match_confidence son NULL
-- porque solo vienen de p_exact (pago exacto), pero en misapplied no hay pago exacto.
-- SOLUCIÓN: Obtener estos campos del pago en otro milestone cuando aplica.
-- ============================================================================

-- Actualizar v_claims_payment_status_cabinet
CREATE OR REPLACE VIEW ops.v_claims_payment_status_cabinet AS
WITH base_claims_raw AS (
    SELECT 
        driver_id,
        person_key,
        lead_date,
        milestone_value,
        amount AS expected_amount_raw
    FROM ops.mv_yango_receivable_payable_detail
    WHERE lead_origin = 'cabinet'
        AND milestone_value IN (1, 5, 25)
),
base_claims_dedup AS (
    SELECT DISTINCT ON (driver_id, milestone_value)
        driver_id,
        person_key,
        lead_date,
        milestone_value,
        expected_amount_raw,
        CASE 
            WHEN milestone_value = 1 THEN 25::numeric(12,2)
            WHEN milestone_value = 5 THEN 35::numeric(12,2)
            WHEN milestone_value = 25 THEN 100::numeric(12,2)
            ELSE expected_amount_raw
        END AS expected_amount
    FROM base_claims_raw
    ORDER BY driver_id, milestone_value, lead_date DESC
),
base_claims AS (
    SELECT 
        driver_id,
        person_key,
        lead_date,
        milestone_value,
        expected_amount
    FROM base_claims_dedup
)
SELECT 
    c.driver_id,
    c.person_key,
    c.milestone_value,
    c.lead_date,
    c.lead_date + INTERVAL '14 days' AS due_date,
    c.expected_amount,
    
    -- Aging: cálculo de días vencidos y bucket
    GREATEST(0, CURRENT_DATE - (c.lead_date + INTERVAL '14 days')::date) AS days_overdue,
    CASE 
        WHEN (c.lead_date + INTERVAL '14 days')::date >= CURRENT_DATE THEN '0_not_due'
        WHEN (CURRENT_DATE - (c.lead_date + INTERVAL '14 days')::date) BETWEEN 1 AND 7 THEN '1_1_7'
        WHEN (CURRENT_DATE - (c.lead_date + INTERVAL '14 days')::date) BETWEEN 8 AND 14 THEN '2_8_14'
        WHEN (CURRENT_DATE - (c.lead_date + INTERVAL '14 days')::date) BETWEEN 15 AND 30 THEN '3_15_30'
        WHEN (CURRENT_DATE - (c.lead_date + INTERVAL '14 days')::date) BETWEEN 31 AND 60 THEN '4_31_60'
        ELSE '5_60_plus'
    END AS bucket_overdue,
    
    -- Pago exacto: driver_id + milestone matching (usando LATERAL JOIN)
    (p_exact.payment_key IS NOT NULL) AS paid_flag,
    COALESCE(p_exact.pay_date, p_other_milestone.pay_date, p_person_key.pay_date) AS paid_date,
    COALESCE(p_exact.payment_key, p_other_milestone.payment_key, p_person_key.payment_key) AS payment_key,
    -- FIX: Obtener campos de identidad del pago correcto (exacto, otro milestone, o person_key)
    COALESCE(p_exact.identity_status, p_other_milestone.identity_status, p_person_key.identity_status) AS payment_identity_status,
    COALESCE(p_exact.match_rule, p_other_milestone.match_rule, p_person_key.match_rule) AS payment_match_rule,
    COALESCE(p_exact.match_confidence, p_other_milestone.match_confidence, p_person_key.match_confidence) AS payment_match_confidence,
    
    -- payment_status: ENUM TEXT (mantener compatibilidad)
    CASE 
        WHEN p_exact.payment_key IS NOT NULL THEN 'paid'
        ELSE 'not_paid'
    END AS payment_status,
    
    -- payment_reason: TEXT (mantener compatibilidad, pero será reemplazado por reason_code)
    CASE 
        WHEN p_exact.payment_key IS NOT NULL THEN 'payment_found'
        ELSE 'no_payment_found'
    END AS payment_reason,
    
    -- reason_code: diagnóstico detallado con prioridad
    CASE 
        WHEN p_exact.payment_key IS NOT NULL THEN 'paid'
        WHEN c.driver_id IS NULL THEN 'missing_driver_id'
        WHEN c.milestone_value IS NULL THEN 'missing_milestone'
        WHEN p_other_milestone.payment_key IS NOT NULL THEN 'payment_found_other_milestone'
        WHEN p_person_key.payment_key IS NOT NULL THEN 'payment_found_person_key_only'
        ELSE 'no_payment_found'
    END AS reason_code,
    
    -- action_priority: prioridad operativa para cobranza
    CASE 
        WHEN p_exact.payment_key IS NOT NULL THEN 'P0_confirmed_paid'
        WHEN (c.lead_date + INTERVAL '14 days')::date >= CURRENT_DATE THEN 'P2_not_due'
        WHEN (CURRENT_DATE - (c.lead_date + INTERVAL '14 days')::date) BETWEEN 8 AND 14 THEN 'P1_watch'
        WHEN (CURRENT_DATE - (c.lead_date + INTERVAL '14 days')::date) >= 15 THEN 'P0_collect_now'
        ELSE 'P2_not_due'
    END AS action_priority

FROM base_claims c
LEFT JOIN LATERAL (
    -- Pago exacto: driver_id + milestone matching
    SELECT 
        payment_key,
        pay_date,
        identity_status,
        match_rule,
        match_confidence
    FROM ops.mv_yango_payments_ledger_latest_enriched
    WHERE driver_id_final = c.driver_id
        AND milestone_value = c.milestone_value
        AND is_paid = true
    ORDER BY pay_date DESC, payment_key DESC
    LIMIT 1
) p_exact ON true
-- FIX: Obtener también campos de identidad del pago en otro milestone
LEFT JOIN LATERAL (
    -- ¿Existe pago para este driver pero otro milestone?
    SELECT 
        payment_key,
        pay_date,
        identity_status,
        match_rule,
        match_confidence
    FROM ops.mv_yango_payments_ledger_latest_enriched p
    WHERE p.driver_id_final = c.driver_id
        AND p.milestone_value != c.milestone_value
        AND p.is_paid = true
    ORDER BY pay_date DESC, payment_key DESC
    LIMIT 1
) p_other_milestone ON p_exact.payment_key IS NULL 
    AND c.driver_id IS NOT NULL
    AND c.milestone_value IS NOT NULL
-- FIX: Obtener también campos de identidad del pago por person_key
LEFT JOIN LATERAL (
    -- ¿Existe pago para este milestone pero solo por person_key?
    SELECT 
        payment_key,
        pay_date,
        identity_status,
        match_rule,
        match_confidence
    FROM ops.mv_yango_payments_ledger_latest_enriched p
    WHERE p.milestone_value = c.milestone_value
        AND p.is_paid = true
        AND p.person_key_final = c.person_key
        AND (p.driver_id_final IS NULL OR p.driver_id_final != c.driver_id)
    ORDER BY pay_date DESC, payment_key DESC
    LIMIT 1
) p_person_key ON p_exact.payment_key IS NULL 
    AND p_other_milestone.payment_key IS NULL
    AND c.person_key IS NOT NULL
    AND c.driver_id IS NOT NULL
    AND c.milestone_value IS NOT NULL;













