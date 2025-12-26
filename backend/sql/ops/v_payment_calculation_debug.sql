-- ============================================================================
-- DIAGNÓSTICO: ops.v_payment_calculation retorna 0 filas
-- ============================================================================
-- Este archivo contiene queries de diagnóstico para identificar exactamente
-- en qué etapa se pierden las filas en la vista v_payment_calculation.
--
-- Ejecutar cada sección en orden para identificar el cuello de botella.
-- ============================================================================

-- ============================================================================
-- A. CONTEO DE INSUMOS
-- ============================================================================
-- Valida que existan datos en las fuentes base y reglas configuradas

-- A1: Total de filas en v_conversion_metrics
-- Valida: ¿Existen leads procesados?
SELECT COUNT(*) AS total_conversion_metrics
FROM observational.v_conversion_metrics;

-- A2: Conteo por origin_tag en v_conversion_metrics
-- Valida: ¿Qué origin_tags existen y cuántos hay de cada uno?
SELECT 
    origin_tag, 
    COUNT(*) AS count
FROM observational.v_conversion_metrics
GROUP BY origin_tag
ORDER BY count DESC;

-- A3: Total de reglas scout
-- Valida: ¿Existen reglas de scouts configuradas?
SELECT COUNT(*) AS total_scout_rules
FROM ops.scout_payment_rules;

-- A4: Total de reglas partner
-- Valida: ¿Existen reglas de partners configuradas?
SELECT COUNT(*) AS total_partner_rules
FROM ops.partner_payment_rules;

-- A5: Reglas scout por estado is_active
-- Valida: ¿Cuántas reglas scout están activas vs inactivas?
SELECT 
    is_active, 
    COUNT(*) AS count
FROM ops.scout_payment_rules
GROUP BY is_active
ORDER BY is_active DESC;

-- A6: Reglas partner por estado is_active
-- Valida: ¿Cuántas reglas partner están activas vs inactivas?
SELECT 
    is_active, 
    COUNT(*) AS count
FROM ops.partner_payment_rules
GROUP BY is_active
ORDER BY is_active DESC;

-- ============================================================================
-- B. COBERTURA DE VIGENCIA VS lead_date
-- ============================================================================
-- Valida si los lead_date están dentro de las ventanas de vigencia de las reglas

-- B1: Rango de lead_date en v_conversion_metrics
-- Valida: ¿En qué rango de fechas están los leads?
SELECT 
    MIN(lead_date) AS min_lead_date,
    MAX(lead_date) AS max_lead_date,
    COUNT(DISTINCT lead_date) AS distinct_dates,
    COUNT(*) AS total_leads
FROM observational.v_conversion_metrics
WHERE driver_id IS NOT NULL;

-- B2: Rango de valid_from/valid_to en scout_payment_rules (solo activas)
-- Valida: ¿En qué rango de fechas son válidas las reglas scout?
SELECT 
    origin_tag,
    MIN(valid_from) AS min_valid_from,
    MAX(valid_from) AS max_valid_from,
    MIN(valid_to) AS min_valid_to,
    MAX(valid_to) AS max_valid_to,
    COUNT(*) FILTER (WHERE valid_to IS NULL) AS rules_with_null_valid_to,
    COUNT(*) AS total_active_rules
FROM ops.scout_payment_rules
WHERE is_active = true
GROUP BY origin_tag
ORDER BY origin_tag;

-- B3: Rango de valid_from/valid_to en partner_payment_rules (solo activas)
-- Valida: ¿En qué rango de fechas son válidas las reglas partner?
SELECT 
    origin_tag,
    MIN(valid_from) AS min_valid_from,
    MAX(valid_from) AS max_valid_from,
    MIN(valid_to) AS min_valid_to,
    MAX(valid_to) AS max_valid_to,
    COUNT(*) FILTER (WHERE valid_to IS NULL) AS rules_with_null_valid_to,
    COUNT(*) AS total_active_rules
FROM ops.partner_payment_rules
WHERE is_active = true
GROUP BY origin_tag
ORDER BY origin_tag;

-- B4: Conteo de leads que matchean reglas por vigencia (scout)
-- Valida: ¿Cuántos leads tienen reglas scout aplicables según vigencia?
SELECT 
    vcm.origin_tag,
    COUNT(DISTINCT vcm.person_key) AS distinct_persons,
    COUNT(*) AS total_lead_rule_combinations
FROM observational.v_conversion_metrics vcm
INNER JOIN ops.scout_payment_rules spr
    ON spr.origin_tag = vcm.origin_tag
    AND spr.is_active = true
    AND vcm.lead_date >= spr.valid_from
    AND (spr.valid_to IS NULL OR vcm.lead_date <= spr.valid_to)
