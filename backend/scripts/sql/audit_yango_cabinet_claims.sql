-- ============================================================================
-- AUDIT SQL: Yango Cabinet Claims - Estado de DB Objects
-- ============================================================================
-- Propósito: Verificar existencia y estado de objetos DB necesarios para
--            el feature "Yango Cabinet Claims"
-- 
-- Uso:
--   psql "$DATABASE_URL" -f backend/scripts/sql/audit_yango_cabinet_claims.sql
--   # o desde Python:
--   python -c "from app.db import engine; from sqlalchemy import text; conn = engine.connect(); print(conn.execute(text(open('backend/scripts/sql/audit_yango_cabinet_claims.sql').read())).fetchall())"
-- ============================================================================

\echo '============================================================================'
\echo 'AUDIT: Yango Cabinet Claims - DB Objects'
\echo '============================================================================'
\echo ''

-- ============================================================================
-- 1. Verificar existencia de objetos principales
-- ============================================================================
\echo '1. VERIFICACIÓN DE EXISTENCIA DE OBJETOS'
\echo '----------------------------------------'

-- MV principal
SELECT 
    CASE 
        WHEN to_regclass('ops.mv_yango_cabinet_claims_for_collection') IS NOT NULL 
        THEN '✓ EXISTE'
        ELSE '✗ NO EXISTE'
    END AS mv_yango_cabinet_claims_for_collection,
    CASE 
        WHEN to_regclass('ops.v_yango_cabinet_claims_for_collection') IS NOT NULL 
        THEN '✓ EXISTE'
        ELSE '✗ NO EXISTE'
    END AS v_yango_cabinet_claims_for_collection,
    CASE 
        WHEN to_regclass('ops.v_yango_cabinet_claims_exigimos') IS NOT NULL 
        THEN '✓ EXISTE'
        ELSE '✗ NO EXISTE'
    END AS v_yango_cabinet_claims_exigimos,
    CASE 
        WHEN to_regclass('ops.v_yango_cabinet_claims_mv_health') IS NOT NULL 
        THEN '✓ EXISTE'
        ELSE '✗ NO EXISTE'
    END AS v_yango_cabinet_claims_mv_health;

\echo ''

-- ============================================================================
-- 2. Verificar índices únicos necesarios para REFRESH CONCURRENTLY
-- ============================================================================
\echo '2. VERIFICACIÓN DE ÍNDICES ÚNICOS (para REFRESH CONCURRENTLY)'
\echo '--------------------------------------------------------------'

SELECT 
    n.nspname AS schema_name,
    t.relname AS table_name,
    i.relname AS index_name,
    CASE 
        WHEN i.indisunique THEN '✓ ÚNICO'
        ELSE '✗ NO ÚNICO'
    END AS is_unique,
    pg_get_indexdef(i.oid) AS index_definition
FROM pg_index idx
JOIN pg_class i ON i.oid = idx.indexrelid
JOIN pg_class t ON t.oid = idx.indrelid
JOIN pg_namespace n ON n.oid = t.relnamespace
WHERE n.nspname = 'ops'
  AND t.relname = 'mv_yango_cabinet_claims_for_collection'
  AND i.indisunique = true
ORDER BY i.relname;

\echo ''

-- ============================================================================
-- 3. Verificar "staleness" de la MV (último refresh)
-- ============================================================================
\echo '3. ESTADO DE REFRESH (Staleness)'
\echo '--------------------------------'

SELECT 
    mv_name,
    MAX(CASE WHEN status IN ('OK', 'SUCCESS') THEN refresh_finished_at 
             WHEN status IN ('OK', 'SUCCESS') AND refresh_finished_at IS NULL THEN refreshed_at 
             ELSE NULL END) AS last_ok_refresh_finished_at,
    EXTRACT(EPOCH FROM (NOW() - MAX(CASE WHEN status IN ('OK', 'SUCCESS') THEN refresh_finished_at 
                                         WHEN status IN ('OK', 'SUCCESS') AND refresh_finished_at IS NULL THEN refreshed_at 
                                         ELSE NULL END))) / 3600.0 AS hours_since_ok_refresh,
    CASE 
        WHEN MAX(CASE WHEN status IN ('OK', 'SUCCESS') THEN refresh_finished_at 
                      WHEN status IN ('OK', 'SUCCESS') AND refresh_finished_at IS NULL THEN refreshed_at 
                      ELSE NULL END) IS NULL THEN 'NO_REFRESH'
        WHEN EXTRACT(EPOCH FROM (NOW() - MAX(CASE WHEN status IN ('OK', 'SUCCESS') THEN refresh_finished_at 
                                                   WHEN status IN ('OK', 'SUCCESS') AND refresh_finished_at IS NULL THEN refreshed_at 
                                                   ELSE NULL END))) / 3600.0 < 24 THEN 'OK'
        WHEN EXTRACT(EPOCH FROM (NOW() - MAX(CASE WHEN status IN ('OK', 'SUCCESS') THEN refresh_finished_at 
                                                   WHEN status IN ('OK', 'SUCCESS') AND refresh_finished_at IS NULL THEN refreshed_at 
                                                   ELSE NULL END))) / 3600.0 < 48 THEN 'WARN'
        ELSE 'CRIT'
    END AS status_bucket,
    (SELECT status 
     FROM ops.mv_refresh_log 
     WHERE schema_name = 'ops' 
       AND mv_name = 'mv_yango_cabinet_claims_for_collection'
     ORDER BY refresh_started_at DESC, refreshed_at DESC
     LIMIT 1) AS last_status,
    (SELECT rows_after_refresh 
     FROM ops.mv_refresh_log 
     WHERE schema_name = 'ops' 
       AND mv_name = 'mv_yango_cabinet_claims_for_collection'
       AND status IN ('OK', 'SUCCESS')
     ORDER BY refresh_finished_at DESC, refreshed_at DESC
     LIMIT 1) AS rows_after_refresh
