-- ============================================================================
-- INSTALACIÓN: Data Health - Observabilidad de Ingestas
-- ============================================================================
-- INSTRUCCIONES:
-- 1. Ejecuta TODO este archivo completo (copiar y pegar en tu cliente SQL)
-- 2. Si alguna tabla no existe y aparece error, comenta la CTE correspondiente
--    en v_data_health.sql y vuelve a ejecutar
-- ============================================================================

-- Este archivo debe ejecutarse DESPUÉS de v_data_health.sql
-- Solo contiene queries de validación

-- ============================================================================
-- PASO 1: Verificar que las vistas se crearon correctamente
-- ============================================================================
SELECT 
    schemaname, 
    viewname,
    CASE 
        WHEN viewname IN ('v_data_sources_catalog', 'v_data_freshness_status', 'v_data_ingestion_daily', 'v_data_health_status')
        THEN '✓ CREADA'
        ELSE 'EXTRA'
    END AS status
FROM pg_views
WHERE schemaname = 'ops'
    AND viewname LIKE 'v_data_%'
ORDER BY viewname;

-- ============================================================================
-- PASO 2: Validar datos (conteos)
-- ============================================================================
SELECT 'CATÁLOGO' AS vista, COUNT(*) AS filas FROM ops.v_data_sources_catalog
UNION ALL
SELECT 'FRESHNESS', COUNT(*) FROM ops.v_data_freshness_status
UNION ALL
SELECT 'INGESTION_DAILY', COUNT(*) FROM ops.v_data_ingestion_daily
UNION ALL
SELECT 'HEALTH_STATUS', COUNT(*) FROM ops.v_data_health_status;

-- ============================================================================
-- PASO 3: Verificar catálogo de fuentes
-- ============================================================================
SELECT * FROM ops.v_data_sources_catalog ORDER BY source_name;

-- ============================================================================
-- PASO 4: Verificar health status
-- ============================================================================
SELECT 
    source_name,
    source_type,
    health_status,
    max_business_date,
    business_days_lag,
    ingestion_lag_interval,
    rows_ingested_today
FROM ops.v_data_health_status
ORDER BY
    CASE health_status
        WHEN 'RED_NO_INGESTION_2D' THEN 1
        WHEN 'RED_INGESTION_STALE' THEN 2
        WHEN 'YELLOW_BUSINESS_LAG' THEN 3
        WHEN 'GREEN_OK' THEN 4
    END,
    source_name;

-- ============================================================================
-- PASO 5: Verificar ingesta diaria (últimos 7 días)
-- ============================================================================
SELECT
    source_name,
    MAX(metric_date) AS last_date,
    SUM(CASE WHEN metric_type = 'business' THEN rows_count ELSE 0 END) AS total_business_rows,
    SUM(CASE WHEN metric_type = 'ingestion' THEN rows_count ELSE 0 END) AS total_ingestion_rows
FROM ops.v_data_ingestion_daily
WHERE metric_date >= CURRENT_DATE - 7
GROUP BY source_name
ORDER BY source_name;



