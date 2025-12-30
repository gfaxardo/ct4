-- ============================================================================
-- Queries de Validación para Data Health
-- ============================================================================
-- Ejecutar estas queries para verificar que las vistas funcionan correctamente
-- ============================================================================

-- 1. Verificar freshness_status (debería mostrar 1 fila por fuente)
SELECT * FROM ops.v_data_freshness_status ORDER BY source_name;

-- 2. Verificar health_status (debería mostrar health_status calculado)
SELECT * FROM ops.v_data_health_status ORDER BY source_name;

-- 3. Verificar ingestion_daily (últimos 30 días)
SELECT * FROM ops.v_data_ingestion_daily 
  WHERE metric_date >= CURRENT_DATE - 30 
  ORDER BY source_name, metric_type, metric_date DESC;

-- 4. Resumen de salud por fuente (vista rápida)
SELECT 
    source_name,
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

-- 5. Verificar que hay datos recientes
SELECT 
    source_name,
    MAX(metric_date) AS last_date,
    SUM(CASE WHEN metric_type = 'business' THEN rows_count ELSE 0 END) AS total_business_rows,
    SUM(CASE WHEN metric_type = 'ingestion' THEN rows_count ELSE 0 END) AS total_ingestion_rows
FROM ops.v_data_ingestion_daily
WHERE metric_date >= CURRENT_DATE - 7
GROUP BY source_name
ORDER BY source_name;

