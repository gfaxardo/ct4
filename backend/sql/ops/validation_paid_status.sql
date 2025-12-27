-- ============================================================================
-- VALIDACIÓN: Total Paid = 0 en Pagos Yango
-- Objetivo: Entender por qué Total Paid es 0 y documentar la realidad
-- ============================================================================

-- 1) CONTEOS POR paid_status EN ops.v_yango_payments_claims_cabinet_14d
-- Esto muestra la distribución real de estados de pago en la vista de claims
SELECT 
    paid_status,
    COUNT(*) AS count_rows,
    SUM(expected_amount) AS total_expected_amount,
    COUNT(DISTINCT driver_id) AS count_distinct_drivers,
    COUNT(DISTINCT person_key) AS count_distinct_persons
FROM ops.v_yango_payments_claims_cabinet_14d
GROUP BY paid_status
ORDER BY paid_status;

-- 2) CONTEOS ESPECÍFICOS DE paid_status='paid'
-- Verificar si realmente existen registros marcados como 'paid'
SELECT 
    'paid' AS paid_status,
    COUNT(*) AS count_paid_rows,
    SUM(expected_amount) AS total_paid_amount,
    COUNT(DISTINCT driver_id) AS count_distinct_drivers_with_paid,
    MIN(due_date) AS min_due_date,
    MAX(due_date) AS max_due_date
FROM ops.v_yango_payments_claims_cabinet_14d
WHERE paid_status = 'paid';

-- 3) REGISTROS EN ops.v_yango_payments_ledger_latest
-- Total de registros en el ledger de pagos
SELECT 
    COUNT(*) AS total_ledger_rows,
    COUNT(DISTINCT driver_id) AS count_distinct_drivers,
    COUNT(DISTINCT milestone_value) AS count_distinct_milestones,
    COUNT(DISTINCT payment_key) AS count_distinct_payment_keys,
    MIN(pay_date) AS min_pay_date,
    MAX(pay_date) AS max_pay_date,
    SUM(CASE WHEN is_paid = true THEN 1 ELSE 0 END) AS count_is_paid_true
FROM ops.v_yango_payments_ledger_latest;

-- 4) MATCHES REALES (driver_id + milestone_value) ENTRE CLAIMS Y LEDGER
-- Verificar cuántos matches existen basados en driver_id + milestone_value
SELECT 
    COUNT(*) AS count_matches,
    SUM(c.expected_amount) AS total_matched_amount,
    COUNT(DISTINCT c.driver_id) AS count_distinct_drivers_matched
FROM ops.v_yango_payments_claims_cabinet_14d c
INNER JOIN ops.v_yango_payments_ledger_latest l
    ON c.driver_id = l.driver_id 
    AND c.milestone_value = l.milestone_value
WHERE c.driver_id IS NOT NULL;

-- 5) REGISTROS CON driver_id NULL EN CLAIMS
-- Verificar si hay claims sin driver_id (no matchables por driver_id)
SELECT 
    COUNT(*) AS count_without_driver_id,
    SUM(expected_amount) AS total_amount_without_driver_id
FROM ops.v_yango_payments_claims_cabinet_14d
WHERE driver_id IS NULL;

-- 6) VERIFICAR is_paid_effective EN CLAIMS
-- Verificar si hay registros con is_paid_effective = true
SELECT 
    is_paid_effective,
    COUNT(*) AS count_rows,
    SUM(expected_amount) AS total_amount
FROM ops.v_yango_payments_claims_cabinet_14d
GROUP BY is_paid_effective
ORDER BY is_paid_effective;

-- 7) VERIFICAR INDICADORES DE PAGO EN CLAIMS
-- Verificar campos que indican pago: paid_payment_key, paid_date, paid_is_paid
SELECT 
    COUNT(*) AS total_rows,
    COUNT(paid_payment_key) AS count_with_payment_key,
    COUNT(paid_date) AS count_with_paid_date,
    SUM(CASE WHEN paid_is_paid = true THEN 1 ELSE 0 END) AS count_paid_is_paid_true,
    SUM(CASE WHEN is_paid_effective = true THEN 1 ELSE 0 END) AS count_is_paid_effective_true,
    SUM(CASE 
        WHEN (paid_payment_key IS NOT NULL OR paid_date IS NOT NULL OR paid_is_paid = true OR is_paid_effective = true)
        THEN 1 ELSE 0 
    END) AS count_with_any_paid_indicator
FROM ops.v_yango_payments_claims_cabinet_14d;

-- 8) COMPARACIÓN: CLAIMS VS LEDGER (EJEMPLO DETALLADO)
-- Mostrar un ejemplo de por qué no matchea (primeros 10 registros de cada lado)
SELECT 
    'CLAIMS' AS source,
    driver_id,
    milestone_value,
    expected_amount,
    paid_status,
    is_paid_effective,
    paid_payment_key,
    paid_date
FROM ops.v_yango_payments_claims_cabinet_14d
WHERE driver_id IS NOT NULL
ORDER BY expected_amount DESC NULLS LAST
LIMIT 10;

SELECT 
    'LEDGER' AS source,
    driver_id,
    milestone_value,
    payment_key,
    pay_date,
    is_paid
FROM ops.v_yango_payments_ledger_latest
ORDER BY pay_date DESC NULLS LAST
LIMIT 10;

-- ============================================================================
-- RESUMEN EJECUTIVO
-- ============================================================================
-- Ejecutar estas queries para obtener un resumen completo:
-- 1. Si count_paid_rows = 0 → No hay registros con paid_status='paid' → Paid = 0 es correcto
-- 2. Si total_ledger_rows > 0 pero count_matches = 0 → Hay pagos pero no matchean con claims
-- 3. Si count_without_driver_id > 0 → Hay claims sin driver_id (no matchables por driver_id)
-- 4. Si count_with_any_paid_indicator > 0 pero paid_status != 'paid' → La lógica de paid_status no está capturando estos casos

