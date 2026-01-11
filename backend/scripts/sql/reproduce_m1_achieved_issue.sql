-- ============================================================================
-- QUERIES DE REPRODUCCIÓN: M1 Achieved Flag Issue
-- ============================================================================
-- Propósito: Reproducir el problema donde M1 no aparece como "Alcanzado"
--            aunque sí se alcanzó por trips, mientras M5 sí aparece.
--
-- Uso:
--   1. Reemplazar 'DRIVER_ID_AQUI' con un driver_id real del screenshot
--   2. Ejecutar todas las queries en orden
--   3. Comparar resultados para identificar el diff lógico
-- ============================================================================

-- VARIABLE: Reemplazar con driver_id del screenshot
\set driver_id 'DRIVER_ID_AQUI'

-- ============================================================================
-- QUERY 1: Milestone Determinístico (debería decir M1 achieved)
-- ============================================================================
-- Fuente: ops.v_cabinet_milestones_achieved_from_trips
-- Esta vista calcula milestones basándose ÚNICAMENTE en viajes reales
-- desde summary_daily, sin depender de leads ni ventanas de reglas.
-- ============================================================================

SELECT 
    '=== QUERY 1: Milestone Determinístico (v_cabinet_milestones_achieved_from_trips) ===' AS seccion;

SELECT 
    driver_id,
    milestone_value,
    achieved_flag,
    achieved_date,
    trips_at_achieved
FROM ops.v_cabinet_milestones_achieved_from_trips
WHERE driver_id = :'driver_id'
ORDER BY milestone_value;

-- Resultado esperado:
-- - M1: achieved_flag = true, achieved_date = <fecha>, trips_at_achieved >= 1
-- - M5: achieved_flag = true, achieved_date = <fecha>, trips_at_achieved >= 5
-- - M25: achieved_flag = true (si aplica)

\echo ''
\echo '============================================================================'

-- ============================================================================
-- QUERY 2: Driver Matrix (está diciendo M1 false)
-- ============================================================================
-- Fuente: ops.v_payments_driver_matrix_cabinet
-- Esta es la vista que alimenta la UI (Driver Matrix / Resumen por Conductor)
-- ============================================================================

SELECT 
    '=== QUERY 2: Driver Matrix (v_payments_driver_matrix_cabinet) ===' AS seccion;

SELECT 
    driver_id,
    person_key,
    driver_name,
    lead_date,
    week_start,
    origin_tag,
    -- Milestone M1
    m1_achieved_flag,
    m1_achieved_date,
    m1_expected_amount_yango,
    m1_yango_payment_status,
    m1_window_status,
    m1_overdue_days,
    -- Milestone M5
    m5_achieved_flag,
    m5_achieved_date,
    m5_expected_amount_yango,
    m5_yango_payment_status,
    m5_window_status,
    m5_overdue_days,
    -- Milestone M25
    m25_achieved_flag,
    m25_achieved_date,
    m25_expected_amount_yango,
    m25_yango_payment_status,
    m25_window_status,
    m25_overdue_days,
    -- Flags de inconsistencia
    m5_without_m1_flag,
    m25_without_m5_flag,
    milestone_inconsistency_notes
FROM ops.v_payments_driver_matrix_cabinet
WHERE driver_id = :'driver_id'
   OR person_key::text LIKE :'driver_id' || '%';

-- Resultado actual (problemático):
-- - M1: m1_achieved_flag = false o NULL
-- - M5: m5_achieved_flag = true, m5_achieved_date = <fecha>
-- - m5_without_m1_flag = true (indica inconsistencia)

\echo ''
\echo '============================================================================'

-- ============================================================================
-- QUERY 3: Claims Base (fuente intermedia)
-- ============================================================================
-- Fuente: ops.v_claims_payment_status_cabinet
-- Esta vista filtra por milestone_achieved = true desde v_payment_calculation
-- ============================================================================

SELECT 
    '=== QUERY 3: Claims Base (v_claims_payment_status_cabinet) ===' AS seccion;

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
    payment_status,
    reason_code,
    action_priority
FROM ops.v_claims_payment_status_cabinet
WHERE driver_id = :'driver_id'
ORDER BY milestone_value;

-- Resultado esperado:
-- - M1: NO existe (porque milestone_achieved = false en v_payment_calculation)
-- - M5: Existe con paid_flag = false, payment_status = 'not_paid', reason_code = 'no_payment_found'

