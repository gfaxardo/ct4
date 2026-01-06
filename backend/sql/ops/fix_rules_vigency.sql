-- ============================================================================
-- FIX: Problema de 0 filas en ops.v_payment_calculation por vigencia de reglas
-- ============================================================================
-- Objetivo: Asegurar que existan reglas activas cuya ventana valid_from/valid_to
-- cubra el rango de lead_date presente en observational.v_conversion_metrics.
--
-- IMPORTANTE: No toca summary_daily ni identity_links.
-- ============================================================================

-- ============================================================================
-- PASO 1 — OBTENER RANGOS REALES (SOLO LECTURA)
-- ============================================================================
-- Ejecutar estas queries primero para entender el estado actual

-- 1) Rango de lead_date en v_conversion_metrics
SELECT 
    MIN(lead_date) AS min_lead_date, 
    MAX(lead_date) AS max_lead_date,
    COUNT(*) AS total_leads,
    COUNT(DISTINCT lead_date) AS distinct_lead_dates
FROM observational.v_conversion_metrics;

-- 2) Reglas activas scout y su rango de vigencia
SELECT 
    'scout' AS scope,
    MIN(valid_from) AS min_valid_from,
    MAX(valid_from) AS max_valid_from,
    MIN(valid_to) AS min_valid_to,
    MAX(valid_to) AS max_valid_to,
    COUNT(*) FILTER (WHERE is_active) AS active_count,
    COUNT(*) FILTER (WHERE NOT is_active) AS inactive_count,
    COUNT(*) AS total_count,
    COUNT(*) FILTER (WHERE valid_to IS NULL) AS rules_with_null_valid_to
FROM ops.scout_payment_rules;

-- 2) Reglas activas partner y su rango de vigencia
SELECT 
    'partner' AS scope,
    MIN(valid_from) AS min_valid_from,
    MAX(valid_from) AS max_valid_from,
    MIN(valid_to) AS min_valid_to,
    MAX(valid_to) AS max_valid_to,
    COUNT(*) FILTER (WHERE is_active) AS active_count,
    COUNT(*) FILTER (WHERE NOT is_active) AS inactive_count,
    COUNT(*) AS total_count,
    COUNT(*) FILTER (WHERE valid_to IS NULL) AS rules_with_null_valid_to
FROM ops.partner_payment_rules;

-- 3) Overlap: cuántos leads matchean reglas activas por vigencia
WITH lead_range AS (
    SELECT MIN(lead_date) AS min_lead, MAX(lead_date) AS max_lead
    FROM observational.v_conversion_metrics
)
SELECT 
    'scout' AS scope,
    COUNT(*) AS matching_leads,
    COUNT(DISTINCT m.person_key) AS distinct_persons
FROM observational.v_conversion_metrics m
INNER JOIN ops.scout_payment_rules r
    ON r.is_active = TRUE
    AND m.lead_date >= r.valid_from
    AND (r.valid_to IS NULL OR m.lead_date <= r.valid_to)

UNION ALL

SELECT 
    'partner' AS scope,
    COUNT(*) AS matching_leads,
    COUNT(DISTINCT m.person_key) AS distinct_persons
FROM observational.v_conversion_metrics m
INNER JOIN ops.partner_payment_rules r
    ON r.is_active = TRUE
    AND m.lead_date >= r.valid_from
    AND (r.valid_to IS NULL OR m.lead_date <= r.valid_to);

-- ============================================================================
-- PASO 2 — FIX MÍNIMO RECOMENDADO (EJECUTAR SOLO SI matching_leads=0)
-- ============================================================================
-- ATENCIÓN: Ejecutar estas queries SOLO después de confirmar que matching_leads=0
-- en el paso anterior. Estas queries modifican datos.

BEGIN;

-- A) Normalizar valid_to: poner NULL cuando esté antes de min_lead_date
-- Para reglas scout
WITH lead_range AS (
    SELECT MIN(lead_date) AS min_lead, MAX(lead_date) AS max_lead
    FROM observational.v_conversion_metrics
)
UPDATE ops.scout_payment_rules r
SET valid_to = NULL
FROM lead_range lr
WHERE r.is_active = TRUE
    AND r.valid_to IS NOT NULL
    AND r.valid_to < lr.min_lead;

-- Para reglas partner
WITH lead_range AS (
    SELECT MIN(lead_date) AS min_lead, MAX(lead_date) AS max_lead
    FROM observational.v_conversion_metrics
)
UPDATE ops.partner_payment_rules r
SET valid_to = NULL
FROM lead_range lr
WHERE r.is_active = TRUE
    AND r.valid_to IS NOT NULL
    AND r.valid_to < lr.min_lead;

-- B) Normalizar valid_from: bajar a min_lead_date cuando esté después de max_lead_date
-- Para reglas scout
WITH lead_range AS (
    SELECT MIN(lead_date) AS min_lead, MAX(lead_date) AS max_lead
    FROM observational.v_conversion_metrics
)
UPDATE ops.scout_payment_rules r
SET valid_from = lr.min_lead
FROM lead_range lr
WHERE r.is_active = TRUE
    AND r.valid_from > lr.max_lead;

-- Para reglas partner
WITH lead_range AS (
    SELECT MIN(lead_date) AS min_lead, MAX(lead_date) AS max_lead
    FROM observational.v_conversion_metrics
)
UPDATE ops.partner_payment_rules r
SET valid_from = lr.min_lead
FROM lead_range lr
WHERE r.is_active = TRUE
    AND r.valid_from > lr.max_lead;

-- Verificar cambios antes de commit
-- Si estás satisfecho con los cambios, ejecuta: COMMIT;
-- Si no, ejecuta: ROLLBACK;
-- Por defecto dejamos en comentario para que sea explícito:
-- COMMIT;

-- ============================================================================
-- PASO 3 — VERIFICACIÓN POST-FIX
-- ============================================================================
-- Ejecutar estas queries después del fix para confirmar que la vista tiene datos

-- Conteo total en la vista
SELECT COUNT(*) AS rows_in_view 
FROM ops.v_payment_calculation;

-- Conteo por rule_scope y origin_tag
SELECT 
    rule_scope, 
    origin_tag, 
    COUNT(*) AS count
FROM ops.v_payment_calculation
GROUP BY 1, 2
ORDER BY 1, 2;

-- Conteo de achieved vs payable vs total por rule_scope
SELECT 
    rule_scope, 
    COUNT(*) FILTER (WHERE milestone_achieved) AS achieved,
    COUNT(*) FILTER (WHERE is_payable) AS payable,
    COUNT(*) AS total
FROM ops.v_payment_calculation
GROUP BY 1
ORDER BY 1;

-- ============================================================================
-- VALIDACIÓN DEL FILTRO DE VIGENCIA EN LA VISTA
-- ============================================================================
-- La vista backend/sql/ops/v_payment_calculation.sql ya tiene el filtro correcto:
--
-- En all_payment_rules (líneas 34, 50):
--   WHERE is_active = true  ✓ CORRECTO
--
-- En rules_with_metrics (líneas 72-73):
--   AND cmb.lead_date >= apr.rule_valid_from
--   AND (apr.rule_valid_to IS NULL OR cmb.lead_date <= apr.rule_valid_to)  ✓ CORRECTO
--
-- No se requieren cambios en la vista. El problema es de datos (vigencia de reglas).
-- ============================================================================


























