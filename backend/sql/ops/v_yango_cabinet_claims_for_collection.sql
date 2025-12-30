-- ============================================================================
-- Vista: ops.v_yango_cabinet_claims_for_collection
-- ============================================================================
-- PROPÓSITO DE NEGOCIO:
-- Vista FINAL y cobrable que indica sin interpretación qué Yango debe pagar,
-- qué ya pagó y qué pagó mal. Diseñada para exportación directa a Yango sin
-- edición manual. Basada en ops.v_claims_payment_status_cabinet.
-- ============================================================================
-- REGLAS DE NEGOCIO:
-- 1. Fuente: ops.v_claims_payment_status_cabinet (garantiza 1 fila por claim)
-- 2. Solo claims Cabinet (milestones 1, 5, 25)
-- 3. Sin filtros destructivos (sin WHERE a nivel de vista)
-- 4. Campos derivados calculados desde lead_date (no recalcular reglas)
-- 5. Campo canónico: yango_payment_status (PAID, PAID_MISAPPLIED, UNPAID)
-- ============================================================================

CREATE OR REPLACE VIEW ops.v_yango_cabinet_claims_for_collection AS
SELECT 
    -- Campos de identificación
    c.driver_id,
    c.person_key,
    d.full_name AS driver_name,
    c.milestone_value,
    c.lead_date,
    
    -- Campo de monto (no recalcular, usar de vista base)
    c.expected_amount,
    
    -- Campos derivados Yango
    c.lead_date + INTERVAL '14 days' AS yango_due_date,
    GREATEST(0, CURRENT_DATE - (c.lead_date + INTERVAL '14 days')::date) AS days_overdue_yango,
    CASE 
        WHEN (c.lead_date + INTERVAL '14 days')::date >= CURRENT_DATE THEN '0_not_due'
        WHEN (CURRENT_DATE - (c.lead_date + INTERVAL '14 days')::date) BETWEEN 1 AND 7 THEN '1_1_7'
        WHEN (CURRENT_DATE - (c.lead_date + INTERVAL '14 days')::date) BETWEEN 8 AND 14 THEN '2_8_14'
        WHEN (CURRENT_DATE - (c.lead_date + INTERVAL '14 days')::date) BETWEEN 15 AND 30 THEN '3_15_30'
        ELSE '4_30_plus'
    END AS overdue_bucket_yango,
    
    -- Campo canónico de estado
    CASE
        WHEN c.paid_flag = true THEN 'PAID'
        WHEN c.reason_code = 'payment_found_other_milestone' THEN 'PAID_MISAPPLIED'
        ELSE 'UNPAID'
    END AS yango_payment_status,
    
    -- Campos de evidencia
    c.payment_key,
    c.paid_date AS pay_date,
    c.reason_code,
    c.payment_match_rule AS match_rule,
    c.payment_match_confidence AS match_confidence

FROM ops.v_claims_payment_status_cabinet c
LEFT JOIN public.drivers d ON d.driver_id = c.driver_id;

-- ============================================================================
-- Comentarios de la Vista
-- ============================================================================
COMMENT ON VIEW ops.v_yango_cabinet_claims_for_collection IS 
'Vista FINAL y cobrable para Yango Cabinet. Indica sin interpretación qué Yango debe pagar (UNPAID), qué ya pagó (PAID) y qué pagó mal (PAID_MISAPPLIED). Diseñada para exportación directa sin edición manual. Basada en ops.v_claims_payment_status_cabinet.';

COMMENT ON COLUMN ops.v_yango_cabinet_claims_for_collection.driver_id IS 
'ID del conductor que entró por cabinet.';

COMMENT ON COLUMN ops.v_yango_cabinet_claims_for_collection.person_key IS 
'Person key del conductor (identidad canónica).';

COMMENT ON COLUMN ops.v_yango_cabinet_claims_for_collection.driver_name IS 
'Nombre del conductor desde public.drivers.full_name. Puede ser NULL si no existe en la tabla drivers.';

COMMENT ON COLUMN ops.v_yango_cabinet_claims_for_collection.milestone_value IS 
'Valor del milestone alcanzado (1, 5, o 25).';

COMMENT ON COLUMN ops.v_yango_cabinet_claims_for_collection.lead_date IS 
'Fecha en que el conductor entró por cabinet (para referencia).';

COMMENT ON COLUMN ops.v_yango_cabinet_claims_for_collection.expected_amount IS 
'Monto esperado del claim según reglas de negocio: milestone 1=25, 5=35, 25=100. No se recalcula, se usa directamente de la vista base.';

COMMENT ON COLUMN ops.v_yango_cabinet_claims_for_collection.yango_due_date IS 
'Fecha de vencimiento para Yango (lead_date + 14 días).';

COMMENT ON COLUMN ops.v_yango_cabinet_claims_for_collection.days_overdue_yango IS 
'Número de días vencidos desde yango_due_date. 0 si el claim no está vencido.';

COMMENT ON COLUMN ops.v_yango_cabinet_claims_for_collection.overdue_bucket_yango IS 
'Bucket de aging simplificado para Yango: 0_not_due (no vencido), 1_1_7 (1-7 días), 2_8_14 (8-14 días), 3_15_30 (15-30 días), 4_30_plus (31+ días).';

COMMENT ON COLUMN ops.v_yango_cabinet_claims_for_collection.yango_payment_status IS 
'Estado canónico del pago para Yango: PAID (pagado correctamente), PAID_MISAPPLIED (pagó pero a otro milestone), UNPAID (no pagado).';

COMMENT ON COLUMN ops.v_yango_cabinet_claims_for_collection.payment_key IS 
'Payment key del pago asociado si existe, NULL si no hay pago.';

COMMENT ON COLUMN ops.v_yango_cabinet_claims_for_collection.pay_date IS 
'Fecha de pago si existe, NULL si no hay pago.';

COMMENT ON COLUMN ops.v_yango_cabinet_claims_for_collection.reason_code IS 
'Código de razón detallado: paid, missing_driver_id, missing_milestone, payment_found_other_milestone, payment_found_person_key_only, no_payment_found.';

COMMENT ON COLUMN ops.v_yango_cabinet_claims_for_collection.match_rule IS 
'Regla de matching del pago (source_upstream, name_unique, ambiguous, no_match) si existe, NULL si no hay pago.';

COMMENT ON COLUMN ops.v_yango_cabinet_claims_for_collection.match_confidence IS 
'Confianza del matching del pago (high, medium, low) si existe, NULL si no hay pago.';

-- ============================================================================
-- QUERY DE EXPORT EJEMPLO
-- ============================================================================
-- Para exportar claims UNPAID y PAID_MISAPPLIED a Yango:
-- SELECT *
-- FROM ops.v_yango_cabinet_claims_for_collection
-- WHERE yango_payment_status IN ('UNPAID','PAID_MISAPPLIED')
-- ORDER BY days_overdue_yango DESC;
-- ============================================================================