\echo ''
\echo '============================================================================'

-- ============================================================================
-- QUERY 4: Payment Calculation (fuente raíz)
-- ============================================================================
-- Fuente: ops.v_payment_calculation
-- Esta vista calcula milestone_achieved basándose en:
-- - Leads desde observational.v_conversion_metrics (module_ct_cabinet_leads)
-- - Viajes desde summary_daily
-- - PERO solo dentro de la ventana (window_days)
-- ============================================================================

SELECT 
    '=== QUERY 4: Payment Calculation (v_payment_calculation) ===' AS seccion;

SELECT 
    driver_id,
    person_key,
    milestone_trips AS milestone_value,
    milestone_achieved,
    achieved_date,
    achieved_trips_in_window,
    is_payable,
    lead_date,
    origin_tag,
    rule_scope,
    window_days,
    amount AS expected_amount,
    rule_valid_from,
    rule_valid_to
FROM ops.v_payment_calculation
WHERE driver_id = :'driver_id'
  AND origin_tag = 'cabinet'
  AND rule_scope = 'partner'
  AND milestone_trips IN (1, 5, 25)
ORDER BY milestone_trips;

-- Resultado esperado:
-- - M1: NO existe O milestone_achieved = false (porque no se alcanzó dentro de la ventana)
-- - M5: Existe con milestone_achieved = true, achieved_date = <fecha>

\echo ''
\echo '============================================================================'

-- ============================================================================
-- QUERY 5: Viajes Reales (summary_daily)
-- ============================================================================
-- Verificar viajes acumulados desde el primer viaje
-- ============================================================================

SELECT 
    '=== QUERY 5: Viajes Reales (summary_daily) ===' AS seccion;

WITH trips_accumulated AS (
    SELECT 
        driver_id,
        to_date(date_file, 'DD-MM-YYYY') AS trip_date,
        count_orders_completed AS trips,
        SUM(count_orders_completed) OVER (
            PARTITION BY driver_id 
            ORDER BY to_date(date_file, 'DD-MM-YYYY')
            ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW
        ) AS cumulative_trips
    FROM public.summary_daily
    WHERE driver_id = :'driver_id'
        AND date_file IS NOT NULL
        AND date_file ~ '^\d{2}-\d{2}-\d{4}$'
        AND count_orders_completed > 0
)
SELECT 
    driver_id,
    trip_date,
    trips,
    cumulative_trips,
    CASE 
        WHEN cumulative_trips >= 1 THEN 'M1 ACHIEVED'
        ELSE ''
    END AS m1_status,
    CASE 
        WHEN cumulative_trips >= 5 THEN 'M5 ACHIEVED'
        ELSE ''
    END AS m5_status,
    CASE 
        WHEN cumulative_trips >= 25 THEN 'M25 ACHIEVED'
        ELSE ''
    END AS m25_status
FROM trips_accumulated
WHERE cumulative_trips <= 30  -- Solo primeros 30 trips para ver el patrón
ORDER BY trip_date;

-- Resultado esperado:
-- - Primer día con cumulative_trips >= 1: M1 ACHIEVED
-- - Primer día con cumulative_trips >= 5: M5 ACHIEVED
-- - Si hay M5 pero no M1 en v_payment_calculation, entonces M1 se alcanzó fuera de la ventana

\echo ''
\echo '============================================================================'

-- ============================================================================
-- QUERY 6: Leads Cabinet (module_ct_cabinet_leads)
-- ============================================================================
-- Verificar si existen leads para este driver
-- ============================================================================

SELECT 
    '=== QUERY 6: Leads Cabinet (module_ct_cabinet_leads) ===' AS seccion;

SELECT 
    external_id,
    lead_created_at::date AS lead_date,
    first_name,
    last_name,
    park_phone,
    asset_plate_number
FROM public.module_ct_cabinet_leads
WHERE external_id = :'driver_id'
   OR asset_plate_number IN (
       SELECT DISTINCT asset_plate_number 
       FROM public.module_ct_cabinet_leads 
       WHERE external_id = :'driver_id'
   )
ORDER BY lead_created_at;

-- Resultado esperado:
-- - Puede haber 0, 1 o múltiples leads
-- - Si no hay leads, entonces v_payment_calculation no tendrá registros para este driver

