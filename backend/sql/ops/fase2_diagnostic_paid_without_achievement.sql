-- ============================================================================
-- FASE 2: Diagnóstico PAID_WITHOUT_ACHIEVEMENT
-- ============================================================================
-- PROPÓSITO:
-- Diagnosticar y clasificar casos PAID_WITHOUT_ACHIEVEMENT en causas reales.
-- Sin modificar reglas, sin recalcular milestones, solo evidencia SQL.
--
-- METODOLOGÍA:
-- Paso 1: Caso ejemplo completo (este archivo)
-- Paso 2: Clasificación sistemática por hipótesis
-- Paso 3: Conclusión y documentación
-- ============================================================================

-- ============================================================================
-- QUERY 1: CASO EJEMPLO COMPLETO - PAID_WITHOUT_ACHIEVEMENT
-- ============================================================================
-- OBJETIVO:
-- Seleccionar UN caso de PAID_WITHOUT_ACHIEVEMENT y mostrar TODA la evidencia:
-- - Detalles del PAID (cuándo pagó Yango, cómo se hizo el matching)
-- - Búsqueda exhaustiva en ACHIEVED (por driver_id, por person_key)
-- - Reglas de pago aplicables (window_days, valid_from, valid_to)
--
-- HIPÓTESIS A VERIFICAR:
-- a) Lag / falta de refresh
-- b) Ventanas de tiempo distintas (window_days)
-- c) Falta real de trips en fuente operativa
-- d) Diferencia de lógica entre Yango y achieved
-- ============================================================================

-- PASO 1: Seleccionar caso ejemplo
WITH sample_case AS (
    SELECT 
        driver_id,
        milestone_value,
        paid_person_key,
        pay_date
    FROM ops.v_cabinet_milestones_reconciled
    WHERE reconciliation_status = 'PAID_WITHOUT_ACHIEVEMENT'
        AND driver_id IS NOT NULL
    ORDER BY pay_date DESC, driver_id, milestone_value
    LIMIT 1
)
-- PASO 2: Detalles del PAID
SELECT 
    'PAID' AS evidence_type,
    sc.driver_id,
    sc.milestone_value,
    sc.paid_person_key AS person_key,
    sc.pay_date,
    p.payment_key,
    p.identity_status,
    p.match_rule,
    p.match_confidence,
    p.raw_driver_name,
    p.driver_name_normalized,
    p.driver_id_original,
    p.driver_id_enriched,
    p.latest_snapshot_at AS snapshot_at,
    NULL::date AS achieved_date,
    NULL::integer AS achieved_trips,
    NULL::integer AS window_days,
    NULL::date AS rule_valid_from,
    NULL::date AS rule_valid_to
FROM sample_case sc
INNER JOIN ops.v_cabinet_milestones_paid p
    ON p.driver_id = sc.driver_id
    AND p.milestone_value = sc.milestone_value

UNION ALL

-- PASO 3: Búsqueda en ACHIEVED (por driver_id)
SELECT 
    'ACHIEVED_by_driver_id' AS evidence_type,
    sc.driver_id,
    sc.milestone_value,
    a.person_key,
    NULL::date AS pay_date,
    NULL::text AS payment_key,
    NULL::text AS identity_status,
    NULL::text AS match_rule,
    NULL::text AS match_confidence,
    NULL::text AS raw_driver_name,
    NULL::text AS driver_name_normalized,
    NULL::text AS driver_id_original,
    NULL::text AS driver_id_enriched,
    NULL::timestamp AS snapshot_at,
    a.achieved_date,
    a.achieved_trips_in_window AS achieved_trips,
    a.window_days,
    a.rule_valid_from,
    a.rule_valid_to
FROM sample_case sc
LEFT JOIN ops.v_cabinet_milestones_achieved a
    ON a.driver_id = sc.driver_id
    AND a.milestone_value = sc.milestone_value

UNION ALL

-- PASO 4: Búsqueda en ACHIEVED (por person_key - por si hay diferencia de identidad)
SELECT 
    'ACHIEVED_by_person_key' AS evidence_type,
    sc.driver_id,
    sc.milestone_value,
    a.person_key,
    NULL::date AS pay_date,
    NULL::text AS payment_key,
    NULL::text AS identity_status,
    NULL::text AS match_rule,
    NULL::text AS match_confidence,
    NULL::text AS raw_driver_name,
    NULL::text AS driver_name_normalized,
    NULL::text AS driver_id_original,
    NULL::text AS driver_id_enriched,
    NULL::timestamp AS snapshot_at,
    a.achieved_date,
    a.achieved_trips_in_window AS achieved_trips,
    a.window_days,
    a.rule_valid_from,
    a.rule_valid_to
