-- ============================================================================
-- Script: Actualizar Vistas Dependientes para Usar Vistas Materializadas
-- ============================================================================
-- OBJETIVO:
-- Actualizar las vistas que dependen de las vistas costosas para que usen
-- las vistas materializadas, manteniendo compatibilidad con el código existente.
-- ============================================================================
-- ESTRATEGIA:
-- Reemplazar referencias a vistas originales por vistas materializadas en:
-- 1. v_claims_payment_status_cabinet: usar mv_claims_payment_status_cabinet
--    (pero esto es circular, así que actualizamos las vistas que la usan)
-- 2. v_yango_payments_ledger_latest_enriched: usar mv_yango_payments_ledger_latest_enriched
-- 3. v_yango_cabinet_claims_for_collection: usar mv_claims_payment_status_cabinet
-- ============================================================================

-- ============================================================================
-- PASO 1: Actualizar v_claims_payment_status_cabinet para usar materializadas
-- ============================================================================
-- NOTA: v_claims_payment_status_cabinet hace JOINs LATERAL a 
-- v_yango_payments_ledger_latest_enriched, así que necesitamos actualizar
-- esa referencia también.

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
    -- Deduplicación: 1 fila por (driver_id + milestone_value), quedarse con lead_date más reciente
    SELECT DISTINCT ON (driver_id, milestone_value)
        driver_id,
        person_key,
        lead_date,
        milestone_value,
        expected_amount_raw,
        -- Aplicar reglas de negocio para expected_amount (milestone 1=25, 5=35, 25=100)
        -- CAST explícito a numeric(12,2) para mantener compatibilidad con vista existente
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
    p_exact.pay_date AS paid_date,
    p_exact.payment_key,
    p_exact.identity_status AS payment_identity_status,
    p_exact.match_rule AS payment_match_rule,
    p_exact.match_confidence AS payment_match_confidence,
    
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
    -- Optimizado: usar LEFT JOIN LATERAL en lugar de subconsultas EXISTS costosas
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
    -- USAR VISTA MATERIALIZADA
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
-- Optimización: solo ejecutar estos JOINs cuando no hay pago exacto
LEFT JOIN LATERAL (
    -- ¿Existe pago para este driver pero otro milestone?
    -- USAR VISTA MATERIALIZADA
    SELECT payment_key
    FROM ops.mv_yango_payments_ledger_latest_enriched p
    WHERE p.driver_id_final = c.driver_id
        AND p.milestone_value != c.milestone_value
        AND p.is_paid = true
    LIMIT 1
) p_other_milestone ON p_exact.payment_key IS NULL 
    AND c.driver_id IS NOT NULL
    AND c.milestone_value IS NOT NULL
LEFT JOIN LATERAL (
    -- ¿Existe pago para este milestone pero solo por person_key?
    -- USAR VISTA MATERIALIZADA
    SELECT payment_key
    FROM ops.mv_yango_payments_ledger_latest_enriched p
    WHERE p.milestone_value = c.milestone_value
        AND p.is_paid = true
        AND p.person_key_final = c.person_key
        AND (p.driver_id_final IS NULL OR p.driver_id_final != c.driver_id)
    LIMIT 1
) p_person_key ON p_exact.payment_key IS NULL 
    AND p_other_milestone.payment_key IS NULL
    AND c.person_key IS NOT NULL
    AND c.driver_id IS NOT NULL
    AND c.milestone_value IS NOT NULL;

-- ============================================================================
-- PASO 2: Actualizar v_yango_payments_ledger_latest_enriched para usar materializadas
-- ============================================================================

CREATE OR REPLACE VIEW ops.v_yango_payments_ledger_latest_enriched AS
WITH ledger_latest AS (
    SELECT 
        id,
        latest_snapshot_at,
        source_table,
        source_pk,
        pay_date,
        pay_time,
        raw_driver_name,
        driver_name_normalized,
        milestone_type,
        milestone_value,
        is_paid,
        paid_flag_source,
        driver_id AS ledger_driver_id,
        person_key AS ledger_person_key,
        match_rule AS ledger_match_rule,
        match_confidence AS ledger_match_confidence,
        payment_key,
        state_hash,
        created_at
    FROM ops.mv_yango_payments_ledger_latest
),
-- Join con raw_current para obtener la identidad más reciente calculada
-- USAR VISTA MATERIALIZADA
enriched AS (
    SELECT 
        ll.*,
        -- Identidad desde raw_current (matching por nombre)
        rc.driver_id AS raw_driver_id,
        rc.person_key AS raw_person_key,
        rc.match_rule AS raw_match_rule,
        rc.match_confidence AS raw_match_confidence
    FROM ledger_latest ll
    LEFT JOIN ops.mv_yango_payments_raw_current rc
        ON rc.payment_key = ll.payment_key
)
SELECT 
    e.id,
    e.latest_snapshot_at,
    e.source_table,
    e.source_pk,
    e.pay_date,
    e.pay_time,
    e.raw_driver_name,
    e.driver_name_normalized,
    e.milestone_type,
    e.milestone_value,
    e.is_paid,
    e.paid_flag_source,
    
    -- driver_id_original: lo que vino del ledger (casi siempre NULL por bug de ingest)
    e.ledger_driver_id AS driver_id_original,
    e.ledger_person_key AS person_key_original,
    
    -- driver_id_enriched: obtenido de raw_current por matching
    CASE 
        WHEN e.ledger_driver_id IS NULL AND e.raw_driver_id IS NOT NULL 
        THEN e.raw_driver_id
        ELSE NULL
    END AS driver_id_enriched,
    
    -- driver_id_final: COALESCE(ledger, raw_current)
    COALESCE(e.ledger_driver_id, e.raw_driver_id) AS driver_id_final,
    
    -- person_key_final
    COALESCE(e.ledger_person_key, e.raw_person_key) AS person_key_final,
    
    -- identity_status basado en fuente y match_rule
    CASE 
        -- Si el ledger ya tenía driver_id → confirmed (upstream)
        WHEN e.ledger_driver_id IS NOT NULL THEN 'confirmed'
        -- Si lo obtuvimos de raw_current con match único → enriched
        WHEN e.raw_driver_id IS NOT NULL AND e.raw_match_rule = 'driver_name_unique' THEN 'enriched'
        -- Si hay nombre pero no hay match o es ambiguo
        WHEN e.raw_driver_name IS NOT NULL AND e.raw_match_rule = 'none' THEN 'ambiguous'
        -- Si no hay nombre en absoluto
        ELSE 'no_match'
    END AS identity_status,
    
    -- match_rule: fuente del matching
    CASE 
        WHEN e.ledger_driver_id IS NOT NULL THEN 'source_upstream'
        WHEN e.raw_driver_id IS NOT NULL AND e.raw_match_rule = 'driver_name_unique' THEN 'name_unique'
        WHEN e.raw_match_rule = 'none' THEN 'ambiguous'
        ELSE 'no_match'
    END AS match_rule,
    
    -- match_confidence
    CASE 
        WHEN e.ledger_driver_id IS NOT NULL THEN 'high'
        WHEN e.raw_driver_id IS NOT NULL THEN 'medium'
        ELSE 'low'
    END AS match_confidence,
    
    -- Flag de enriquecimiento
    (e.ledger_driver_id IS NULL AND e.raw_driver_id IS NOT NULL) AS identity_enriched,
    
    -- Campos de auditoría
    e.payment_key,
    e.state_hash,
    e.created_at