\echo ''
\echo '============================================================================'

-- ============================================================================
-- QUERY 7: Conversion Metrics (observational.v_conversion_metrics)
-- ============================================================================
-- Verificar si el driver está en v_conversion_metrics (requisito para v_payment_calculation)
-- ============================================================================

SELECT 
    '=== QUERY 7: Conversion Metrics (v_conversion_metrics) ===' AS seccion;

SELECT 
    person_key,
    origin_tag,
    lead_date,
    driver_id,
    scout_id
FROM observational.v_conversion_metrics
WHERE driver_id = :'driver_id'
  AND origin_tag = 'cabinet'
ORDER BY lead_date;

-- Resultado esperado:
-- - Si no hay registros, entonces v_payment_calculation no tendrá registros
-- - Si hay registros, entonces v_payment_calculation debería tener registros (pero puede que milestone_achieved = false)

\echo ''
\echo '============================================================================'

-- ============================================================================
-- QUERY 8: Comparación Directa (Diff Lógico)
-- ============================================================================
-- Comparar milestones determinísticos vs milestones en driver matrix
-- ============================================================================

SELECT 
    '=== QUERY 8: Comparación Directa (Diff Lógico) ===' AS seccion;

WITH deterministic AS (
    SELECT 
        driver_id,
        milestone_value,
        achieved_flag,
        achieved_date
    FROM ops.v_cabinet_milestones_achieved_from_trips
    WHERE driver_id = :'driver_id'
),
driver_matrix AS (
    SELECT 
        driver_id,
        1 AS milestone_value,
        m1_achieved_flag AS achieved_flag,
        m1_achieved_date AS achieved_date
    FROM ops.v_payments_driver_matrix_cabinet
    WHERE driver_id = :'driver_id'
    
    UNION ALL
    
    SELECT 
        driver_id,
        5 AS milestone_value,
        m5_achieved_flag AS achieved_flag,
        m5_achieved_date AS achieved_date
    FROM ops.v_payments_driver_matrix_cabinet
    WHERE driver_id = :'driver_id'
    
    UNION ALL
    
    SELECT 
        driver_id,
        25 AS milestone_value,
        m25_achieved_flag AS achieved_flag,
        m25_achieved_date AS achieved_date
    FROM ops.v_payments_driver_matrix_cabinet
    WHERE driver_id = :'driver_id'
)
SELECT 
    COALESCE(d.milestone_value, dm.milestone_value) AS milestone_value,
    d.achieved_flag AS deterministic_achieved,
    d.achieved_date AS deterministic_date,
    dm.achieved_flag AS driver_matrix_achieved,
    dm.achieved_date AS driver_matrix_date,
    CASE 
        WHEN d.achieved_flag = true AND COALESCE(dm.achieved_flag, false) = false THEN '❌ PROBLEMA: Determinístico TRUE pero Driver Matrix FALSE'
        WHEN d.achieved_flag = false AND dm.achieved_flag = true THEN '⚠️ WARNING: Determinístico FALSE pero Driver Matrix TRUE'
        WHEN d.achieved_flag = dm.achieved_flag THEN '✅ OK: Coinciden'
        ELSE '❓ DESCONOCIDO: No hay datos en una de las fuentes'
    END AS diff_status
FROM deterministic d
FULL OUTER JOIN driver_matrix dm 
    ON d.driver_id = dm.driver_id 
    AND d.milestone_value = dm.milestone_value
ORDER BY milestone_value;

-- Resultado esperado:
-- - M1: ❌ PROBLEMA: Determinístico TRUE pero Driver Matrix FALSE
-- - M5: ✅ OK: Coinciden (ambos TRUE)
-- - M25: Depende de si se alcanzó

\echo ''
\echo '============================================================================'
\echo 'FIN DE QUERIES DE REPRODUCCIÓN'
\echo '============================================================================'
\echo ''
\echo 'INSTRUCCIONES:'
\echo '1. Reemplazar :driver_id con un driver_id real del screenshot'
\echo '2. Ejecutar todas las queries en orden'
\echo '3. Revisar Query 8 para ver el diff lógico exacto'
\echo '4. Si Query 8 muestra "PROBLEMA" para M1, entonces se confirma el bug'
\echo ''