WHERE vcm.driver_id IS NOT NULL
GROUP BY vcm.origin_tag
ORDER BY vcm.origin_tag;

-- B5: Conteo de leads que matchean reglas por vigencia (partner)
-- Valida: ¿Cuántos leads tienen reglas partner aplicables según vigencia?
SELECT 
    vcm.origin_tag,
    COUNT(DISTINCT vcm.person_key) AS distinct_persons,
    COUNT(*) AS total_lead_rule_combinations
FROM observational.v_conversion_metrics vcm
INNER JOIN ops.partner_payment_rules ppr
    ON ppr.origin_tag = vcm.origin_tag
    AND ppr.is_active = true
    AND vcm.lead_date >= ppr.valid_from
    AND (ppr.valid_to IS NULL OR vcm.lead_date <= ppr.valid_to)
WHERE vcm.driver_id IS NOT NULL
GROUP BY vcm.origin_tag
ORDER BY vcm.origin_tag;

-- B6: Combinado: leads que matchean reglas (scout + partner)
-- Valida: ¿Cuántos leads tienen reglas aplicables en total?
SELECT 
    vcm.origin_tag,
    'scout' AS rule_scope,
    COUNT(DISTINCT vcm.person_key) AS distinct_persons,
    COUNT(*) AS total_combinations
FROM observational.v_conversion_metrics vcm
INNER JOIN ops.scout_payment_rules spr
    ON spr.origin_tag = vcm.origin_tag
    AND spr.is_active = true
    AND vcm.lead_date >= spr.valid_from
    AND (spr.valid_to IS NULL OR vcm.lead_date <= spr.valid_to)
WHERE vcm.driver_id IS NOT NULL
GROUP BY vcm.origin_tag

UNION ALL

SELECT 
    vcm.origin_tag,
    'partner' AS rule_scope,
    COUNT(DISTINCT vcm.person_key) AS distinct_persons,
    COUNT(*) AS total_combinations
FROM observational.v_conversion_metrics vcm
INNER JOIN ops.partner_payment_rules ppr
    ON ppr.origin_tag = vcm.origin_tag
    AND ppr.is_active = true
    AND vcm.lead_date >= ppr.valid_from
    AND (ppr.valid_to IS NULL OR vcm.lead_date <= ppr.valid_to)
WHERE vcm.driver_id IS NOT NULL
GROUP BY vcm.origin_tag
ORDER BY origin_tag, rule_scope;

-- ============================================================================
-- C. VERIFICACIÓN DE JOIN/WHERE EN LA VISTA
-- ============================================================================
-- Replica la lógica de la vista paso a paso para ver dónde se pierden filas

WITH conversion_metrics_base AS (
    -- Paso 1: Base de métricas (igual que en la vista)
    SELECT 
        person_key,
        origin_tag,
        lead_date,
        scout_id,
        driver_id
    FROM observational.v_conversion_metrics
    WHERE driver_id IS NOT NULL
),
all_payment_rules AS (
    -- Paso 2: Unión de reglas (igual que en la vista)
    SELECT 
        id AS rule_id,
        'scout' AS rule_scope,
        origin_tag,
        window_days,
        milestone_trips,
        amount,
        currency,
        valid_from AS rule_valid_from,
        valid_to AS rule_valid_to
    FROM ops.scout_payment_rules
    WHERE is_active = true
    
    UNION ALL
    
    SELECT 
        id AS rule_id,
        'partner' AS rule_scope,
        origin_tag,
        window_days,
        milestone_trips,
        amount,
        currency,
        valid_from AS rule_valid_from,
        valid_to AS rule_valid_to
    FROM ops.partner_payment_rules
    WHERE is_active = true
),
rules_with_metrics AS (
    -- Paso 3: JOIN con filtro de vigencia (igual que en la vista)
    SELECT 
        cmb.person_key,
        cmb.origin_tag,
        cmb.lead_date,
        cmb.scout_id,
        cmb.driver_id,
        apr.rule_id,
        apr.rule_scope,
        apr.milestone_trips,
        apr.window_days,
        apr.amount,
        apr.currency,
        apr.rule_valid_from,
        apr.rule_valid_to
    FROM conversion_metrics_base cmb
    INNER JOIN all_payment_rules apr
        ON apr.origin_tag = cmb.origin_tag
        AND cmb.lead_date >= apr.rule_valid_from
        AND (apr.rule_valid_to IS NULL OR cmb.lead_date <= apr.rule_valid_to)
)
-- Conteo por etapa
SELECT 
    '1. Base (v_conversion_metrics con driver_id)' AS etapa,
    (SELECT COUNT(*) FROM conversion_metrics_base) AS count_base
