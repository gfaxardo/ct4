DROP VIEW IF EXISTS ops.v_yango_payments_claims_cabinet_14d CASCADE;

CREATE VIEW ops.v_yango_payments_claims_cabinet_14d AS
-- Performance: filter pushdown before joins for UI stability
-- Apply date filter early to reduce data volume before expensive LEFT JOINs
WITH base_claims AS (
    SELECT 
        driver_id,
        person_key,
        lead_date,
        pay_week_start_monday,
        milestone_value,
        amount AS expected_amount,
        currency
    FROM ops.v_yango_receivable_payable_detail
    WHERE lead_origin = 'cabinet'
        AND milestone_value IN (1, 5, 25)
        -- Performance: filter by date BEFORE expensive JOINs to reduce data volume
        -- Default filter: last 1 week (7 days) from start of current week (very aggressive for UI stability)
        AND pay_week_start_monday >= (date_trunc('week', current_date)::date - interval '7 days')::date
),
-- Usar ledger enriquecido para matching
-- Performance: filter ledger by pay_date BEFORE expensive JOINs to reduce scan volume
ledger_enriched AS (
    SELECT 
        driver_id_final AS driver_id,
        person_key_original AS person_key,
        payment_key,
        pay_date,
        is_paid,
        milestone_value,
        match_rule,
        match_confidence,
        identity_status,
        identity_enriched
    FROM ops.v_yango_payments_ledger_latest_enriched
    WHERE pay_date >= (date_trunc('week', current_date)::date - interval '7 days')::date
        -- Only include paid records for matching (reduces volume significantly)
        AND is_paid = true
)
SELECT 
    e.driver_id,
    e.person_key,
    e.lead_date,
    e.pay_week_start_monday,
    e.milestone_value,
    e.expected_amount,
    e.currency,
    e.lead_date + INTERVAL '14 days' AS due_date,
    CASE 
        WHEN CURRENT_DATE <= (e.lead_date + INTERVAL '14 days') THEN 'active'
        ELSE 'expired'
    END AS window_status,
    -- Campos de paid_confirmed (identity_status='confirmed')
    p_confirmed.payment_key AS paid_payment_key_confirmed,
    p_confirmed.pay_date AS paid_date_confirmed,
    COALESCE(p_confirmed.is_paid, false) AS is_paid_confirmed,
    -- Campos de paid_enriched (identity_status='enriched')
    p_enriched.payment_key AS paid_payment_key_enriched,
    p_enriched.pay_date AS paid_date_enriched,
    COALESCE(p_enriched.is_paid, false) AS is_paid_enriched,
    -- Campos de compatibilidad (usar confirmed primero, luego enriched para visibilidad)
    COALESCE(p_confirmed.payment_key, p_enriched.payment_key) AS paid_payment_key,
    COALESCE(p_confirmed.pay_date, p_enriched.pay_date) AS paid_date,
    COALESCE(p_confirmed.is_paid, p_enriched.is_paid, false) AS paid_is_paid,
    -- is_paid_effective: solo confirmed cuenta como paid real
    COALESCE(p_confirmed.is_paid, false) AS is_paid_effective,
    -- match_method
    CASE 
        WHEN e.driver_id IS NOT NULL AND p_confirmed.payment_key IS NOT NULL THEN 'driver_id'
        WHEN e.driver_id IS NULL AND e.person_key IS NOT NULL AND p_confirmed.payment_key IS NOT NULL THEN 'person_key'
        WHEN e.driver_id IS NOT NULL AND p_enriched.payment_key IS NOT NULL THEN 'driver_id_enriched'
        WHEN e.driver_id IS NULL AND e.person_key IS NOT NULL AND p_enriched.payment_key IS NOT NULL THEN 'person_key_enriched'
        ELSE 'none'
    END AS match_method,
    -- paid_status: separar confirmed vs enriched
    CASE 
        WHEN p_confirmed.is_paid = true THEN 'paid_confirmed'
        WHEN p_enriched.is_paid = true THEN 'paid_enriched'
        WHEN CURRENT_DATE <= (e.lead_date + INTERVAL '14 days') THEN 'pending_active'
        ELSE 'pending_expired'
    END AS paid_status
FROM base_claims e
LEFT JOIN ledger_enriched p_confirmed
    ON (
        (e.driver_id IS NOT NULL AND p_confirmed.driver_id = e.driver_id)
        OR (e.driver_id IS NULL AND e.person_key IS NOT NULL AND p_confirmed.person_key = e.person_key AND p_confirmed.driver_id IS NULL)
    )
    AND p_confirmed.milestone_value = e.milestone_value
    AND p_confirmed.identity_status = 'confirmed'
    AND p_confirmed.is_paid = true
LEFT JOIN ledger_enriched p_enriched
    ON (
        (e.driver_id IS NOT NULL AND p_enriched.driver_id = e.driver_id)
        OR (e.driver_id IS NULL AND e.person_key IS NOT NULL AND p_enriched.person_key = e.person_key AND p_enriched.driver_id IS NULL)
    )
    AND p_enriched.milestone_value = e.milestone_value
    AND p_enriched.identity_status = 'enriched'
    AND p_enriched.is_paid = true
ORDER BY 
    e.pay_week_start_monday DESC,
    e.lead_date DESC,
    e.milestone_value;

COMMENT ON VIEW ops.v_yango_payments_claims_cabinet_14d IS 
'Vista de claims de pagos Yango Cabinet (ventana 14 días). Separa paid_confirmed (identity_status=confirmed desde upstream) vs paid_enriched (identity_status=enriched por matching por nombre). paid_confirmed es la fuente para paid real, paid_enriched es informativo. Performance: filter pushdown before joins for UI stability - applies 1-week (7 days) default filter in base_claims CTE AND ledger_enriched CTE before expensive LEFT JOINs to reduce scan volume.';

COMMENT ON COLUMN ops.v_yango_payments_claims_cabinet_14d.paid_status IS 
'Estado de pago: paid_confirmed (identity confirmada desde upstream), paid_enriched (identity enriquecida por nombre), pending_active (dentro de ventana), pending_expired (fuera de ventana).';
