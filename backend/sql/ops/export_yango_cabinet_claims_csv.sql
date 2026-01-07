-- ============================================================================
-- Queries para Exportar a CSV - Reclamo Formal a Yango
-- ============================================================================
-- Ejecutar estos queries y exportar resultados a CSV para el reclamo formal
-- ============================================================================

-- ============================================================================
-- 1. Export EXIGIMOS (Claims No Pagados)
-- ============================================================================
-- Ordenado por monto descendente
SELECT 
    claim_key,
    person_key,
    driver_id,
    driver_name,
    milestone_value,
    lead_date,
    expected_amount,
    yango_due_date,
    days_overdue_yango,
    overdue_bucket_yango,
    yango_payment_status,
    reason_code,
    identity_status,
    match_rule,
    match_confidence,
    is_reconcilable_enriched,
    payment_key,
    pay_date,
    suggested_driver_id
FROM ops.v_yango_cabinet_claims_exigimos
ORDER BY expected_amount DESC, days_overdue_yango DESC;

-- ============================================================================
-- 2. Export REPORTAMOS (Pagos Recibidos Sin Mapeo)
-- ============================================================================
-- Ordenado por monto descendente
SELECT 
    payment_key,
    pay_date,
    milestone_value,
    paid_amount,
    driver_id_final,
    person_key_final,
    driver_name_norm,
    identity_status,
    match_rule,
    match_confidence,
    claim_driver_id,
    claim_person_key,
    cabinet_driver_id,
    cabinet_person_key,
    no_mapping_reason
FROM ops.v_yango_cabinet_payments_reportamos
ORDER BY paid_amount DESC, pay_date DESC;

-- ============================================================================
-- 3. Export RESUMEN EJECUTIVO
-- ============================================================================
-- Ordenado por sección y monto descendente
SELECT 
    section,
    category,
    count_claims,
    amount
FROM ops.v_yango_cabinet_claims_exec_summary
ORDER BY section, amount DESC;