UNION ALL
SELECT 
    '2. Reglas totales (activas)' AS etapa,
    (SELECT COUNT(*) FROM all_payment_rules) AS count_rules_total
UNION ALL
SELECT 
    '3. Después de JOIN + filtro vigencia (rules_with_metrics)' AS etapa,
    (SELECT COUNT(*) FROM rules_with_metrics) AS count_after_vigency_filter
ORDER BY etapa;

-- ============================================================================
-- D. EJEMPLOS DE FILAS QUE DEBERÍAN EXISTIR
-- ============================================================================
-- Muestra 20 combinaciones de leads + reglas que deberían generar filas,
-- incluso si el milestone no se alcanza (para verificar que el problema no
-- es falta de reglas o vigencia)

WITH conversion_metrics_sample AS (
    SELECT 
        person_key,
        origin_tag,
        lead_date,
        scout_id,
        driver_id
    FROM observational.v_conversion_metrics
    WHERE driver_id IS NOT NULL
    LIMIT 10
),
all_payment_rules_active AS (
    SELECT 
        id AS rule_id,
        'scout' AS rule_scope,
        origin_tag,
        window_days,
        milestone_trips,
        amount,
        currency,
        valid_from AS rule_valid_from,
        valid_to AS rule_valid_to
    FROM ops.scout_payment_rules
    WHERE is_active = true
    
    UNION ALL
    
    SELECT 
        id AS rule_id,
        'partner' AS rule_scope,
        origin_tag,
        window_days,
        milestone_trips,
        amount,
        currency,
        valid_from AS rule_valid_from,
        valid_to AS rule_valid_to
    FROM ops.partner_payment_rules
    WHERE is_active = true
)
SELECT 
    cm.person_key,
    cm.origin_tag,
    cm.lead_date,
    cm.driver_id,
    apr.rule_id,
    apr.rule_scope,
    apr.milestone_trips,
    apr.window_days,
    apr.amount,
    apr.currency,
    apr.rule_valid_from,
    apr.rule_valid_to,
    CASE 
        WHEN cm.lead_date >= apr.rule_valid_from 
            AND (apr.rule_valid_to IS NULL OR cm.lead_date <= apr.rule_valid_to)
        THEN 'VIGENTE'
        ELSE 'NO VIGENTE'
    END AS estado_vigencia
FROM conversion_metrics_sample cm
CROSS JOIN all_payment_rules_active apr
WHERE cm.origin_tag = apr.origin_tag
    AND cm.lead_date >= apr.rule_valid_from
    AND (apr.rule_valid_to IS NULL OR cm.lead_date <= apr.rule_valid_to)
ORDER BY cm.origin_tag, apr.rule_scope, cm.lead_date
LIMIT 20;

-- ============================================================================
-- E. DIAGNÓSTICO ADICIONAL: VALIDACIÓN DE origin_tag
-- ============================================================================
-- Valida que los origin_tags sean exactamente 'cabinet' o 'fleet_migration'

-- E1: origin_tags únicos en v_conversion_metrics
-- Valida: ¿Qué valores de origin_tag existen?
SELECT 
    origin_tag, 
    COUNT(*) AS count
FROM observational.v_conversion_metrics
GROUP BY origin_tag
ORDER BY origin_tag;

-- E2: origin_tags únicos en reglas scout (activas)
-- Valida: ¿Qué valores de origin_tag tienen reglas scout?
SELECT 
    origin_tag, 
    COUNT(*) AS count
FROM ops.scout_payment_rules
WHERE is_active = true
GROUP BY origin_tag
ORDER BY origin_tag;

-- E3: origin_tags únicos en reglas partner (activas)
-- Valida: ¿Qué valores de origin_tag tienen reglas partner?
SELECT 
    origin_tag, 
    COUNT(*) AS count
FROM ops.partner_payment_rules
WHERE is_active = true
GROUP BY origin_tag
ORDER BY origin_tag;

-- ============================================================================
-- F. DIAGNÓSTICO ADICIONAL: PROBLEMA POTENCIAL CON INNER JOIN A summary_daily
-- ============================================================================
-- IMPORTANTE: La vista usa INNER JOIN con summary_daily en trips_from_lead_date
-- Este JOIN elimina combinaciones si no hay producción. Sin embargo, la vista
-- luego usa LEFT JOIN en all_rule_combinations, así que debería mostrar filas
-- aunque no se alcance el milestone (con achieved_date NULL).
-- 
-- Esta query verifica si el problema es falta de datos en summary_daily.

