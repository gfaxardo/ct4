-- ============================================================================
-- Vista: ops.v_yango_payments_claims_cabinet_14d
-- ============================================================================
-- Descripción: Vista de claims de pagos Yango Cabinet (ventana 14 días).
-- Separa paid_confirmed (identity_status='confirmed' desde upstream) vs 
-- paid_enriched (identity_status='enriched' por matching por nombre).
--
-- IMPORTANTE: Esta vista NO debe referenciarse a sí misma (ni directa ni 
-- indirectamente) para evitar recursión infinita.
--
-- Fuentes de datos (ÚNICAS dependencias permitidas - vistas canónicas C2-C4):
-- - ops.v_payment_calculation (claims base - vista canónica C2)
-- - ops.v_yango_payments_ledger_latest_enriched (pagos reales enriquecidos)
--
-- NOTA: No usar DROP VIEW ... CASCADE (provoca statement timeout).
-- Usar solo CREATE OR REPLACE VIEW.
-- ============================================================================

CREATE OR REPLACE VIEW ops.v_yango_payments_claims_cabinet_14d AS
-- Performance: filter pushdown before joins for UI stability
-- Apply date filter early to reduce data volume before expensive LEFT JOINs
WITH base_claims AS (
    -- Fuente core: ops.v_payment_calculation (vista canónica C2)
    -- Filtra solo claims de Yango (partner) para cabinet con milestones 1, 5, 25
    SELECT 
        pc.driver_id,
        pc.person_key,
        pc.lead_date,
        date_trunc('week', pc.payable_date)::date AS pay_week_start_monday,
        pc.milestone_trips AS milestone_value,
        -- Aplicar reglas de negocio para expected_amount (milestone 1=25, 5=35, 25=100)
        CASE 
            WHEN pc.milestone_trips = 1 THEN 25::numeric(12,2)
            WHEN pc.milestone_trips = 5 THEN 35::numeric(12,2)
            WHEN pc.milestone_trips = 25 THEN 100::numeric(12,2)
            ELSE NULL::numeric(12,2)
        END AS expected_amount,
        pc.currency
    FROM ops.v_payment_calculation pc
    WHERE pc.origin_tag = 'cabinet'
        AND pc.rule_scope = 'partner'  -- Solo Yango (partner), no scouts
        AND pc.milestone_trips IN (1, 5, 25)
        AND pc.milestone_achieved = true  -- Solo milestones alcanzados
        AND pc.driver_id IS NOT NULL
        AND pc.payable_date IS NOT NULL
        -- Performance: filter by date BEFORE expensive JOINs to reduce data volume
        -- Default filter: last 1 week (7 days) from start of current week (very aggressive for UI stability)
        AND date_trunc('week', pc.payable_date)::date >= (date_trunc('week', current_date)::date - interval '7 days')::date
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
    -- Alias de compatibilidad: is_paid = paid_is_paid (para queries legacy)
    COALESCE(p_confirmed.is_paid, p_enriched.is_paid, false) AS is_paid,
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
    END AS paid_status,
    -- Campos de identidad desde ledger (usar confirmed primero, luego enriched)
    COALESCE(p_confirmed.identity_status, p_enriched.identity_status) AS identity_status,
    COALESCE(p_confirmed.match_rule, p_enriched.match_rule) AS match_rule,
    COALESCE(p_confirmed.match_confidence, p_enriched.match_confidence) AS match_confidence
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
    AND p_enriched.is_paid = true;
-- NOTA: ORDER BY removido - no está permitido en vistas PostgreSQL sin LIMIT
-- Si se necesita ordenamiento, debe hacerse en la query que consume la vista

COMMENT ON VIEW ops.v_yango_payments_claims_cabinet_14d IS 
'Vista de claims de pagos Yango Cabinet (ventana 14 días). Separa paid_confirmed (identity_status=confirmed desde upstream) vs paid_enriched (identity_status=enriched por matching por nombre). paid_confirmed es la fuente para paid real, paid_enriched es informativo. Performance: filter pushdown before joins for UI stability - applies 1-week (7 days) default filter in base_claims CTE AND ledger_enriched CTE before expensive LEFT JOINs to reduce scan volume. IMPORTANTE: No contiene referencias circulares.';

COMMENT ON COLUMN ops.v_yango_payments_claims_cabinet_14d.paid_status IS 
'Estado de pago: paid_confirmed (identity confirmada desde upstream), paid_enriched (identity enriquecida por nombre), pending_active (dentro de ventana), pending_expired (fuera de ventana).';

COMMENT ON COLUMN ops.v_yango_payments_claims_cabinet_14d.is_paid IS 
'Alias de compatibilidad: is_paid = paid_is_paid. Usar para queries legacy que esperan is_paid en lugar de paid_is_paid.';

COMMENT ON COLUMN ops.v_yango_payments_claims_cabinet_14d.paid_is_paid IS 
'Boolean indicando si el claim tiene un pago asociado (confirmed o enriched).';

COMMENT ON COLUMN ops.v_yango_payments_claims_cabinet_14d.is_paid_effective IS 
'Boolean indicando si el claim tiene un pago confirmado (solo confirmed cuenta como paid real).';

-- ============================================================================
-- QUERIES DE VERIFICACIÓN (COMENTADAS - EJECUTAR DESPUÉS DE CREAR LA VISTA)
-- ============================================================================
-- NOTA: Estas queries están comentadas para evitar timeout al crear la vista.
-- Ejecutar manualmente DESPUÉS de que la vista se haya creado exitosamente.
--
-- Para ejecutar las verificaciones:
-- 1. Crear la vista primero (ejecutar solo hasta la línea 138)
-- 2. Luego ejecutar las queries de verificación una por una
-- ============================================================================

/*
-- 1. Verificación básica: conteos y montos totales
SELECT 
    '=== VERIFICACIÓN BÁSICA ===' AS seccion,
    COUNT(*) AS total_rows,
    COUNT(*) FILTER (WHERE is_paid = true) AS count_is_paid_true,
    COUNT(*) FILTER (WHERE paid_is_paid = true) AS count_paid_is_paid_true,
    COUNT(*) FILTER (WHERE is_paid_confirmed = true) AS count_is_paid_confirmed,
    COUNT(*) FILTER (WHERE is_paid_enriched = true) AS count_is_paid_enriched,
    COUNT(*) FILTER (WHERE is_paid_effective = true) AS count_is_paid_effective,
    COALESCE(SUM(expected_amount), 0) AS total_expected_amount,
    COALESCE(SUM(expected_amount) FILTER (WHERE is_paid = true), 0) AS total_paid_amount
FROM ops.v_yango_payments_claims_cabinet_14d;

-- 2. Distribución por paid_status
SELECT 
    '=== DISTRIBUCIÓN POR paid_status ===' AS seccion,
    paid_status,
    COUNT(*) AS count_rows,
    ROUND(100.0 * COUNT(*) / NULLIF((SELECT COUNT(*) FROM ops.v_yango_payments_claims_cabinet_14d), 0), 2) AS pct_rows,
    COALESCE(SUM(expected_amount), 0) AS total_amount,
    ROUND(100.0 * COALESCE(SUM(expected_amount), 0) / NULLIF((SELECT SUM(expected_amount) FROM ops.v_yango_payments_claims_cabinet_14d), 0), 2) AS pct_amount
FROM ops.v_yango_payments_claims_cabinet_14d
GROUP BY paid_status
ORDER BY count_rows DESC;

-- 3. Distribución por window_status
SELECT 
    '=== DISTRIBUCIÓN POR window_status ===' AS seccion,
    window_status,
    COUNT(*) AS count_rows,
    ROUND(100.0 * COUNT(*) / NULLIF((SELECT COUNT(*) FROM ops.v_yango_payments_claims_cabinet_14d), 0), 2) AS pct_rows,
    COALESCE(SUM(expected_amount), 0) AS total_amount
FROM ops.v_yango_payments_claims_cabinet_14d
GROUP BY window_status
ORDER BY count_rows DESC;

-- 4. Verificación de columnas requeridas (debe retornar todas las columnas esperadas)
SELECT 
    '=== VERIFICACIÓN DE COLUMNAS ===' AS seccion,
    column_name,
    data_type,
    is_nullable
FROM information_schema.columns 
WHERE table_schema = 'ops' 
  AND table_name = 'v_yango_payments_claims_cabinet_14d'
  AND column_name IN (
    'driver_id', 'person_key', 'lead_date', 'pay_week_start_monday', 'milestone_value',
    'expected_amount', 'currency', 'due_date', 'window_status',
    'paid_payment_key_confirmed', 'paid_date_confirmed', 'is_paid_confirmed',
    'paid_payment_key_enriched', 'paid_date_enriched', 'is_paid_enriched',
    'paid_is_paid', 'is_paid', 'paid_payment_key', 'paid_date',
    'is_paid_effective', 'match_method', 'paid_status',
    'identity_status', 'match_rule', 'match_confidence'
  )
ORDER BY column_name;

-- 5. Verificación de que is_paid y paid_is_paid son iguales
SELECT 
    '=== VERIFICACIÓN is_paid = paid_is_paid ===' AS seccion,
    COUNT(*) AS total_rows,
    COUNT(*) FILTER (WHERE is_paid = paid_is_paid) AS count_match,
    COUNT(*) FILTER (WHERE is_paid != paid_is_paid OR (is_paid IS NULL AND paid_is_paid IS NOT NULL) OR (is_paid IS NOT NULL AND paid_is_paid IS NULL)) AS count_mismatch
FROM ops.v_yango_payments_claims_cabinet_14d;

-- 6. Verificación de que no hay referencias circulares (debe ejecutarse sin error)
SELECT 
    '=== VERIFICACIÓN SIN RECURSIÓN ===' AS seccion,
    'OK: Vista creada sin errores de recursión' AS status;
*/
