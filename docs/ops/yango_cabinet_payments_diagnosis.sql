-- ============================================================================
-- DIAGNÓSTICO CANÓNICO: Pagos Yango Cabinet - PAID_MISAPPLIED
-- ============================================================================
-- PROPÓSITO:
-- Queries SQL que explican claramente:
-- a) Por qué existen PAID_MISAPPLIED
-- b) Qué payment_key está asociado a más de un milestone
-- c) En qué casos el mismo pago se "distribuye" o se pisa
--
-- FUENTES DE DATOS:
-- - ops.mv_yango_cabinet_claims_for_collection (claims con yango_payment_status)
-- - ops.v_yango_payments_ledger_latest_enriched (pagos reales)
-- - ops.v_claims_payment_status_cabinet (vista base con reason_code)
-- ============================================================================

-- ============================================================================
-- QUERY 1.1: Distribución de PAID_MISAPPLIED por razón, identidad y confianza
-- ============================================================================
-- Objetivo: Entender la distribución de casos PAID_MISAPPLIED según diferentes
-- dimensiones para identificar patrones.
-- ============================================================================

SELECT 
    '=== DISTRIBUCIÓN: PAID_MISAPPLIED por razón, identidad y confianza ===' AS seccion;

SELECT 
    reason_code,
    identity_status,
    match_confidence,
    COUNT(*) AS count_claims,
    SUM(expected_amount) AS total_expected_amount,
    ROUND(100.0 * COUNT(*) / NULLIF((SELECT COUNT(*) FROM ops.mv_yango_cabinet_claims_for_collection WHERE yango_payment_status = 'PAID_MISAPPLIED'), 0), 2) AS pct_rows,
    ROUND(100.0 * SUM(expected_amount) / NULLIF((SELECT SUM(expected_amount) FROM ops.mv_yango_cabinet_claims_for_collection WHERE yango_payment_status = 'PAID_MISAPPLIED'), 0), 2) AS pct_amount
FROM ops.mv_yango_cabinet_claims_for_collection
WHERE yango_payment_status = 'PAID_MISAPPLIED'
GROUP BY reason_code, identity_status, match_confidence
ORDER BY count_claims DESC, total_expected_amount DESC;

-- ============================================================================
-- QUERY 1.2: Payment_key asociado a múltiples milestones
-- ============================================================================
-- Objetivo: Identificar casos donde un mismo payment_key está asociado a
-- múltiples milestones (mismo driver, mismo payment_key, diferentes milestones).
-- Esto puede indicar que un pago se está usando para múltiples claims.
-- ============================================================================

SELECT 
    '=== PAYMENT_KEY asociado a múltiples milestones ===' AS seccion;

WITH payment_milestone_counts AS (
    SELECT 
        p.payment_key,
        p.driver_id_final,
        COUNT(DISTINCT p.milestone_value) AS distinct_milestones,
        COUNT(*) AS total_payment_records,
        STRING_AGG(DISTINCT p.milestone_value::text, ', ' ORDER BY p.milestone_value::text) AS milestone_values
    FROM ops.v_yango_payments_ledger_latest_enriched p
    WHERE p.is_paid = true
        AND p.driver_id_final IS NOT NULL
        AND p.payment_key IS NOT NULL
    GROUP BY p.payment_key, p.driver_id_final
    HAVING COUNT(DISTINCT p.milestone_value) > 1
)
SELECT 
    pmc.payment_key,
    pmc.driver_id_final,
    pmc.distinct_milestones,
    pmc.total_payment_records,
    pmc.milestone_values,
    -- Detalle de cada milestone para este payment_key
    (
        SELECT JSON_AGG(
            json_build_object(
                'milestone_value', p2.milestone_value,
                'pay_date', p2.pay_date,
                'is_paid', p2.is_paid,
                'identity_status', p2.identity_status,
                'match_rule', p2.match_rule
            )
        )
        FROM ops.v_yango_payments_ledger_latest_enriched p2
        WHERE p2.payment_key = pmc.payment_key
            AND p2.driver_id_final = pmc.driver_id_final
            AND p2.is_paid = true
    ) AS payment_details
