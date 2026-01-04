-- ============================================================================
-- Queries de Verificación: ops.v_payments_driver_matrix_cabinet
-- ============================================================================
-- EJECUTAR DESPUÉS DE CREAR LA VISTA: ops.v_payments_driver_matrix_cabinet
-- ============================================================================
-- NOTA: Estas queries están diseñadas para verificar que la vista funciona
-- correctamente y que los datos cumplen con las expectativas de negocio.
-- ============================================================================

-- 1. Verificación básica: COUNT y métricas generales
SELECT 
    '=== VERIFICACIÓN BÁSICA ===' AS seccion,
    COUNT(*) AS total_drivers,
    COUNT(*) FILTER (WHERE m1_achieved_flag = true) AS drivers_with_m1,
    COUNT(*) FILTER (WHERE m5_achieved_flag = true) AS drivers_with_m5,
    COUNT(*) FILTER (WHERE m25_achieved_flag = true) AS drivers_with_m25,
    COUNT(*) FILTER (WHERE connected_flag = true) AS drivers_connected,
    COUNT(*) FILTER (WHERE origin_tag IS NOT NULL) AS drivers_with_origin_tag,
    COUNT(*) FILTER (WHERE driver_name IS NOT NULL) AS drivers_with_name
FROM ops.v_payments_driver_matrix_cabinet;

-- 2. Sample de 20 filas (ordenadas por lead_date DESC para ver los más recientes)
SELECT 
    '=== SAMPLE 20 FILAS ===' AS seccion,
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
    m5_achieved_flag,
    m5_achieved_date,
    m5_yango_payment_status,
    m5_window_status,
    m25_achieved_flag,
    m25_achieved_date,
    m25_yango_payment_status,
    m25_window_status
FROM ops.v_payments_driver_matrix_cabinet
ORDER BY lead_date DESC
LIMIT 20;

-- 3. Sanity check: verificar que no hay duplicados por driver_id
-- Debe retornar 0 filas (cada driver_id debe aparecer solo una vez)
SELECT 
    '=== SANITY CHECK: DUPLICADOS ===' AS seccion,
    driver_id,
    COUNT(*) AS count_rows
FROM ops.v_payments_driver_matrix_cabinet
GROUP BY driver_id
HAVING COUNT(*) > 1;

-- 4. Sanity check: verificar distribución de milestones
SELECT 
    '=== SANITY CHECK: DISTRIBUCIÓN MILESTONES ===' AS seccion,
    COUNT(*) AS total_drivers,
    COUNT(*) FILTER (WHERE m1_achieved_flag = true) AS count_m1,
    COUNT(*) FILTER (WHERE m5_achieved_flag = true) AS count_m5,
    COUNT(*) FILTER (WHERE m25_achieved_flag = true) AS count_m25,
    COUNT(*) FILTER (WHERE m1_achieved_flag = true AND m5_achieved_flag = true) AS count_m1_and_m5,
    COUNT(*) FILTER (WHERE m1_achieved_flag = true AND m5_achieved_flag = true AND m25_achieved_flag = true) AS count_all_milestones,
    COUNT(*) FILTER (WHERE m1_achieved_flag = false AND m5_achieved_flag = false AND m25_achieved_flag = false) AS count_no_milestones
FROM ops.v_payments_driver_matrix_cabinet;

-- 5. Sanity check: verificar distribución de yango_payment_status por milestone
SELECT 
    '=== SANITY CHECK: DISTRIBUCIÓN YANGO PAYMENT STATUS ===' AS seccion,
    'M1' AS milestone,
    m1_yango_payment_status AS payment_status,
    COUNT(*) AS count_rows,
    COALESCE(SUM(m1_expected_amount_yango), 0) AS total_amount
FROM ops.v_payments_driver_matrix_cabinet
WHERE m1_achieved_flag = true
GROUP BY m1_yango_payment_status
UNION ALL
SELECT 
    'M5' AS milestone,
    m5_yango_payment_status AS payment_status,
    COUNT(*) AS count_rows,
    COALESCE(SUM(m5_expected_amount_yango), 0) AS total_amount