FROM enriched e
ORDER BY e.latest_snapshot_at DESC, e.payment_key;

-- ============================================================================
-- PASO 3: Actualizar v_yango_cabinet_claims_for_collection para usar materializada
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
    c.payment_match_confidence AS match_confidence,
    
    -- Campos de identidad enriquecida (Opción B: diagnóstico de misapplied)
    c.payment_identity_status AS identity_status,
    
    -- suggested_driver_id: driver_id sugerido desde ledger enriched cuando hay misapplied
    -- Optimizado con LEFT JOIN LATERAL para evitar subconsultas correlacionadas costosas
    -- USAR VISTA MATERIALIZADA
    COALESCE(
        p_other_milestone.driver_id_final,
        p_person_key.driver_id_final
    ) AS suggested_driver_id,
    
    -- is_reconcilable_enriched: flag para identificar claims reconciliables
    -- Regla: identity_status IN ('confirmed','enriched') AND match_confidence >= 0.85
    -- Interpretación: 'high' >= 0.85, 'medium' con 'name_unique' >= 0.85
    CASE
        WHEN c.payment_identity_status IN ('confirmed', 'enriched') 
            AND (
                (c.payment_match_confidence = 'high') OR
                (c.payment_match_confidence = 'medium' AND c.payment_match_rule = 'name_unique')
            )
        THEN true
        ELSE false
    END AS is_reconcilable_enriched

FROM ops.mv_claims_payment_status_cabinet c
LEFT JOIN public.drivers d ON d.driver_id = c.driver_id
-- Optimización: usar LEFT JOIN LATERAL solo cuando reason_code lo requiera
-- Esto evita ejecutar subconsultas costosas para todas las filas
-- USAR VISTA MATERIALIZADA
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

-- ============================================================================
-- PASO 4: Actualizar v_yango_cabinet_claims_for_collection para usar materializada
-- ============================================================================
-- NOTA: Si existe mv_yango_cabinet_claims_for_collection, la vista puede
-- simplemente apuntar a ella. Pero para mantener compatibilidad, mantenemos
-- la vista que calcula desde mv_claims_payment_status_cabinet.
-- Si se crea mv_yango_cabinet_claims_for_collection, se puede usar directamente.
-- ============================================================================

-- La vista v_yango_cabinet_claims_for_collection ya está actualizada en PASO 3
-- para usar mv_claims_payment_status_cabinet. Si existe mv_yango_cabinet_claims_for_collection,
-- podemos crear una vista wrapper que apunte directamente a ella:

-- Opción: Si mv_yango_cabinet_claims_for_collection existe, usar directamente
-- (Comentado porque requiere que la materializada exista primero)
-- CREATE OR REPLACE VIEW ops.v_yango_cabinet_claims_for_collection AS
-- SELECT * FROM ops.mv_yango_cabinet_claims_for_collection;

-- ============================================================================
-- RESUMEN
-- ============================================================================
-- Vistas actualizadas para usar materializadas:
-- 1. ops.v_claims_payment_status_cabinet
--    - Usa: mv_yango_receivable_payable_detail
--    - Usa: mv_yango_payments_ledger_latest_enriched (en JOINs LATERAL)
-- 2. ops.v_yango_payments_ledger_latest_enriched
--    - Usa: mv_yango_payments_ledger_latest
--    - Usa: mv_yango_payments_raw_current
-- 3. ops.v_yango_cabinet_claims_for_collection
--    - Usa: mv_claims_payment_status_cabinet
--    - Usa: mv_yango_payments_ledger_latest_enriched (en JOINs LATERAL)
--    - Opcional: Puede apuntar directamente a mv_yango_cabinet_claims_for_collection
--
-- NOTA: Las vistas originales ahora apuntan a materializadas, pero mantienen
-- la misma estructura y columnas, por lo que el código existente sigue funcionando.
-- ============================================================================

