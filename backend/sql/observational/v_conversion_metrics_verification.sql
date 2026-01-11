-- Queries de Verificación para observational.v_conversion_metrics
-- Ejecutar estas queries después de crear la vista para validar los resultados

-- 1. Total filas por origin_tag
SELECT 
    origin_tag, 
    COUNT(*) as total
FROM observational.v_conversion_metrics
GROUP BY origin_tag
ORDER BY origin_tag;

-- 2. % con driver_id no null
SELECT 
    origin_tag,
    COUNT(*) as total,
    COUNT(driver_id) as with_driver_id,
    ROUND(100.0 * COUNT(driver_id) / NULLIF(COUNT(*), 0), 2) as pct_with_driver
FROM observational.v_conversion_metrics
GROUP BY origin_tag
ORDER BY origin_tag;

-- 3. Distribución de time_to_1_days (min/avg/max) por origin_tag
SELECT 
    origin_tag,
    MIN(time_to_1_days) as min_days,
    ROUND(AVG(time_to_1_days), 2) as avg_days,
    MAX(time_to_1_days) as max_days,
    COUNT(*) FILTER (WHERE time_to_1_days IS NOT NULL) as has_time_to_1,
    COUNT(*) FILTER (WHERE time_to_1_days IS NULL) as no_time_to_1,
    COUNT(*) as total
FROM observational.v_conversion_metrics
GROUP BY origin_tag
ORDER BY origin_tag;