FROM payment_milestone_counts pmc
ORDER BY pmc.distinct_milestones DESC, pmc.total_payment_records DESC
LIMIT 50;

-- ============================================================================
-- QUERY 1.3: Análisis de "distribución" o "pisado" de pagos
-- ============================================================================
-- Objetivo: Identificar casos donde el mismo payment_key se usa en diferentes
-- claims (diferentes driver_id o diferentes milestones). Esto puede indicar
-- que un pago se está "distribuyendo" entre múltiples claims o que hay
-- conflictos de matching.
-- ============================================================================

SELECT 
    '=== DISTRIBUCIÓN/PISADO: Mismo payment_key en diferentes claims ===' AS seccion;

WITH claims_with_payments AS (
    SELECT 
        c.driver_id,
        c.milestone_value AS claim_milestone,
        c.expected_amount,
        c.payment_key,
        c.yango_payment_status,
        c.reason_code,
        -- Información del pago real
        p.milestone_value AS payment_milestone,
        p.pay_date,
        p.driver_id_final AS payment_driver_id,
        p.is_paid,
        p.identity_status,
        p.match_rule
    FROM ops.mv_yango_cabinet_claims_for_collection c
    LEFT JOIN ops.v_yango_payments_ledger_latest_enriched p
        ON p.payment_key = c.payment_key
    WHERE c.payment_key IS NOT NULL
),
payment_key_conflicts AS (
    SELECT 
        payment_key,
        COUNT(DISTINCT driver_id) AS distinct_drivers,
        COUNT(DISTINCT claim_milestone) AS distinct_claim_milestones,
        COUNT(DISTINCT payment_milestone) AS distinct_payment_milestones,
        COUNT(*) AS total_claims,
        STRING_AGG(DISTINCT driver_id::text, ', ' ORDER BY driver_id::text) AS driver_ids,
        STRING_AGG(DISTINCT claim_milestone::text, ', ' ORDER BY claim_milestone::text) AS claim_milestones,
        STRING_AGG(DISTINCT payment_milestone::text, ', ' ORDER BY payment_milestone::text) AS payment_milestones
    FROM claims_with_payments
    WHERE payment_key IS NOT NULL
    GROUP BY payment_key
    HAVING COUNT(DISTINCT driver_id) > 1 
        OR COUNT(DISTINCT claim_milestone) > 1
        OR COUNT(DISTINCT payment_milestone) > 1
)
SELECT 
    pkc.payment_key,
    pkc.distinct_drivers,
    pkc.distinct_claim_milestones,
    pkc.distinct_payment_milestones,
    pkc.total_claims,
    pkc.driver_ids,
    pkc.claim_milestones,
    pkc.payment_milestones,
    -- Detalle de cada claim asociado a este payment_key
    (
        SELECT JSON_AGG(
            json_build_object(
                'driver_id', cwp.driver_id,
                'claim_milestone', cwp.claim_milestone,
                'expected_amount', cwp.expected_amount,
                'yango_payment_status', cwp.yango_payment_status,
                'reason_code', cwp.reason_code,
                'payment_milestone', cwp.payment_milestone,
                'pay_date', cwp.pay_date,
                'payment_driver_id', cwp.payment_driver_id,
                'match_rule', cwp.match_rule
            )
        )
        FROM claims_with_payments cwp
        WHERE cwp.payment_key = pkc.payment_key
    ) AS claims_details
FROM payment_key_conflicts pkc
ORDER BY pkc.total_claims DESC, pkc.distinct_drivers DESC
LIMIT 50;

-- ============================================================================
-- QUERY 1.4: Ejemplos concretos de PAID_MISAPPLIED con evidencia completa
-- ============================================================================
-- Objetivo: Mostrar ejemplos concretos de claims PAID_MISAPPLIED con toda
-- la evidencia: claim original (milestone esperado) + pago encontrado en
-- otro milestone (con milestone_value real).
-- ============================================================================

SELECT 
    '=== EJEMPLOS: PAID_MISAPPLIED con evidencia completa ===' AS seccion;

