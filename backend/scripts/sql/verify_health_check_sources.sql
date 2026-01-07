-- Verificar que lead_events e ingestion_runs aparezcan en el health check

-- 1. Verificar en catálogo
SELECT 
    source_name,
    source_type,
    schema_name,
    object_name
FROM ops.v_data_sources_catalog
WHERE source_name IN ('lead_events', 'ingestion_runs')
ORDER BY source_name;

-- 2. Verificar en freshness status
SELECT 
    source_name,
    max_business_date,
    business_days_lag,
    max_ingestion_ts,
    ingestion_lag_interval
FROM ops.v_data_freshness_status
WHERE source_name IN ('lead_events', 'ingestion_runs')
ORDER BY source_name;

-- 3. Verificar en health status
SELECT 
    source_name,
    source_type,
    health_status,
    max_business_date,
    business_days_lag
FROM ops.v_data_health_status
WHERE source_name IN ('lead_events', 'ingestion_runs')
ORDER BY source_name;


