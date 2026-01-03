-- ============================================================================
-- Script de Verificación: ops.v_payments_driver_matrix_cabinet
-- ============================================================================
-- Verifica existencia, conteos y distribuciones de la vista driver matrix.
-- Solo SELECT (no modifica datos).
-- ============================================================================

-- 1. Verificar que existe la vista
SELECT 
    '=== VERIFICACIÓN: EXISTENCIA DE VISTA ===' AS seccion,
    CASE 
        WHEN EXISTS (
            SELECT 1 FROM information_schema.views 
            WHERE table_schema = 'ops' 
            AND table_name = 'v_payments_driver_matrix_cabinet'
        ) THEN '✅ Vista existe'
        ELSE '❌ Vista NO existe'
    END AS estado;

-- 2. SELECT COUNT(*) total
SELECT 
    '=== CONTEOS TOTALES ===' AS seccion,
    COUNT(*) AS total_drivers
FROM ops.v_payments_driver_matrix_cabinet;

-- 3. Resumen de drivers y milestones
SELECT 
    '=== RESUMEN: DRIVERS Y MILESTONES ===' AS seccion,
    COUNT(*) AS total_drivers,
    COUNT(*) FILTER (WHERE m1_achieved_flag = true) AS drivers_with_m1,
    COUNT(*) FILTER (WHERE m5_achieved_flag = true) AS drivers_with_m5,
    COUNT(*) FILTER (WHERE m25_achieved_flag = true) AS drivers_with_m25,
    COUNT(*) FILTER (WHERE m1_achieved_flag = true AND m5_achieved_flag = true) AS drivers_with_m1_and_m5,
    COUNT(*) FILTER (WHERE m1_achieved_flag = true AND m5_achieved_flag = true AND m25_achieved_flag = true) AS drivers_with_all_milestones,
    COUNT(*) FILTER (WHERE origin_tag IS NOT NULL) AS drivers_with_origin_tag,
    COUNT(*) FILTER (WHERE connected_flag = true) AS drivers_connected
FROM ops.v_payments_driver_matrix_cabinet;

-- 4. Distribución por week_start (últimas 8 semanas)
SELECT 
    '=== DISTRIBUCIÓN POR WEEK_START (ÚLTIMAS 8 SEMANAS) ===' AS seccion,
    week_start,
    COUNT(*) AS total_drivers,
    COUNT(*) FILTER (WHERE m1_achieved_flag = true) AS drivers_with_m1,
    COUNT(*) FILTER (WHERE m5_achieved_flag = true) AS drivers_with_m5,
    COUNT(*) FILTER (WHERE m25_achieved_flag = true) AS drivers_with_m25
FROM ops.v_payments_driver_matrix_cabinet
WHERE week_start >= (date_trunc('week', current_date)::date - interval '8 weeks')::date
    AND week_start IS NOT NULL
GROUP BY week_start
ORDER BY week_start DESC;