-- F1: ¿Cuántos driver_id de v_conversion_metrics tienen datos en summary_daily?
SELECT 
    COUNT(DISTINCT vcm.driver_id) AS drivers_con_datos_summary,
    (SELECT COUNT(DISTINCT driver_id) 
     FROM observational.v_conversion_metrics 
     WHERE driver_id IS NOT NULL) AS total_drivers_en_vcm,
    COUNT(DISTINCT vcm.driver_id) * 100.0 / 
        NULLIF((SELECT COUNT(DISTINCT driver_id) 
                FROM observational.v_conversion_metrics 
                WHERE driver_id IS NOT NULL), 0) AS porcentaje_cobertura
FROM observational.v_conversion_metrics vcm
INNER JOIN (
    SELECT DISTINCT driver_id
    FROM public.summary_daily
    WHERE date_file IS NOT NULL
        AND date_file ~ '^\d{2}-\d{2}-\d{4}$'
) sdn ON sdn.driver_id = vcm.driver_id
WHERE vcm.driver_id IS NOT NULL;

-- F2: driver_id que NO tienen datos en summary_daily (ejemplos)
-- Valida: ¿Hay drivers sin producción que se perderían?
SELECT 
    vcm.driver_id,
    vcm.person_key,
    vcm.origin_tag,
    vcm.lead_date
FROM observational.v_conversion_metrics vcm
WHERE vcm.driver_id IS NOT NULL
    AND NOT EXISTS (
        SELECT 1
        FROM public.summary_daily sd
        WHERE sd.driver_id = vcm.driver_id
            AND sd.date_file IS NOT NULL
            AND sd.date_file ~ '^\d{2}-\d{2}-\d{4}$'
    )
LIMIT 10;

-- ============================================================================
-- SOLUCIÓN SUGERIDA (NO EJECUTAR - SOLO REFERENCIA)
-- ============================================================================
-- Si el problema es vigencia (valid_from/valid_to), se puede solucionar de dos formas:

-- Opción 1: Ampliar valid_to a NULL (reglas vigentes indefinidamente)
-- UPDATE ops.scout_payment_rules 
-- SET valid_to = NULL 
-- WHERE is_active = true AND valid_to < (SELECT MAX(lead_date) FROM observational.v_conversion_metrics);
-- 
-- UPDATE ops.partner_payment_rules 
-- SET valid_to = NULL 
-- WHERE is_active = true AND valid_to < (SELECT MAX(lead_date) FROM observational.v_conversion_metrics);

-- Opción 2: Establecer valid_from más antiguo (cubrir todo el histórico)
-- UPDATE ops.scout_payment_rules 
-- SET valid_from = (SELECT MIN(lead_date) FROM observational.v_conversion_metrics)
-- WHERE is_active = true;
-- 
-- UPDATE ops.partner_payment_rules 
-- SET valid_from = (SELECT MIN(lead_date) FROM observational.v_conversion_metrics)
-- WHERE is_active = true;

-- ============================================================================
-- RESUMEN EJECUTIVO: CAUSA RAÍZ MÁS PROBABLE
-- ============================================================================
-- 
-- Según el análisis de la vista v_payment_calculation.sql, la causa raíz más probable
-- de que la vista retorne 0 filas es:
--
-- 1. PROBLEMA DE VIGENCIA (valid_from/valid_to): El INNER JOIN en rules_with_metrics
--    (líneas 69-73) filtra combinaciones donde lead_date NO está dentro del rango
--    de vigencia de las reglas. Si todos los lead_date están fuera de las ventanas
--    de vigencia (valid_from > lead_date o valid_to < lead_date), el resultado será 0 filas.
--
-- 2. FALTA DE REGLAS ACTIVAS: Si no hay reglas con is_active=true en las tablas
--    scout_payment_rules y partner_payment_rules, el CTE all_payment_rules estará vacío.
--
-- 3. MISMATCH DE origin_tag: Si los origin_tags en v_conversion_metrics no coinciden
--    exactamente con 'cabinet' o 'fleet_migration' en las reglas, el JOIN por origin_tag
--    no producirá matches.
--
-- 4. FALTA DE DATOS BASE: Si no hay filas en v_conversion_metrics con driver_id IS NOT NULL,
--    la vista estará vacía desde el inicio.
--
-- NOTA: El INNER JOIN con summary_daily (línea 110) NO debería causar 0 filas porque
--       all_rule_combinations hace LEFT JOIN desde rules_with_metrics, preservando todas
--       las combinaciones válidas incluso si no hay producción (con achieved_date NULL).
--
-- ORDEN DE DIAGNÓSTICO RECOMENDADO:
--   1. Ejecutar queries B (vigencia) para confirmar si hay overlap entre lead_date y vigencia
--   2. Ejecutar query C para ver en qué etapa se pierden las filas
--   3. Ejecutar queries E (origin_tag) para verificar coincidencias
--   4. Ejecutar queries A para confirmar existencia de datos base y reglas activas
--
-- ============================================================================

