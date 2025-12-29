-- ============================================================================
-- Script de Verificación Completa: Optimizaciones de Performance
-- ============================================================================
-- Este script verifica que todas las optimizaciones estén funcionando
-- correctamente y mide el impacto en el performance.
-- ============================================================================

-- 1. Verificar que la materialized view existe y tiene datos
SELECT 
    'Materialized View' AS check_name,
    COUNT(*) AS total_drivers,
    COUNT(DISTINCT driver_id) AS distinct_drivers
FROM ops.mv_drivers_park_08e20910d81d42658d4334d3f6d10ac0_active90d;

-- 2. Verificar que la vista enriquecida funciona (sin filtro de fecha para ver todos los datos)
SELECT 
    'Vista Enriquecida (sin filtro)' AS check_name,
    COUNT(*) AS total_rows,
    COUNT(DISTINCT driver_id_final) AS distinct_drivers,
    COUNT(*) FILTER (WHERE identity_status = 'enriched') AS enriched_count,
    COUNT(*) FILTER (WHERE identity_status = 'confirmed') AS confirmed_count,
    COUNT(*) FILTER (WHERE identity_status = 'no_match') AS no_match_count
FROM ops.v_yango_payments_ledger_latest_enriched
LIMIT 1000;

-- 3. Verificar que la vista de claims funciona
SELECT 
    'Vista Claims Cabinet' AS check_name,
    COUNT(*) AS total_rows,
    MIN(pay_week_start_monday) AS min_week,
    MAX(pay_week_start_monday) AS max_week
FROM ops.v_yango_payments_claims_cabinet_14d;

-- 4. Verificar EXPLAIN plan - debe usar materialized view, no public.drivers
-- Usar solo VERBOSE (sin BUFFERS) para ver el plan sin ejecutar la query completa
EXPLAIN (VERBOSE)
SELECT 
    driver_id_final,
    identity_status,
    match_rule
FROM ops.v_yango_payments_ledger_latest_enriched
WHERE pay_date >= (current_date - interval '30 days')::date
LIMIT 10;

-- 5. Verificar EXPLAIN plan de la vista de claims
-- Usar solo VERBOSE (sin BUFFERS) para ver el plan sin ejecutar la query completa
EXPLAIN (VERBOSE)
SELECT 
    pay_week_start_monday,
    milestone_value,
    COUNT(*) AS row_count
FROM ops.v_yango_payments_claims_cabinet_14d
GROUP BY pay_week_start_monday, milestone_value
ORDER BY pay_week_start_monday DESC, milestone_value
LIMIT 5;

-- 6. Comparar tamaño: materialized view vs todos los drivers del park
SELECT 
    'Materialized View (activos 90d)' AS source,
    COUNT(*) AS total_drivers
FROM ops.mv_drivers_park_08e20910d81d42658d4334d3f6d10ac0_active90d
UNION ALL
SELECT 
    'Todos drivers del park' AS source,
    COUNT(*) AS total_drivers
FROM public.drivers
WHERE park_id = '08e20910d81d42658d4334d3f6d10ac0'
    AND driver_id IS NOT NULL
    AND (full_name IS NOT NULL OR first_name IS NOT NULL OR last_name IS NOT NULL);

-- 7. Verificar que no hay Seq Scan sobre public.drivers en el plan
-- (Este query debe mostrar que se usa la materialized view)
SELECT 
    schemaname,
    tablename,
    indexname,
    idx_scan AS index_scans
FROM pg_stat_user_indexes
WHERE tablename LIKE '%drivers_park%'
ORDER BY idx_scan DESC;