FROM ops.mv_refresh_log
WHERE schema_name = 'ops' 
  AND mv_name = 'mv_yango_cabinet_claims_for_collection'
GROUP BY mv_name;

\echo ''

-- ============================================================================
-- 4. Conteo de filas (sanity check)
-- ============================================================================
\echo '4. CONTEOS DE FILAS (Sanity Check)'
\echo '-----------------------------------'

SELECT 
    (SELECT COUNT(*) FROM ops.mv_yango_cabinet_claims_for_collection) AS mv_total_rows,
    (SELECT COUNT(*) FROM ops.v_yango_cabinet_claims_exigimos) AS vista_exigimos_rows,
    (SELECT COUNT(*) FROM ops.mv_yango_cabinet_claims_for_collection WHERE yango_payment_status = 'UNPAID') AS mv_unpaid_rows,
    (SELECT COUNT(*) FROM ops.mv_yango_cabinet_claims_for_collection WHERE yango_payment_status = 'PAID') AS mv_paid_rows,
    (SELECT COUNT(*) FROM ops.mv_yango_cabinet_claims_for_collection WHERE yango_payment_status = 'PAID_MISAPPLIED') AS mv_paid_misapplied_rows;

\echo ''

-- ============================================================================
-- 5. Verificar dependencias (vistas base)
-- ============================================================================
\echo '5. VERIFICACIÓN DE DEPENDENCIAS (Vistas Base)'
\echo '----------------------------------------------'

SELECT 
    CASE 
        WHEN to_regclass('ops.v_claims_payment_status_cabinet') IS NOT NULL 
        THEN '✓ EXISTE'
        ELSE '✗ NO EXISTE (CRÍTICO)'
    END AS v_claims_payment_status_cabinet,
    CASE 
        WHEN to_regclass('ops.mv_claims_payment_status_cabinet') IS NOT NULL 
        THEN '✓ EXISTE'
        ELSE '⚠ NO EXISTE (puede usar vista normal)'
    END AS mv_claims_payment_status_cabinet,
    CASE 
        WHEN to_regclass('ops.v_yango_payments_ledger_latest_enriched') IS NOT NULL 
        THEN '✓ EXISTE'
        ELSE '✗ NO EXISTE (CRÍTICO)'
    END AS v_yango_payments_ledger_latest_enriched,
    CASE 
        WHEN to_regclass('ops.mv_yango_payments_ledger_latest_enriched') IS NOT NULL 
        THEN '✓ EXISTE'
        ELSE '⚠ NO EXISTE (puede usar vista normal)'
    END AS mv_yango_payments_ledger_latest_enriched,
    CASE 
        WHEN to_regclass('public.drivers') IS NOT NULL 
        THEN '✓ EXISTE'
        ELSE '✗ NO EXISTE (CRÍTICO)'
    END AS public_drivers;

\echo ''

-- ============================================================================
-- 6. Verificar tabla de refresh log
-- ============================================================================
\echo '6. VERIFICACIÓN DE TABLA DE REFRESH LOG'
\echo '----------------------------------------'

SELECT 
    CASE 
        WHEN to_regclass('ops.mv_refresh_log') IS NOT NULL 
        THEN '✓ EXISTE'
        ELSE '✗ NO EXISTE (CRÍTICO para health check)'
    END AS mv_refresh_log_exists,
    (SELECT COUNT(*) FROM ops.mv_refresh_log 
     WHERE schema_name = 'ops' 
       AND mv_name = 'mv_yango_cabinet_claims_for_collection') AS total_refresh_records;

\echo ''
\echo '============================================================================'
\echo 'FIN DEL AUDIT'
\echo '============================================================================'





