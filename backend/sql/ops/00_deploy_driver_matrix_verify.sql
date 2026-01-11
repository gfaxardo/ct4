-- ============================================================================
-- SCRIPT DE VERIFICACIÓN: Driver Matrix Views
-- ============================================================================
-- PROPÓSITO:
-- Verifica que todas las vistas necesarias para driver-matrix existen y funcionan
-- correctamente. Ejecutar DESPUÉS de 00_deploy_driver_matrix.sql
-- ============================================================================

-- ============================================================================
-- VERIFICACIÓN 1: Listar existencia de las 5 vistas críticas
-- ============================================================================

SELECT 
    '=== VERIFICACIÓN: EXISTENCIA DE VISTAS ===' AS seccion,
    table_name AS vista,
    CASE 
        WHEN EXISTS (
            SELECT 1 FROM information_schema.views 
            WHERE table_schema = 'ops' AND table_name = v.table_name
        ) THEN '✅ EXISTE'
        ELSE '❌ NO EXISTE'
    END AS estado
FROM (
    VALUES 
        ('v_payment_calculation'),
        ('v_claims_payment_status_cabinet'),
        ('v_yango_cabinet_claims_for_collection'),
        ('v_yango_payments_claims_cabinet_14d'),
        ('v_payments_driver_matrix_cabinet')
) AS v(table_name)
ORDER BY v.table_name;

-- ============================================================================
-- VERIFICACIÓN 2: Sample de 20 filas de la vista final
-- ============================================================================

SELECT 
    '=== SAMPLE: 20 FILAS DE v_payments_driver_matrix_cabinet ===' AS seccion,
    driver_id,
    person_key,
    driver_name,
    lead_date,
    week_start,
    origin_tag,
    connected_flag,
    connected_date,
    m1_achieved_flag,
    m1_achieved_date,
    m1_yango_payment_status,
    m1_window_status,
    m1_overdue_days,
    m5_achieved_flag,
    m5_achieved_date,
    m5_yango_payment_status,
    m5_window_status,
    m5_overdue_days,
    m25_achieved_flag,
    m25_achieved_date,
    m25_yango_payment_status,
    m25_window_status,
    m25_overdue_days
FROM ops.v_payments_driver_matrix_cabinet
ORDER BY lead_date DESC NULLS LAST, driver_name ASC NULLS LAST
LIMIT 20;

-- ============================================================================
-- VERIFICACIÓN 3: Sanity Check - Duplicados por driver_id
-- ============================================================================
-- Debe retornar 0 filas (no debe haber duplicados)

SELECT 
    '=== SANITY CHECK: DUPLICADOS POR driver_id ===' AS seccion,
    driver_id,
    COUNT(*) AS count_rows
FROM ops.v_payments_driver_matrix_cabinet
GROUP BY driver_id
HAVING COUNT(*) > 1;

-- Si la query anterior retorna filas, hay un problema de duplicación.
-- Debe retornar 0 filas para pasar el sanity check.

-- ============================================================================
-- VERIFICACIÓN 4: Conteos básicos
-- ============================================================================

SELECT 
    '=== VERIFICACIÓN: CONTEOS BÁSICOS ===' AS seccion,
    COUNT(*) AS total_drivers,
    COUNT(*) FILTER (WHERE m1_achieved_flag = true) AS drivers_with_m1,
    COUNT(*) FILTER (WHERE m5_achieved_flag = true) AS drivers_with_m5,
    COUNT(*) FILTER (WHERE m25_achieved_flag = true) AS drivers_with_m25,
    COUNT(*) FILTER (WHERE connected_flag = true) AS drivers_connected,
    COUNT(*) FILTER (WHERE origin_tag IS NOT NULL) AS drivers_with_origin_tag,
    COUNT(DISTINCT driver_id) AS unique_driver_ids,
    COUNT(*) - COUNT(DISTINCT driver_id) AS duplicate_count
FROM ops.v_payments_driver_matrix_cabinet;

-- ============================================================================
-- VERIFICACIÓN 5: Distribución de milestones
-- ============================================================================

SELECT 
    '=== VERIFICACIÓN: DISTRIBUCIÓN DE MILESTONES ===' AS seccion,
    COUNT(*) AS total_drivers,
    COUNT(*) FILTER (WHERE m1_achieved_flag = true) AS count_m1,
    COUNT(*) FILTER (WHERE m5_achieved_flag = true) AS count_m5,
    COUNT(*) FILTER (WHERE m25_achieved_flag = true) AS count_m25,
    COUNT(*) FILTER (WHERE m1_achieved_flag = true AND m5_achieved_flag = true) AS count_m1_and_m5,
    COUNT(*) FILTER (WHERE m1_achieved_flag = true AND m5_achieved_flag = true AND m25_achieved_flag = true) AS count_all_milestones
