-- ============================================================================
-- Vista: ops.v_claims_payment_status_cabinet
-- ============================================================================
-- PROPÓSITO DE NEGOCIO (5 líneas):
-- Vista orientada a cobranza que responde: "Para cada conductor que entró por 
-- cabinet y alcanzó un milestone, ¿nos pagaron o no, cuándo vence, qué tan vencido 
-- está, y por qué no pagaron si no pagaron?". Proporciona aging (vencimiento), 
-- reason_code (diagnóstico de no pago) y action_priority (prioridad operativa) 
-- para soportar gestión de cobranza eficiente.
-- ============================================================================
-- REGLAS DE NEGOCIO:
-- 1. Universo: Solo drivers que entraron por cabinet. Solo milestones 1, 5, 25.
-- 2. Un claim = (driver_id + milestone_value). GARANTIZADO: 1 fila por claim (deduplicación).
-- 3. Un claim se considera PAGADO si existe AL MENOS UN pago en 
--    ops.v_yango_payments_ledger_latest_enriched con:
--    - is_paid = true
--    - driver_id_final = driver_id
--    - milestone_value = milestone_value
--    - SIN filtrar por identity_status
--    - SIN filtrar por ventana de fecha del pago
-- 4. Si no existe pago → NO PAGADO.
-- 5. NO calcular montos en frontend. Todo sale de SQL.
-- 6. expected_amount se calcula según reglas: milestone 1=25, 5=35, 25=100.
-- ============================================================================
-- CORRECCIÓN DE DEPENDENCIAS (2026-01-XX):
-- CAMBIO: Eliminada dependencia de ops.v_yango_receivable_payable_detail (vista UI/report).
-- NUEVA FUENTE: ops.v_payment_calculation (vista canónica C2).
-- RAZÓN: Driver Matrix debe depender solo de vistas canónicas, no de vistas UI/report.
-- MANTIENE: Deduplicación con DISTINCT ON (driver_id, milestone_value) y reglas de expected_amount.
-- ============================================================================
-- VALIDACIÓN DE ACHIEVED (2026-01-XX):
-- CORRECCIÓN: Esta vista ahora usa ops.v_cabinet_milestones_achieved_from_payment_calc
-- (source-of-truth basado en v_payment_calculation) para validar achieved de claims.
-- Esto asegura que M1, M5 y M25 se generen correctamente cuando están achieved dentro
-- de la ventana de 14 días.
-- ============================================================================

CREATE OR REPLACE VIEW ops.v_claims_payment_status_cabinet AS
WITH milestone_amounts AS (
    -- Catálogo centralizado de montos por milestone (única fuente de verdad)
    SELECT 1 AS milestone_value, 25::numeric(12,2) AS expected_amount
    UNION ALL SELECT 5, 35::numeric(12,2)
    UNION ALL SELECT 25, 100::numeric(12,2)
),
payment_calc_agg AS (
    -- Agregado canónico de v_payment_calculation por (driver_id, milestone_trips)
    -- Evita duplicados cuando hay múltiples reglas activas para el mismo milestone
    SELECT DISTINCT ON (driver_id, milestone_trips)
        driver_id,
        person_key,
        lead_date,
        milestone_trips,
        milestone_achieved,
        achieved_date
    FROM ops.v_payment_calculation
    WHERE origin_tag = 'cabinet'
        AND rule_scope = 'partner'  -- Solo Yango (partner), no scouts
        AND milestone_trips IN (1, 5, 25)
        AND driver_id IS NOT NULL
        AND milestone_achieved = true  -- Solo milestones alcanzados (dentro de ventana)
    ORDER BY driver_id, milestone_trips, lead_date DESC, achieved_date ASC
),
base_claims_raw AS (
    -- Fuente core: ops.v_cabinet_milestones_achieved_from_payment_calc (vista canónica)
    -- Filtra solo claims de Yango (partner) para cabinet con milestones 1, 5, 25
    -- REGLA CANÓNICA: Solo generar claim si existe milestone achieved dentro de ventana de 14 días
    SELECT 
        m.driver_id,
        pc_agg.person_key,
        pc_agg.lead_date,
        m.milestone_value,
        -- Aplicar reglas de negocio para expected_amount desde catálogo
        ma.expected_amount
    FROM ops.v_cabinet_milestones_achieved_from_payment_calc m
    INNER JOIN payment_calc_agg pc_agg
        ON pc_agg.driver_id = m.driver_id
        AND pc_agg.milestone_trips = m.milestone_value
    INNER JOIN milestone_amounts ma
        ON ma.milestone_value = m.milestone_value
    WHERE m.achieved_flag = true
        AND m.milestone_value IN (1, 5, 25)
        AND m.driver_id IS NOT NULL
        -- Ventana de 14 días: achieved_date debe estar dentro de lead_date + 14 días
        AND m.achieved_date::date <= (pc_agg.lead_date + INTERVAL '14 days')::date
        AND m.achieved_date::date >= pc_agg.lead_date
),
base_claims_dedup AS (
    -- Deduplicación: 1 fila por (driver_id + milestone_value), quedarse con lead_date más reciente
    SELECT DISTINCT ON (driver_id, milestone_value)
        driver_id,
        person_key,
        lead_date,
        milestone_value,
        expected_amount
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
) p_exact ON true
-- Optimización: solo ejecutar estos JOINs cuando no hay pago exacto
LEFT JOIN LATERAL (
    -- ¿Existe pago para este driver pero otro milestone?
    SELECT payment_key
    FROM ops.v_yango_payments_ledger_latest_enriched p
    WHERE p.driver_id_final = c.driver_id
        AND p.milestone_value != c.milestone_value
        AND p.is_paid = true
    LIMIT 1
) p_other_milestone ON p_exact.payment_key IS NULL 
    AND c.driver_id IS NOT NULL
    AND c.milestone_value IS NOT NULL