SELECT 
    -- Información del claim original
    c.driver_id AS claim_driver_id,
    c.person_key AS claim_person_key,
    c.milestone_value AS claim_milestone_expected,
    c.expected_amount AS claim_expected_amount,
    c.lead_date AS claim_lead_date,
    c.yango_due_date AS claim_due_date,
    c.days_overdue_yango AS claim_days_overdue,
    c.yango_payment_status,
    c.reason_code,
    c.identity_status AS claim_identity_status,
    c.match_rule AS claim_match_rule,
    c.match_confidence AS claim_match_confidence,
    c.is_reconcilable_enriched,
    
    -- Información del pago encontrado (en otro milestone)
    c.payment_key AS found_payment_key,
    c.pay_date AS found_pay_date,
    c.suggested_driver_id AS found_suggested_driver_id,
    
    -- Pago real desde el ledger (si existe)
    p.milestone_value AS payment_milestone_actual,
    p.pay_date AS payment_pay_date,
    p.driver_id_final AS payment_driver_id_final,
    p.person_key_final AS payment_person_key_final,
    p.is_paid AS payment_is_paid,
    p.identity_status AS payment_identity_status,
    p.match_rule AS payment_match_rule,
    p.match_confidence AS payment_match_confidence,
    p.raw_driver_name AS payment_raw_driver_name,
    
    -- Análisis de discrepancia
    CASE 
        WHEN c.milestone_value != p.milestone_value THEN 'MILESTONE_MISMATCH'
        WHEN c.driver_id != p.driver_id_final THEN 'DRIVER_MISMATCH'
        WHEN c.payment_key IS NULL THEN 'NO_PAYMENT_FOUND'
        ELSE 'OK'
    END AS discrepancy_type,
    
    -- Evidencia de identidad
    CASE 
        WHEN c.driver_id = p.driver_id_final THEN 'DRIVER_ID_MATCH'
        WHEN c.person_key = p.person_key_final THEN 'PERSON_KEY_MATCH'
        ELSE 'NO_IDENTITY_MATCH'
    END AS identity_match_type
    
FROM ops.mv_yango_cabinet_claims_for_collection c
LEFT JOIN ops.v_yango_payments_ledger_latest_enriched p
    ON p.payment_key = c.payment_key
    AND p.driver_id_final = c.driver_id
WHERE c.yango_payment_status = 'PAID_MISAPPLIED'
    AND c.reason_code = 'payment_found_other_milestone'
ORDER BY c.days_overdue_yango DESC, c.expected_amount DESC
LIMIT 20;

-- ============================================================================
-- QUERY 1.5: Resumen ejecutivo de PAID_MISAPPLIED
-- ============================================================================
-- Objetivo: Resumen agregado de todos los casos PAID_MISAPPLIED para
-- entender el alcance del problema.
-- ============================================================================

SELECT 
    '=== RESUMEN EJECUTIVO: PAID_MISAPPLIED ===' AS seccion;

SELECT 
    COUNT(*) AS total_paid_misapplied_claims,
    SUM(expected_amount) AS total_expected_amount_misapplied,
    COUNT(DISTINCT driver_id) AS distinct_drivers_affected,
    COUNT(DISTINCT milestone_value) AS distinct_milestones_affected,
    
    -- Distribución por milestone
    COUNT(*) FILTER (WHERE milestone_value = 1) AS count_milestone_1,
    SUM(expected_amount) FILTER (WHERE milestone_value = 1) AS amount_milestone_1,
    COUNT(*) FILTER (WHERE milestone_value = 5) AS count_milestone_5,
    SUM(expected_amount) FILTER (WHERE milestone_value = 5) AS amount_milestone_5,
    COUNT(*) FILTER (WHERE milestone_value = 25) AS count_milestone_25,
    SUM(expected_amount) FILTER (WHERE milestone_value = 25) AS amount_milestone_25,
    
    -- Distribución por reconciliabilidad
    COUNT(*) FILTER (WHERE is_reconcilable_enriched = true) AS count_reconcilable,
    SUM(expected_amount) FILTER (WHERE is_reconcilable_enriched = true) AS amount_reconcilable,
    COUNT(*) FILTER (WHERE is_reconcilable_enriched = false) AS count_not_reconcilable,
    SUM(expected_amount) FILTER (WHERE is_reconcilable_enriched = false) AS amount_not_reconcilable,
    
    -- Distribución por identidad
    COUNT(*) FILTER (WHERE identity_status = 'confirmed') AS count_confirmed,
    COUNT(*) FILTER (WHERE identity_status = 'enriched') AS count_enriched,
    COUNT(*) FILTER (WHERE identity_status = 'ambiguous') AS count_ambiguous,
    COUNT(*) FILTER (WHERE identity_status = 'no_match') AS count_no_match,
    
    -- Distribución por confianza de matching
    COUNT(*) FILTER (WHERE match_confidence = 'high') AS count_high_confidence,
    COUNT(*) FILTER (WHERE match_confidence = 'medium') AS count_medium_confidence,
    COUNT(*) FILTER (WHERE match_confidence = 'low') AS count_low_confidence
    
