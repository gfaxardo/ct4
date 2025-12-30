-- ============================================================================
-- Vista: ops.v_cabinet_payment_evidence_pack
-- ============================================================================
-- PROPÓSITO:
-- Vista "Evidence Pack" que permite responder a Yango: "este pago corresponde 
-- a este conductor" con evidencia clara. Combina claims canónicos con datos 
-- del ledger para proporcionar trazabilidad completa de la relación 
-- claim-payment.
--
-- OPTIMIZACIÓN: Usa los datos de v_claims_payment_status_cabinet cuando 
-- están disponibles y solo hace JOIN adicional con ledger para casos especiales.
-- ============================================================================

CREATE OR REPLACE VIEW ops.v_cabinet_payment_evidence_pack AS
WITH claims_base AS (
    -- Base de claims desde la vista de status (ya tiene los datos básicos del pago)
    SELECT 
        driver_id AS claim_driver_id,
        person_key AS claim_person_key,
        milestone_value AS claim_milestone_value,
        lead_date,
        due_date,
        expected_amount,
        paid_flag,
        payment_status,
        reason_code,
        action_priority,
        payment_key,
        paid_date AS pay_date,
        payment_identity_status AS identity_status,
        payment_match_rule AS match_rule,
        payment_match_confidence AS match_confidence
    FROM ops.v_claims_payment_status_cabinet
),
-- Para pago exacto, obtener datos adicionales del ledger usando payment_key
ledger_exact AS (
    SELECT DISTINCT ON (c.claim_driver_id, c.claim_milestone_value)
        c.claim_driver_id,
        c.claim_milestone_value,
        l.driver_id_final AS ledger_driver_id_final,
        l.person_key_original AS ledger_person_key_original,
        l.milestone_value AS ledger_milestone_value
    FROM claims_base c
    INNER JOIN ops.v_yango_payments_ledger_latest_enriched l
        ON l.payment_key = c.payment_key
    WHERE c.payment_key IS NOT NULL
        AND c.paid_flag = true
),
-- Para otro milestone, obtener datos del pago encontrado
ledger_other_milestone AS (
    SELECT DISTINCT ON (c.claim_driver_id, c.claim_milestone_value)
        c.claim_driver_id,
        c.claim_milestone_value,
        l.payment_key AS payment_key_other,
        l.pay_date AS pay_date_other,
        l.milestone_value AS milestone_paid,
        l.driver_id_final AS ledger_driver_id_final_other,
        l.person_key_original AS ledger_person_key_original_other,
        l.identity_status AS identity_status_other,
        l.match_rule AS match_rule_other,
        l.match_confidence AS match_confidence_other
    FROM claims_base c
    INNER JOIN ops.v_yango_payments_ledger_latest_enriched l
        ON l.driver_id_final = c.claim_driver_id
        AND l.milestone_value != c.claim_milestone_value
        AND l.is_paid = true
    WHERE c.reason_code = 'payment_found_other_milestone'
    ORDER BY c.claim_driver_id, c.claim_milestone_value, l.pay_date DESC, l.payment_key DESC
)
SELECT 
    -- Campos del claim
    c.claim_driver_id,
    c.claim_person_key,
    c.claim_milestone_value,
    c.lead_date,
    c.due_date,
    c.expected_amount,
    c.payment_status,
    c.reason_code,
    c.action_priority,
    c.paid_flag,
    
    -- Campos del pago
    COALESCE(c.payment_key, l_other.payment_key_other) AS payment_key,
    COALESCE(c.pay_date, l_other.pay_date_other) AS pay_date,
    
    -- Campos del ledger
    COALESCE(l_exact.ledger_driver_id_final, l_other.ledger_driver_id_final_other, c.claim_driver_id) AS ledger_driver_id_final,
    COALESCE(l_exact.ledger_person_key_original, l_other.ledger_person_key_original_other, c.claim_person_key) AS ledger_person_key_original,
    COALESCE(l_exact.ledger_milestone_value, l_other.milestone_paid, c.claim_milestone_value) AS ledger_milestone_value,
    COALESCE(c.identity_status, l_other.identity_status_other) AS identity_status,
    COALESCE(c.match_rule, l_other.match_rule_other) AS match_rule,
    COALESCE(c.match_confidence, l_other.match_confidence_other) AS match_confidence,
    
    -- Milestone del pago cuando es otro milestone
    l_other.milestone_paid,
    
    -- evidence_level: nivel de evidencia de la relación claim-payment
    CASE 
        WHEN c.payment_key IS NOT NULL AND c.paid_flag = true THEN 'driver_id_exact'
        WHEN l_other.payment_key_other IS NOT NULL THEN 'other_milestone'
        ELSE 'none'
    END AS evidence_level