FROM ops.v_payments_driver_matrix_cabinet
WHERE m5_achieved_flag = true
GROUP BY m5_yango_payment_status
UNION ALL
SELECT 
    'M25' AS milestone,
    m25_yango_payment_status AS payment_status,
    COUNT(*) AS count_rows,
    COALESCE(SUM(m25_expected_amount_yango), 0) AS total_amount
FROM ops.v_payments_driver_matrix_cabinet
WHERE m25_achieved_flag = true
GROUP BY m25_yango_payment_status
ORDER BY milestone, payment_status;

-- 6. Sanity check: verificar distribución de window_status por milestone
SELECT 
    '=== SANITY CHECK: DISTRIBUCIÓN WINDOW STATUS ===' AS seccion,
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

-- 7. Sanity check: verificar expected_amounts (deben ser 25, 35, 100 según milestone)
SELECT 
    '=== SANITY CHECK: EXPECTED AMOUNTS ===' AS seccion,
    'M1' AS milestone,
    COUNT(*) AS count_rows,
    COUNT(*) FILTER (WHERE m1_expected_amount_yango = 25) AS count_correct_amount,
    COUNT(*) FILTER (WHERE m1_expected_amount_yango != 25 AND m1_expected_amount_yango IS NOT NULL) AS count_incorrect_amount,
    COUNT(*) FILTER (WHERE m1_expected_amount_yango IS NULL) AS count_null_amount
FROM ops.v_payments_driver_matrix_cabinet
WHERE m1_achieved_flag = true
UNION ALL
SELECT 
    'M5' AS milestone,
    COUNT(*) AS count_rows,
    COUNT(*) FILTER (WHERE m5_expected_amount_yango = 35) AS count_correct_amount,
    COUNT(*) FILTER (WHERE m5_expected_amount_yango != 35 AND m5_expected_amount_yango IS NOT NULL) AS count_incorrect_amount,
    COUNT(*) FILTER (WHERE m5_expected_amount_yango IS NULL) AS count_null_amount
FROM ops.v_payments_driver_matrix_cabinet
WHERE m5_achieved_flag = true
UNION ALL
SELECT 
    'M25' AS milestone,
    COUNT(*) AS count_rows,
    COUNT(*) FILTER (WHERE m25_expected_amount_yango = 100) AS count_correct_amount,
    COUNT(*) FILTER (WHERE m25_expected_amount_yango != 100 AND m25_expected_amount_yango IS NOT NULL) AS count_incorrect_amount,
    COUNT(*) FILTER (WHERE m25_expected_amount_yango IS NULL) AS count_null_amount
FROM ops.v_payments_driver_matrix_cabinet
WHERE m25_achieved_flag = true;

-- 8. Sanity check: verificar overdue_days (debe ser >= 0)
SELECT 
    '=== SANITY CHECK: OVERDUE DAYS ===' AS seccion,
    'M1' AS milestone,
    COUNT(*) AS count_rows,
    COUNT(*) FILTER (WHERE m1_overdue_days < 0) AS count_negative_overdue,
    MIN(m1_overdue_days) AS min_overdue_days,
    MAX(m1_overdue_days) AS max_overdue_days,
    ROUND(AVG(m1_overdue_days), 2) AS avg_overdue_days
FROM ops.v_payments_driver_matrix_cabinet
WHERE m1_achieved_flag = true
UNION ALL
SELECT 
    'M5' AS milestone,
    COUNT(*) AS count_rows,
    COUNT(*) FILTER (WHERE m5_overdue_days < 0) AS count_negative_overdue,
    MIN(m5_overdue_days) AS min_overdue_days,
    MAX(m5_overdue_days) AS max_overdue_days,
    ROUND(AVG(m5_overdue_days), 2) AS avg_overdue_days
FROM ops.v_payments_driver_matrix_cabinet
WHERE m5_achieved_flag = true
UNION ALL
SELECT 
    'M25' AS milestone,
    COUNT(*) AS count_rows,
    COUNT(*) FILTER (WHERE m25_overdue_days < 0) AS count_negative_overdue,
    MIN(m25_overdue_days) AS min_overdue_days,
    MAX(m25_overdue_days) AS max_overdue_days,
    ROUND(AVG(m25_overdue_days), 2) AS avg_overdue_days
