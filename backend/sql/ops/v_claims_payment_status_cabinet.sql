-- ============================================================================
-- Vista: ops.v_claims_payment_status_cabinet
-- ============================================================================
-- OBJETIVO:
-- Responder sin ambigüedad: "Para cada conductor que entró por cabinet y 
-- alcanzó un milestone, ¿nos pagaron o no?"
--
-- REGLAS DE NEGOCIO:
-- 1. Universo: Solo drivers que entraron por cabinet. Solo milestones 1, 5, 25.
-- 2. Un claim = (driver_id + milestone_value).
-- 3. Un claim se considera PAGADO si existe AL MENOS UN pago en 
--    ops.v_yango_payments_ledger_latest_enriched con:
--    - is_paid = true
--    - driver_id_final = driver_id
--    - milestone_value = milestone_value
--    - SIN filtrar por identity_status
--    - SIN filtrar por ventana de fecha del pago
-- 4. Si no existe pago → NO PAGADO.
-- 5. NO calcular montos en frontend. Todo sale de SQL.
--
-- IMPLEMENTACIÓN:
-- - Usar LEFT JOIN LATERAL para buscar el ÚLTIMO pago válido por 
--   driver_id + milestone_value.
-- - Priorizar simplicidad y trazabilidad.
-- - NO usar filtros de fecha sobre el ledger.
-- ============================================================================

CREATE OR REPLACE VIEW ops.v_claims_payment_status_cabinet AS
WITH base_claims AS (
    SELECT 
        driver_id,
        person_key,
        lead_date,
        milestone_value,
        amount AS expected_amount
    FROM ops.v_yango_receivable_payable_detail
    WHERE lead_origin = 'cabinet'
        AND milestone_value IN (1, 5, 25)
)
SELECT 
    c.driver_id,
    c.person_key,
    c.milestone_value,
    c.lead_date,
    c.lead_date + INTERVAL '14 days' AS due_date,
    c.expected_amount,
    -- paid_flag: boolean indicando si existe al menos un pago
    (p.payment_key IS NOT NULL) AS paid_flag,
    -- paid_date: última fecha de pago si existe
    p.pay_date AS paid_date,
    -- payment_key: si existe
    p.payment_key,
    -- payment_identity_status: si existe
    p.identity_status AS payment_identity_status,
    -- payment_match_rule: si existe
    p.match_rule AS payment_match_rule,
    -- payment_match_confidence: si existe
    p.match_confidence AS payment_match_confidence,
    -- payment_status: ENUM TEXT
    CASE 
        WHEN p.payment_key IS NOT NULL THEN 'paid'
        ELSE 'not_paid'
    END AS payment_status,
    -- payment_reason: TEXT
    CASE 
        WHEN p.payment_key IS NOT NULL THEN 'payment_found'
        ELSE 'no_payment_found'
    END AS payment_reason
FROM base_claims c
LEFT JOIN LATERAL (
    SELECT 
        payment_key,
        pay_date,
        identity_status,
        match_rule,
        match_confidence
    FROM ops.v_yango_payments_ledger_latest_enriched
    WHERE driver_id_final = c.driver_id
        AND milestone_value = c.milestone_value
        AND is_paid = true
    ORDER BY pay_date DESC, payment_key DESC
    LIMIT 1
) p ON true;

COMMENT ON VIEW ops.v_claims_payment_status_cabinet IS 
'Vista FINAL, SIMPLE y ORIENTADA A NEGOCIO que responde: "Para cada conductor que entró por cabinet y alcanzó un milestone, ¿nos pagaron o no?". Un claim = (driver_id + milestone_value). Un claim se considera PAGADO si existe AL MENOS UN pago en ops.v_yango_payments_ledger_latest_enriched con is_paid=true que matchee driver_id_final=driver_id y milestone_value=milestone_value, SIN filtrar por identity_status ni por ventana de fecha. Devuelve exactamente 1 fila por claim (driver_id + milestone).';

COMMENT ON COLUMN ops.v_claims_payment_status_cabinet.driver_id IS 
'ID del conductor que entró por cabinet.';

COMMENT ON COLUMN ops.v_claims_payment_status_cabinet.person_key IS 
'Person key del conductor.';

COMMENT ON COLUMN ops.v_claims_payment_status_cabinet.milestone_value IS 
'Valor del milestone alcanzado (1, 5, o 25).';

COMMENT ON COLUMN ops.v_claims_payment_status_cabinet.lead_date IS 
'Fecha en que el conductor entró por cabinet.';

COMMENT ON COLUMN ops.v_claims_payment_status_cabinet.due_date IS 
'Fecha de vencimiento del claim (lead_date + 14 días).';

COMMENT ON COLUMN ops.v_claims_payment_status_cabinet.expected_amount IS 
'Monto esperado del claim.';

COMMENT ON COLUMN ops.v_claims_payment_status_cabinet.paid_flag IS 
'Boolean indicando si el claim tiene al menos un pago asociado (is_paid=true).';

COMMENT ON COLUMN ops.v_claims_payment_status_cabinet.paid_date IS 
'Última fecha de pago si existe, NULL si no hay pago.';

COMMENT ON COLUMN ops.v_claims_payment_status_cabinet.payment_key IS 
'Payment key del pago asociado si existe, NULL si no hay pago.';

COMMENT ON COLUMN ops.v_claims_payment_status_cabinet.payment_identity_status IS 
'Estado de identidad del pago (confirmed, enriched, ambiguous, no_match) si existe, NULL si no hay pago.';

COMMENT ON COLUMN ops.v_claims_payment_status_cabinet.payment_match_rule IS 
'Regla de matching del pago (source_upstream, name_unique, ambiguous, no_match) si existe, NULL si no hay pago.';

COMMENT ON COLUMN ops.v_claims_payment_status_cabinet.payment_match_confidence IS 
'Confianza del matching del pago (high, medium, low) si existe, NULL si no hay pago.';

COMMENT ON COLUMN ops.v_claims_payment_status_cabinet.payment_status IS 
'Estado de pago: ''paid'' si existe al menos un pago, ''not_paid'' si no existe pago.';

COMMENT ON COLUMN ops.v_claims_payment_status_cabinet.payment_reason IS 
'Razón del estado de pago: ''payment_found'' si existe pago, ''no_payment_found'' si no existe pago.';