LEFT JOIN LATERAL (
    -- ¿Existe pago para este milestone pero solo por person_key?
    SELECT payment_key
    FROM ops.v_yango_payments_ledger_latest_enriched p
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
-- Comentarios de la Vista
-- ============================================================================
COMMENT ON VIEW ops.v_claims_payment_status_cabinet IS 
'Vista orientada a cobranza que responde: "Para cada conductor que entró por cabinet y alcanzó un milestone, ¿nos pagaron o no, cuándo vence, qué tan vencido está, y por qué no pagaron si no pagaron?". Proporciona aging (vencimiento), reason_code (diagnóstico de no pago) y action_priority (prioridad operativa) para soportar gestión de cobranza eficiente. Devuelve exactamente 1 fila por claim (driver_id + milestone).';

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

COMMENT ON COLUMN ops.v_claims_payment_status_cabinet.days_overdue IS 
'Número de días vencidos. 0 si el claim no está vencido.';

COMMENT ON COLUMN ops.v_claims_payment_status_cabinet.bucket_overdue IS 
'Bucket de aging: 0_not_due (no vencido), 1_1_7 (1-7 días), 2_8_14 (8-14 días), 3_15_30 (15-30 días), 4_31_60 (31-60 días), 5_60_plus (más de 60 días).';

COMMENT ON COLUMN ops.v_claims_payment_status_cabinet.expected_amount IS 
'Monto esperado del claim según reglas de negocio: milestone 1=25, 5=35, 25=100.';

COMMENT ON COLUMN ops.v_claims_payment_status_cabinet.paid_flag IS 
'Boolean indicando si el claim tiene al menos un pago asociado (is_paid=true, driver_id_final=driver_id, milestone_value=milestone_value).';

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
'Razón del estado de pago (compatibilidad con versión anterior): ''payment_found'' si existe pago, ''no_payment_found'' si no existe pago.';

COMMENT ON COLUMN ops.v_claims_payment_status_cabinet.reason_code IS 
'Código de razón detallado con prioridad: ''paid'' (pagado), ''missing_driver_id'' (sin driver_id), ''missing_milestone'' (sin milestone), ''payment_found_other_milestone'' (existe pago para otro milestone), ''payment_found_person_key_only'' (existe pago solo por person_key), ''no_payment_found'' (no existe pago).';

COMMENT ON COLUMN ops.v_claims_payment_status_cabinet.action_priority IS 
'Prioridad operativa para cobranza: ''P0_confirmed_paid'' (pagado confirmado), ''P0_collect_now'' (cobrar ahora: 15-60+ días vencido), ''P1_watch'' (vigilar: 8-14 días vencido), ''P2_not_due'' (no vencido).';