FROM ops.v_payments_driver_matrix_cabinet
WHERE m25_achieved_flag = true;

-- 9. Sanity check: verificar origin_tag (debe ser 'cabinet' o 'fleet_migration' o NULL)
SELECT 
    '=== SANITY CHECK: ORIGIN TAG ===' AS seccion,
    origin_tag,
    COUNT(*) AS count_drivers,
    ROUND(100.0 * COUNT(*) / NULLIF((SELECT COUNT(*) FROM ops.v_payments_driver_matrix_cabinet), 0), 2) AS pct_drivers
FROM ops.v_payments_driver_matrix_cabinet
GROUP BY origin_tag
ORDER BY count_drivers DESC;

-- 10. Sanity check: verificar connected_flag y connected_date
SELECT 
    '=== SANITY CHECK: CONNECTED FLAG/DATE ===' AS seccion,
    COUNT(*) AS total_drivers,
    COUNT(*) FILTER (WHERE connected_flag = true) AS count_connected,
    COUNT(*) FILTER (WHERE connected_flag = false) AS count_not_connected,
    COUNT(*) FILTER (WHERE connected_flag = true AND connected_date IS NULL) AS count_connected_flag_true_but_date_null,
    COUNT(*) FILTER (WHERE connected_flag = false AND connected_date IS NOT NULL) AS count_connected_flag_false_but_date_not_null,
    MIN(connected_date) AS min_connected_date,
    MAX(connected_date) AS max_connected_date
FROM ops.v_payments_driver_matrix_cabinet;

-- 11. Sanity check: verificar week_start (debe ser lunes)
-- En PostgreSQL, date_trunc('week', date) devuelve el lunes de la semana
SELECT 
    '=== SANITY CHECK: WEEK_START (DEBE SER LUNES) ===' AS seccion,
    COUNT(*) AS total_drivers,
    COUNT(*) FILTER (WHERE EXTRACT(DOW FROM week_start) = 1) AS count_monday,  -- 1 = lunes en PostgreSQL
    COUNT(*) FILTER (WHERE EXTRACT(DOW FROM week_start) != 1) AS count_not_monday,
    MIN(week_start) AS min_week_start,
    MAX(week_start) AS max_week_start
FROM ops.v_payments_driver_matrix_cabinet
WHERE week_start IS NOT NULL;

-- 12. Verificación de columnas requeridas (debe retornar todas las columnas esperadas)
SELECT 
    '=== VERIFICACIÓN DE COLUMNAS ===' AS seccion,
    column_name,
    data_type,
    is_nullable
FROM information_schema.columns 
WHERE table_schema = 'ops' 
  AND table_name = 'v_payments_driver_matrix_cabinet'
ORDER BY ordinal_position;

-- 13. Verificación de flags de inconsistencia de milestones
SELECT 
    '=== VERIFICACIÓN: FLAGS DE INCONSISTENCIA ===' AS seccion,
    COUNT(*) AS total_drivers,
    COUNT(*) FILTER (WHERE m5_without_m1_flag = true) AS count_m5_sin_m1,
    COUNT(*) FILTER (WHERE m25_without_m5_flag = true) AS count_m25_sin_m5,
    COUNT(*) FILTER (WHERE milestone_inconsistency_notes IS NOT NULL) AS count_con_notas,
    COUNT(*) FILTER (WHERE m5_without_m1_flag = true AND m25_without_m5_flag = true) AS count_ambas_inconsistencias
FROM ops.v_payments_driver_matrix_cabinet;

-- 14. Sample de drivers con inconsistencias
SELECT 
    '=== SAMPLE: DRIVERS CON INCONSISTENCIAS ===' AS seccion,
    driver_id,
    driver_name,
    m5_without_m1_flag,
    m25_without_m5_flag,
    milestone_inconsistency_notes,
    m1_achieved_flag,
    m5_achieved_flag,
    m25_achieved_flag
FROM ops.v_payments_driver_matrix_cabinet
WHERE m5_without_m1_flag = true OR m25_without_m5_flag = true
ORDER BY milestone_inconsistency_notes, driver_name
LIMIT 20;