FROM ops.v_payments_driver_matrix_cabinet;

-- ============================================================================
-- VERIFICACIÓN 6: Distribución de yango_payment_status por milestone
-- ============================================================================

SELECT 
    '=== VERIFICACIÓN: DISTRIBUCIÓN YANGO PAYMENT STATUS ===' AS seccion,
    'M1' AS milestone,
    m1_yango_payment_status AS payment_status,
    COUNT(*) AS count_rows
FROM ops.v_payments_driver_matrix_cabinet
WHERE m1_achieved_flag = true
GROUP BY m1_yango_payment_status

UNION ALL

SELECT 
    'M5' AS milestone,
    m5_yango_payment_status AS payment_status,
    COUNT(*) AS count_rows
FROM ops.v_payments_driver_matrix_cabinet
WHERE m5_achieved_flag = true
GROUP BY m5_yango_payment_status

UNION ALL

SELECT 
    'M25' AS milestone,
    m25_yango_payment_status AS payment_status,
    COUNT(*) AS count_rows
FROM ops.v_payments_driver_matrix_cabinet
WHERE m25_achieved_flag = true
GROUP BY m25_yango_payment_status

ORDER BY milestone, payment_status;

-- ============================================================================
-- VERIFICACIÓN 7: Distribución de window_status por milestone
-- ============================================================================

SELECT 
    '=== VERIFICACIÓN: DISTRIBUCIÓN WINDOW STATUS ===' AS seccion,
    'M1' AS milestone,
    m1_window_status AS window_status,
    COUNT(*) AS count_rows
FROM ops.v_payments_driver_matrix_cabinet
WHERE m1_achieved_flag = true
GROUP BY m1_window_status

UNION ALL

SELECT 
    'M5' AS milestone,
    m5_window_status AS window_status,
    COUNT(*) AS count_rows
FROM ops.v_payments_driver_matrix_cabinet
WHERE m5_achieved_flag = true
GROUP BY m5_window_status

UNION ALL

SELECT 
    'M25' AS milestone,
    m25_window_status AS window_status,
    COUNT(*) AS count_rows
FROM ops.v_payments_driver_matrix_cabinet
WHERE m25_achieved_flag = true
GROUP BY m25_window_status

ORDER BY milestone, window_status;

-- ============================================================================
-- VERIFICACIÓN 8: Verificar expected_amounts (reglas de negocio)
-- ============================================================================

SELECT 
    '=== VERIFICACIÓN: EXPECTED AMOUNTS ===' AS seccion,
    'M1' AS milestone,
    COUNT(*) AS count_rows,
    COUNT(*) FILTER (WHERE m1_expected_amount_yango = 25) AS count_correct_amount,
    COUNT(*) FILTER (WHERE m1_expected_amount_yango != 25 AND m1_expected_amount_yango IS NOT NULL) AS count_incorrect_amount
FROM ops.v_payments_driver_matrix_cabinet
WHERE m1_achieved_flag = true

UNION ALL

SELECT 
    'M5' AS milestone,
    COUNT(*) AS count_rows,
    COUNT(*) FILTER (WHERE m5_expected_amount_yango = 35) AS count_correct_amount,
    COUNT(*) FILTER (WHERE m5_expected_amount_yango != 35 AND m5_expected_amount_yango IS NOT NULL) AS count_incorrect_amount
FROM ops.v_payments_driver_matrix_cabinet
WHERE m5_achieved_flag = true

UNION ALL

SELECT 
    'M25' AS milestone,
    COUNT(*) AS count_rows,
    COUNT(*) FILTER (WHERE m25_expected_amount_yango = 100) AS count_correct_amount,
    COUNT(*) FILTER (WHERE m25_expected_amount_yango != 100 AND m25_expected_amount_yango IS NOT NULL) AS count_incorrect_amount
FROM ops.v_payments_driver_matrix_cabinet
WHERE m25_achieved_flag = true

ORDER BY milestone;

-- ============================================================================
-- FIN DEL SCRIPT DE VERIFICACIÓN
-- ============================================================================
-- Revisa los resultados de cada sección:
-- 1. Todas las vistas deben existir (✅ EXISTE)
-- 2. Sample debe mostrar 20 filas válidas
-- 3. Sanity check de duplicados debe retornar 0 filas
-- 4. Conteos básicos deben ser consistentes
-- 5-8. Distribuciones deben tener valores razonables
-- ============================================================================



