-- ============================================================================
-- Fix Completo y Final: is_reconcilable_enriched
-- ============================================================================
-- Este script aplica TODOS los fixes necesarios en el orden correcto:
-- 1. Fix de campos de identidad en v_claims_payment_status_cabinet
-- 2. Fix de is_reconcilable_enriched en v_yango_cabinet_claims_for_collection
-- 3. Recrear vistas materializadas
-- ============================================================================

-- PASO 1: Aplicar fix de campos de identidad en v_claims_payment_status_cabinet
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
    -- FIX: Obtener campos de identidad del pago correcto
    COALESCE(p_exact.identity_status, p_other_milestone.identity_status, p_person_key.identity_status) AS payment_identity_status,
    COALESCE(p_exact.match_rule, p_other_milestone.match_rule, p_person_key.match_rule) AS payment_match_rule,
    COALESCE(p_exact.match_confidence, p_other_milestone.match_confidence, p_person_key.match_confidence) AS payment_match_confidence,
    
    -- payment_status: ENUM TEXT (mantener compatibilidad)
    CASE 
        WHEN p_exact.payment_key IS NOT NULL THEN 'paid'
        ELSE 'not_paid'
    END AS payment_status,
    
    -- payment_reason: TEXT (mantener compatibilidad)
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

-- PASO 2: Aplicar fix de is_reconcilable_enriched en v_yango_cabinet_claims_for_collection
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
    c.payment_match_confidence AS match_confidence,
    
    -- Campos de identidad enriquecida (Opción B: diagnóstico de misapplied)
    c.payment_identity_status AS identity_status,
    
    -- suggested_driver_id: driver_id sugerido desde ledger enriched cuando hay misapplied
    COALESCE(
        p_other_milestone.driver_id_final,
        p_person_key.driver_id_final
    ) AS suggested_driver_id,
    
    -- is_reconcilable_enriched: flag para identificar claims reconciliables
    -- LÓGICA ROBUSTA:
    -- 1. identity_status debe ser 'confirmed' o 'enriched'
    -- 2. match_confidence puede ser string ('high'/'medium'/'low') o numérico
    -- 3. Si es 'high' -> siempre reconciliable
    -- 4. Si es 'medium' -> reconciliable si match_rule es 'name_unique' o 'source_upstream'
    -- 5. Si es numérico -> reconciliable si >= 0.85
    CASE
        -- Requisito base: identity_status debe ser confirmed o enriched
        WHEN c.payment_identity_status NOT IN ('confirmed', 'enriched') THEN false
        
        -- match_confidence = 'high' -> siempre reconciliable
        WHEN c.payment_match_confidence = 'high' THEN true
        
        -- match_confidence = 'medium' -> reconciliable solo si match_rule es único
        WHEN c.payment_match_confidence = 'medium' 
            AND c.payment_match_rule IN ('name_unique', 'source_upstream') 
        THEN true
        
        -- match_confidence numérico -> reconciliable si >= 0.85
        WHEN c.payment_match_confidence::text ~ '^[0-9]+\.?[0-9]*$' 
            AND (c.payment_match_confidence::numeric >= 0.85)
        THEN true
        
        -- Cualquier otro caso -> no reconciliable
        ELSE false
    END AS is_reconcilable_enriched

FROM ops.mv_claims_payment_status_cabinet c
LEFT JOIN public.drivers d ON d.driver_id = c.driver_id
-- Optimización: usar LEFT JOIN LATERAL solo cuando reason_code lo requiera
LEFT JOIN LATERAL (
    -- Para reason_code = 'payment_found_other_milestone': buscar driver_id del pago encontrado
    SELECT driver_id_final
    FROM ops.mv_yango_payments_ledger_latest_enriched p
    WHERE p.driver_id_final = c.driver_id
        AND p.milestone_value != c.milestone_value
        AND p.is_paid = true
    ORDER BY p.pay_date DESC
    LIMIT 1
) p_other_milestone ON c.reason_code = 'payment_found_other_milestone'
LEFT JOIN LATERAL (
    -- Para reason_code = 'payment_found_person_key_only': buscar driver_id_final del pago por person_key
    SELECT driver_id_final
    FROM ops.mv_yango_payments_ledger_latest_enriched p
    WHERE p.person_key_final = c.person_key
        AND p.milestone_value = c.milestone_value
        AND p.is_paid = true
        AND p.driver_id_final IS NOT NULL
    ORDER BY p.pay_date DESC
    LIMIT 1
) p_person_key ON c.reason_code = 'payment_found_person_key_only' 
    AND c.person_key IS NOT NULL;

-- PASO 3: Recrear vista materializada con todos los fixes aplicados
DROP MATERIALIZED VIEW IF EXISTS ops.mv_claims_payment_status_cabinet CASCADE;

CREATE MATERIALIZED VIEW ops.mv_claims_payment_status_cabinet AS
SELECT 
    driver_id,
    person_key,
    milestone_value,
    lead_date,
    due_date,
    expected_amount,
    days_overdue,
    bucket_overdue,
    paid_flag,
    paid_date,
    payment_key,
    payment_identity_status,
    payment_match_rule,
    payment_match_confidence,
    payment_status,
    payment_reason,
    reason_code,
    action_priority
FROM ops.v_claims_payment_status_cabinet;