FROM ops.mv_yango_cabinet_claims_for_collection
WHERE yango_payment_status = 'PAID_MISAPPLIED';

-- ============================================================================
-- QUERY 1.6: Casos donde el mismo pago se "pisa" (mismo payment_key, mismo driver, diferentes claims)
-- ============================================================================
-- Objetivo: Identificar casos donde el mismo payment_key se asocia a múltiples
-- claims del mismo driver pero diferentes milestones. Esto puede indicar
-- que un pago se está usando incorrectamente para múltiples claims.
-- ============================================================================

SELECT 
    '=== PISADO: Mismo payment_key para mismo driver en diferentes milestones ===' AS seccion;

WITH driver_payment_claims AS (
    SELECT 
        c.driver_id,
        c.payment_key,
        COUNT(DISTINCT c.milestone_value) AS distinct_claim_milestones,
        COUNT(*) AS total_claims,
        STRING_AGG(DISTINCT c.milestone_value::text, ', ' ORDER BY c.milestone_value::text) AS claim_milestones,
        SUM(c.expected_amount) AS total_expected_amount,
        -- Información del pago real
        MAX(p.milestone_value) AS payment_milestone_actual,
        MAX(p.pay_date) AS payment_pay_date
    FROM ops.mv_yango_cabinet_claims_for_collection c
    LEFT JOIN ops.v_yango_payments_ledger_latest_enriched p
        ON p.payment_key = c.payment_key
        AND p.driver_id_final = c.driver_id
    WHERE c.payment_key IS NOT NULL
        AND c.driver_id IS NOT NULL
        AND c.yango_payment_status IN ('PAID', 'PAID_MISAPPLIED')
    GROUP BY c.driver_id, c.payment_key
    HAVING COUNT(DISTINCT c.milestone_value) > 1
)
SELECT 
    dpc.driver_id,
    dpc.payment_key,
    dpc.distinct_claim_milestones,
    dpc.total_claims,
    dpc.claim_milestones,
    dpc.total_expected_amount,
    dpc.payment_milestone_actual,
    dpc.payment_pay_date,
    -- Detalle de cada claim asociado
    (
        SELECT JSON_AGG(
            json_build_object(
                'milestone_value', c.milestone_value,
                'expected_amount', c.expected_amount,
                'yango_payment_status', c.yango_payment_status,
                'reason_code', c.reason_code,
                'lead_date', c.lead_date,
                'days_overdue_yango', c.days_overdue_yango
            )
        )
        FROM ops.mv_yango_cabinet_claims_for_collection c
        WHERE c.driver_id = dpc.driver_id
            AND c.payment_key = dpc.payment_key
    ) AS claims_details
FROM driver_payment_claims dpc
ORDER BY dpc.total_claims DESC, dpc.total_expected_amount DESC
LIMIT 30;

-- ============================================================================
-- FIN DEL DIAGNÓSTICO
-- ============================================================================
-- NOTAS:
-- - Todas las queries usan vistas existentes, sin recalcular lógica
-- - Los resultados deben validarse contra ops.v_yango_cabinet_claims_exec_summary
-- - Los casos de PAID_MISAPPLIED requieren revisión manual para determinar
--   si el pago debe reasignarse o si el claim debe marcarse como pagado
-- ============================================================================