FROM sample_case sc
LEFT JOIN ops.v_cabinet_milestones_achieved a
    ON a.person_key = sc.paid_person_key
    AND a.milestone_value = sc.milestone_value
WHERE a.person_key IS NOT NULL  -- Solo si existe

UNION ALL

-- PASO 5: Reglas de pago aplicables
SELECT 
    'PAYMENT_RULES' AS evidence_type,
    sc.driver_id,
    sc.milestone_value,
    NULL::uuid AS person_key,
    NULL::date AS pay_date,
    NULL::text AS payment_key,
    NULL::text AS identity_status,
    NULL::text AS match_rule,
    NULL::text AS match_confidence,
    pr.origin_tag || ' / milestone=' || pr.milestone_trips AS raw_driver_name,
    NULL::text AS driver_name_normalized,
    NULL::text AS driver_id_original,
    NULL::text AS driver_id_enriched,
    NULL::timestamp AS snapshot_at,
    NULL::date AS achieved_date,
    NULL::integer AS achieved_trips,
    pr.window_days,
    pr.valid_from AS rule_valid_from,
    pr.valid_to AS rule_valid_to
FROM sample_case sc
CROSS JOIN ops.partner_payment_rules pr
WHERE pr.origin_tag = 'cabinet'
    AND pr.milestone_trips = sc.milestone_value
    AND pr.is_active = true

ORDER BY evidence_type;

-- ============================================================================
-- QUERY 2: VIAJES REALES (ejecutar DESPUÉS del Query 1)
-- ============================================================================
-- INSTRUCCIÓN:
-- 1. Ejecutar Query 1 y anotar el driver_id del resultado
-- 2. Reemplazar 'DRIVER_ID_AQUI' con ese driver_id
-- 3. Ejecutar este query para ver viajes reales en summary_daily
-- ============================================================================
/*
-- REPLACE 'DRIVER_ID_AQUI' con el driver_id del Query 1
SELECT 
    to_date(date_file, 'DD-MM-YYYY') AS prod_date,
    count_orders_completed AS trips,
    SUM(count_orders_completed) OVER (ORDER BY to_date(date_file, 'DD-MM-YYYY')) AS cumulative_trips
FROM public.summary_daily
WHERE driver_id = 'DRIVER_ID_AQUI'
    AND date_file IS NOT NULL
    AND date_file ~ '^\d{2}-\d{2}-\d{4}$'
    AND count_orders_completed > 0
ORDER BY prod_date DESC
LIMIT 100;
*/

-- ============================================================================
-- INTERPRETACIÓN DEL QUERY 1
-- ============================================================================
-- Este query retorna múltiples filas con evidence_type:
--
-- 1. "PAID": Información completa del pago reconocido por Yango
--    - pay_date: Cuándo pagó Yango
--    - identity_status, match_rule: Calidad del matching
--    - snapshot_at: Timestamp del ledger
--
-- 2. "ACHIEVED_by_driver_id": Búsqueda en ACHIEVED por driver_id exacto
--    - Si existe: muestra achieved_date, achieved_trips, window_days
--    - Si NO existe: retorna fila con achieved_date=NULL (confirmar PAID_WITHOUT_ACHIEVEMENT)
--
-- 3. "ACHIEVED_by_person_key": Búsqueda alternativa por person_key
--    - Solo aparece si existe match por person_key pero no por driver_id
--    - Indica posible problema de identidad
--
-- 4. "PAYMENT_RULES": Reglas de pago aplicables para este milestone
--    - window_days: Ventana de tiempo para alcanzar el milestone
--    - valid_from, valid_to: Vigencia de la regla
--
-- ANÁLISIS ESPERADO:
-- - Si "ACHIEVED_by_driver_id" tiene achieved_date=NULL → confirmar PAID_WITHOUT_ACHIEVEMENT
-- - Comparar pay_date con rule_valid_from/valid_to (¿estaba vigente la regla?)
-- - Revisar window_days (¿cuántos días tenía para alcanzar el milestone?)
-- - Revisar identity_status y match_rule (¿calidad del matching es confiable?)
-- ============================================================================