-- Recrear índices
CREATE UNIQUE INDEX IF NOT EXISTS idx_mv_claims_driver_milestone 
    ON ops.mv_claims_payment_status_cabinet(driver_id, milestone_value) 
    WHERE driver_id IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_mv_claims_reason_code 
    ON ops.mv_claims_payment_status_cabinet(reason_code);
CREATE INDEX IF NOT EXISTS idx_mv_claims_paid_flag 
    ON ops.mv_claims_payment_status_cabinet(paid_flag);
CREATE INDEX IF NOT EXISTS idx_mv_claims_lead_date 
    ON ops.mv_claims_payment_status_cabinet(lead_date DESC);
CREATE INDEX IF NOT EXISTS idx_mv_claims_payment_key 
    ON ops.mv_claims_payment_status_cabinet(payment_key) 
    WHERE payment_key IS NOT NULL;

-- PASO 4: Recrear vista materializada mv_yango_cabinet_claims_for_collection
DROP MATERIALIZED VIEW IF EXISTS ops.mv_yango_cabinet_claims_for_collection CASCADE;

CREATE MATERIALIZED VIEW ops.mv_yango_cabinet_claims_for_collection AS
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
    c.payment_match_confidence AS match_confidence,
    
    -- Campos de identidad enriquecida (Opción B: diagnóstico de misapplied)
    c.payment_identity_status AS identity_status,
    
    -- suggested_driver_id: driver_id sugerido desde ledger enriched cuando hay misapplied
    COALESCE(
        p_other_milestone.driver_id_final,
        p_person_key.driver_id_final
    ) AS suggested_driver_id,
    
    -- is_reconcilable_enriched: flag para identificar claims reconciliables
    -- LÓGICA ROBUSTA:
    -- 1. identity_status debe ser 'confirmed' o 'enriched'
    -- 2. match_confidence puede ser string ('high'/'medium'/'low') o numérico
    -- 3. Si es 'high' -> siempre reconciliable
    -- 4. Si es 'medium' -> reconciliable si match_rule es 'name_unique' o 'source_upstream'
    -- 5. Si es numérico -> reconciliable si >= 0.85
    CASE
        -- Requisito base: identity_status debe ser confirmed o enriched
        WHEN c.payment_identity_status NOT IN ('confirmed', 'enriched') THEN false
        
        -- match_confidence = 'high' -> siempre reconciliable
        WHEN c.payment_match_confidence = 'high' THEN true
        
        -- match_confidence = 'medium' -> reconciliable solo si match_rule es único
        WHEN c.payment_match_confidence = 'medium' 
            AND c.payment_match_rule IN ('name_unique', 'source_upstream') 
        THEN true
        
        -- match_confidence numérico -> reconciliable si >= 0.85
        WHEN c.payment_match_confidence::text ~ '^[0-9]+\.?[0-9]*$' 
            AND (c.payment_match_confidence::numeric >= 0.85)
        THEN true
        
        -- Cualquier otro caso -> no reconciliable
        ELSE false
    END AS is_reconcilable_enriched

FROM ops.mv_claims_payment_status_cabinet c
LEFT JOIN public.drivers d ON d.driver_id = c.driver_id
-- Usar vistas materializadas en los JOINs LATERAL
LEFT JOIN LATERAL (
    SELECT driver_id_final
    FROM ops.mv_yango_payments_ledger_latest_enriched p
    WHERE p.driver_id_final = c.driver_id
        AND p.milestone_value != c.milestone_value
        AND p.is_paid = true
    ORDER BY p.pay_date DESC
    LIMIT 1
) p_other_milestone ON c.reason_code = 'payment_found_other_milestone'
LEFT JOIN LATERAL (
    SELECT driver_id_final
    FROM ops.mv_yango_payments_ledger_latest_enriched p
    WHERE p.person_key_final = c.person_key
        AND p.milestone_value = c.milestone_value
        AND p.is_paid = true
        AND p.driver_id_final IS NOT NULL
    ORDER BY p.pay_date DESC
    LIMIT 1
) p_person_key ON c.reason_code = 'payment_found_person_key_only' 
    AND c.person_key IS NOT NULL;

-- Recrear índices
CREATE INDEX IF NOT EXISTS idx_mv_yango_cabinet_claims_misapplied_reconcilable 
    ON ops.mv_yango_cabinet_claims_for_collection(yango_payment_status, is_reconcilable_enriched) 
    WHERE yango_payment_status = 'PAID_MISAPPLIED';

CREATE INDEX IF NOT EXISTS idx_mv_yango_cabinet_claims_payment_status 
    ON ops.mv_yango_cabinet_claims_for_collection(yango_payment_status);
    
CREATE INDEX IF NOT EXISTS idx_mv_yango_cabinet_claims_reconcilable 
    ON ops.mv_yango_cabinet_claims_for_collection(is_reconcilable_enriched) 
    WHERE is_reconcilable_enriched = true;

CREATE INDEX IF NOT EXISTS idx_mv_yango_cabinet_claims_driver_milestone 
    ON ops.mv_yango_cabinet_claims_for_collection(driver_id, milestone_value) 
    WHERE driver_id IS NOT NULL;

CREATE INDEX IF NOT EXISTS idx_mv_yango_cabinet_claims_expected_amount 
    ON ops.mv_yango_cabinet_claims_for_collection(expected_amount DESC);

-- PASO 5: Ejecutar ANALYZE para actualizar estadísticas
ANALYZE ops.mv_claims_payment_status_cabinet;
ANALYZE ops.mv_yango_cabinet_claims_for_collection;