FROM claims_base c
LEFT JOIN ledger_exact l_exact 
    ON l_exact.claim_driver_id = c.claim_driver_id 
    AND l_exact.claim_milestone_value = c.claim_milestone_value
LEFT JOIN ledger_other_milestone l_other
    ON l_other.claim_driver_id = c.claim_driver_id
    AND l_other.claim_milestone_value = c.claim_milestone_value;

-- ============================================================================
-- Comentarios de la Vista
-- ============================================================================
COMMENT ON VIEW ops.v_cabinet_payment_evidence_pack IS 
'Vista "Evidence Pack" que permite responder a Yango: "este pago corresponde a este conductor" con evidencia clara. Combina claims canónicos con datos del ledger para proporcionar trazabilidad completa de la relación claim-payment. Devuelve exactamente 1 fila por claim (driver_id + milestone).';

COMMENT ON COLUMN ops.v_cabinet_payment_evidence_pack.claim_driver_id IS 
'Driver ID del claim canónico.';

COMMENT ON COLUMN ops.v_cabinet_payment_evidence_pack.claim_person_key IS 
'Person key del claim canónico.';

COMMENT ON COLUMN ops.v_cabinet_payment_evidence_pack.claim_milestone_value IS 
'Milestone value del claim canónico (1, 5, o 25).';

COMMENT ON COLUMN ops.v_cabinet_payment_evidence_pack.expected_amount IS 
'Monto esperado del claim.';

COMMENT ON COLUMN ops.v_cabinet_payment_evidence_pack.due_date IS 
'Fecha de vencimiento del claim.';

COMMENT ON COLUMN ops.v_cabinet_payment_evidence_pack.payment_status IS 
'Estado de pago: ''paid'' o ''not_paid''.';

COMMENT ON COLUMN ops.v_cabinet_payment_evidence_pack.reason_code IS 
'Código de razón del estado de pago.';

COMMENT ON COLUMN ops.v_cabinet_payment_evidence_pack.action_priority IS 
'Prioridad operativa para cobranza.';

COMMENT ON COLUMN ops.v_cabinet_payment_evidence_pack.paid_flag IS 
'Boolean indicando si el claim tiene pago asociado.';

COMMENT ON COLUMN ops.v_cabinet_payment_evidence_pack.payment_key IS 
'Payment key del pago asociado (exacto o de otro milestone).';

COMMENT ON COLUMN ops.v_cabinet_payment_evidence_pack.pay_date IS 
'Fecha del pago asociado.';

COMMENT ON COLUMN ops.v_cabinet_payment_evidence_pack.ledger_driver_id_final IS 
'Driver ID final del ledger.';

COMMENT ON COLUMN ops.v_cabinet_payment_evidence_pack.ledger_person_key_original IS 
'Person key original del ledger.';

COMMENT ON COLUMN ops.v_cabinet_payment_evidence_pack.ledger_milestone_value IS 
'Milestone value del pago en el ledger.';

COMMENT ON COLUMN ops.v_cabinet_payment_evidence_pack.identity_status IS 
'Estado de identidad del pago: confirmed, enriched, ambiguous, no_match.';

COMMENT ON COLUMN ops.v_cabinet_payment_evidence_pack.match_rule IS 
'Regla de matching del pago: source_upstream, name_unique, ambiguous, no_match.';

COMMENT ON COLUMN ops.v_cabinet_payment_evidence_pack.match_confidence IS 
'Confianza del matching: high, medium, low.';

COMMENT ON COLUMN ops.v_cabinet_payment_evidence_pack.milestone_paid IS 
'Milestone del pago encontrado cuando reason_code=''payment_found_other_milestone''.';

COMMENT ON COLUMN ops.v_cabinet_payment_evidence_pack.evidence_level IS 
'Nivel de evidencia: ''driver_id_exact'' (driver_id matchea exactamente), ''person_key_only'' (solo person_key matchea), ''other_milestone'' (hay pago para otro milestone), ''none'' (no hay pago).';
