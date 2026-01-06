-- ============================================================================
-- Script: Comparar Rendimiento Vista Normal vs Materializada
-- ============================================================================
-- PROPÓSITO:
-- Comparar tiempos de ejecución entre la vista normal y la vista materializada
-- para demostrar la mejora de rendimiento.
-- ============================================================================
-- USO:
-- psql $DATABASE_URL -f backend/scripts/sql/compare_performance.sql
-- ============================================================================

\timing on

\echo '============================================================================'
\echo 'COMPARACIÓN DE RENDIMIENTO: Vista Normal vs Materializada'
\echo '============================================================================'
\echo ''

\echo '--- QUERY 1: Conteo total (sin filtros) ---'
\echo 'Vista Normal:'
SELECT COUNT(*) FROM ops.v_payments_driver_matrix_cabinet;
\echo ''
\echo 'Vista Materializada:'
SELECT COUNT(*) FROM ops.mv_payments_driver_matrix_cabinet;
\echo ''

\echo '--- QUERY 2: Filtro por origin_tag = cabinet (LIMIT 25) ---'
\echo 'Vista Normal:'
SELECT COUNT(*) FROM ops.v_payments_driver_matrix_cabinet WHERE origin_tag = 'cabinet' LIMIT 25;
\echo ''
\echo 'Vista Materializada:'
SELECT COUNT(*) FROM ops.mv_payments_driver_matrix_cabinet WHERE origin_tag = 'cabinet' LIMIT 25;
\echo ''

\echo '--- QUERY 3: Filtro por origin_tag + week_start (LIMIT 25) ---'
\echo 'Vista Normal:'
SELECT COUNT(*) FROM ops.v_payments_driver_matrix_cabinet 
WHERE origin_tag = 'cabinet' AND week_start >= '2025-12-01' LIMIT 25;
\echo ''
\echo 'Vista Materializada:'
SELECT COUNT(*) FROM ops.mv_payments_driver_matrix_cabinet 
WHERE origin_tag = 'cabinet' AND week_start >= '2025-12-01' LIMIT 25;
\echo ''

\echo '--- QUERY 4: SELECT con ORDER BY (LIMIT 25) ---'
\echo 'Vista Normal:'
SELECT driver_id, driver_name, origin_tag, week_start 
FROM ops.v_payments_driver_matrix_cabinet 
WHERE origin_tag = 'cabinet' 
ORDER BY week_start DESC NULLS LAST, driver_name ASC NULLS LAST 
LIMIT 25;
\echo ''
\echo 'Vista Materializada:'
SELECT driver_id, driver_name, origin_tag, week_start 
FROM ops.mv_payments_driver_matrix_cabinet 
WHERE origin_tag = 'cabinet' 
ORDER BY week_start DESC NULLS LAST, driver_name ASC NULLS LAST 
LIMIT 25;
\echo ''

\echo '============================================================================'
\echo 'COMPARACIÓN COMPLETADA'
\echo '============================================================================'

\timing off

