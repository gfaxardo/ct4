-- ============================================================================
-- Detección de Duplicados en ops.mv_yango_cabinet_claims_for_collection
-- ============================================================================
-- PROPÓSITO:
-- Verificar si la MV tiene duplicados por su grano canónico para habilitar
-- REFRESH MATERIALIZED VIEW CONCURRENTLY.
--
-- GRANO CANÓNICO:
-- (driver_id, milestone_value)
--
-- JUSTIFICACIÓN:
-- Según docs/ops/yango_cabinet_grain_mapping.md:
-- - La MV está deduplicada: solo hay 1 fila por (driver_id, milestone_value)
-- - La deduplicación se realiza en ops.v_claims_payment_status_cabinet
--   usando DISTINCT ON (driver_id, milestone_value)
-- - La MV se basa en ops.mv_claims_payment_status_cabinet c (ya deduplicada)
-- - LEFT JOIN con public.drivers d es 1:1 por driver_id
-- - LEFT JOIN LATERAL con pagos trae 0 o 1 fila
-- - No hay GROUP BY ni agregación que pueda crear duplicados
--
-- REQUISITO PARA CONCURRENTLY:
-- REFRESH MATERIALIZED VIEW CONCURRENTLY requiere un índice único en el grano.
-- Si hay duplicados, no se puede crear el índice único y CONCURRENTLY fallará.
-- ============================================================================

-- ============================================================================
-- QUERY 1: Cuenta total de filas en la MV
-- ============================================================================
SELECT 
    'Total filas en MV' AS descripcion,
    COUNT(*) AS total_filas
FROM ops.mv_yango_cabinet_claims_for_collection;

-- ============================================================================
-- QUERY 2: Detecta duplicados por el grano canónico (driver_id, milestone_value)
-- ============================================================================
-- Retorna las combinaciones (driver_id, milestone_value) que aparecen más de 1 vez
-- Ordenado por cantidad de duplicados descendente
-- LIMIT 200 para no sobrecargar la salida
-- ============================================================================
SELECT 
    driver_id,
    milestone_value,
    COUNT(*) AS count_duplicates
FROM ops.mv_yango_cabinet_claims_for_collection
GROUP BY driver_id, milestone_value
HAVING COUNT(*) > 1
ORDER BY count_duplicates DESC
LIMIT 200;

-- ============================================================================
-- QUERY 3: Ejemplo de filas para investigar duplicados
-- ============================================================================
-- Devuelve todas las filas para las top 20 combinaciones duplicadas
-- Útil para investigar por qué hay duplicados
-- Ordenado por grano canónico y luego por otras columnas relevantes
-- LIMIT 500 para no sobrecargar la salida
-- ============================================================================
WITH duplicates AS (
    SELECT 
        driver_id,
        milestone_value,
        COUNT(*) AS count_duplicates
    FROM ops.mv_yango_cabinet_claims_for_collection
    GROUP BY driver_id, milestone_value
    HAVING COUNT(*) > 1
    ORDER BY count_duplicates DESC
    LIMIT 20
)
SELECT 
    m.*
FROM ops.mv_yango_cabinet_claims_for_collection m
JOIN duplicates d 
    ON m.driver_id = d.driver_id 
    AND m.milestone_value = d.milestone_value
ORDER BY 
    m.driver_id,
    m.milestone_value,
    m.lead_date DESC,
    m.payment_key,
    m.pay_date DESC
LIMIT 500;

-- ============================================================================
-- NOTAS:
-- ============================================================================
-- Si QUERY 2 retorna 0 filas: la MV no tiene duplicados y se puede crear
--   índice único para habilitar CONCURRENTLY.
--
-- Si QUERY 2 retorna >0 filas: hay duplicados que deben resolverse antes de
--   habilitar CONCURRENTLY. Usar QUERY 3 para investigar la causa.
--
-- Posibles causas de duplicados:
-- 1. La vista base ops.mv_claims_payment_status_cabinet tiene duplicados
-- 2. Los JOINs LATERAL están trayendo múltiples filas
-- 3. Cambios en la lógica de deduplicación
-- ============================================================================







