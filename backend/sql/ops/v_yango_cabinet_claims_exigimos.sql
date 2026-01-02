-- ============================================================================
-- Vista: Claims Exigimos a Yango (No Pagados)
-- ============================================================================
-- PROPÓSITO:
-- Vista READ-ONLY que lista los claims de nuestros leads cabinet que NO están pagados.
-- Usada para reclamo formal a Yango.
--
-- DEFINICIÓN CANÓNICA:
-- - Universo: leads de nuestro cabinet (tabla cabinet_leads) que tienen driver_id 
--   y alcanzaron milestones según nuestra fuente de producción/claims.
-- - Pago exigible Yango:
--   - milestone 1 => S/25
--   - milestone 5 => S/35 adicionales
--   - milestone 25 => S/100 adicionales
-- - Campo esperado por milestone viene de ops.mv_yango_cabinet_claims_for_collection
--
-- FILTRO:
-- Solo claims NO pagados: yango_payment_status = 'UNPAID' 
-- o reason_code = 'no_payment_found'
-- ============================================================================

CREATE OR REPLACE VIEW ops.v_yango_cabinet_claims_exigimos AS
SELECT 
    -- Identificador único del claim
    MD5(
        COALESCE(driver_id::text, 'NULL') || '|' ||
        milestone_value::text || '|' ||
        COALESCE(lead_date::text, 'NULL')
    ) AS claim_key,
    
    -- Identificación
    person_key,
    driver_id,
    driver_name,
    milestone_value,
    lead_date,
    
    -- Monto exigible
    expected_amount,
    
    -- Fechas
    yango_due_date,
    days_overdue_yango,
    overdue_bucket_yango,
    
    -- Estado de pago
    yango_payment_status,
    reason_code,
    
    -- Identidad y matching
    identity_status,
    match_rule,
    match_confidence,
    is_reconcilable_enriched,
    
    -- Campos adicionales para contexto
    payment_key,
    pay_date,
    suggested_driver_id
    
FROM ops.mv_yango_cabinet_claims_for_collection
WHERE 
    -- Solo claims NO pagados
    yango_payment_status = 'UNPAID'
    -- Asegurar que tenemos driver_id (requisito: leads con driver_id)
    AND driver_id IS NOT NULL
    -- Solo milestones válidos
    AND milestone_value IN (1, 5, 25);

-- ============================================================================
-- Comentarios
-- ============================================================================
COMMENT ON VIEW ops.v_yango_cabinet_claims_exigimos IS 
'Vista READ-ONLY de claims NO pagados de nuestros leads cabinet. Usada para reclamo formal a Yango. Filtra solo claims con yango_payment_status = UNPAID y driver_id NOT NULL. Montos: milestone 1=S/25, 5=S/35, 25=S/100.';

COMMENT ON COLUMN ops.v_yango_cabinet_claims_exigimos.claim_key IS 
'Identificador único del claim: MD5(driver_id|milestone_value|lead_date).';

COMMENT ON COLUMN ops.v_yango_cabinet_claims_exigimos.expected_amount IS 
'Monto exigible según milestone: 1=S/25, 5=S/35, 25=S/100. Viene de ops.mv_yango_cabinet_claims_for_collection.';

COMMENT ON COLUMN ops.v_yango_cabinet_claims_exigimos.yango_payment_status IS 
'Estado de pago: UNPAID (no pagado). Solo se incluyen claims con este estado.';

COMMENT ON COLUMN ops.v_yango_cabinet_claims_exigimos.is_reconcilable_enriched IS 
'Flag indicando si el claim es reconciliable usando identidad enriquecida. TRUE si identity_status IN (confirmed, enriched) AND match_confidence alto.';

