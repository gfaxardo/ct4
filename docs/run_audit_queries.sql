-- ============================================
-- QUERIES DE SANITY CHECK PARA AUDITORÍA DE RUNS
-- ============================================
-- Estas queries permiten validar que el sistema "matchea lo correcto"
-- y que la trazabilidad por corrida funciona correctamente.
--
-- Uso: Ejecutar estas queries después de cada corrida para validar:
-- 1. Que los matches tienen evidencia correcta
-- 2. Que los unmatched tienen reason_code apropiados
-- 3. Que los missing_keys se reportan correctamente
-- 4. Que los MULTIPLE_CANDIDATES tienen gap y candidatos

-- ============================================
-- 1) 5 EJEMPLOS DE MATCHED DEL ÚLTIMO RUN
-- ============================================
-- Muestra: source_table, source_pk, match_rule, confidence, evidence
-- Útil para: Validar que las reglas R1-R4 están funcionando correctamente
SELECT 
    source_table, 
    source_pk, 
    match_rule, 
    confidence_level, 
    evidence,
    linked_at
FROM canon.identity_links
WHERE run_id = (
    SELECT MAX(id) 
    FROM ops.ingestion_runs 
    WHERE status='COMPLETED' 
      AND job_type='identity_run'
)
ORDER BY linked_at DESC
LIMIT 5;

-- ============================================
-- 2) TOP REASON_CODE DEL ÚLTIMO RUN
-- ============================================
-- Muestra: reason_code y conteo
-- Útil para: Ver distribución de razones de unmatched
SELECT 
    reason_code, 
    COUNT(*) as count
FROM canon.identity_unmatched
WHERE run_id = (
    SELECT MAX(id) 
    FROM ops.ingestion_runs 
    WHERE status='COMPLETED' 
      AND job_type='identity_run'
)
GROUP BY 1 
ORDER BY 2 DESC;

-- ============================================
-- 3) TOP MISSING_KEYS
-- ============================================
-- Muestra: keys faltantes más comunes y su frecuencia
-- Útil para: Identificar qué campos faltan más frecuentemente en los datos
SELECT 
    jsonb_array_elements_text(details->'missing_keys') AS missing_key, 
    COUNT(*) as count
FROM canon.identity_unmatched
WHERE run_id = (
    SELECT MAX(id) 
    FROM ops.ingestion_runs 
    WHERE status='COMPLETED' 
      AND job_type='identity_run'
)
  AND reason_code='MISSING_KEYS'
GROUP BY 1 
ORDER BY 2 DESC 
LIMIT 15;

-- ============================================
-- 4) EJEMPLOS DE MULTIPLE_CANDIDATES
-- ============================================
-- Muestra: source_table, source_pk, details, candidates_preview, gap
-- Útil para: Analizar casos ambiguos y el gap entre candidatos
SELECT 
    source_table, 
    source_pk, 
    details, 
    candidates_preview,
    candidates_preview->>'gap' as gap
FROM canon.identity_unmatched
WHERE run_id = (
    SELECT MAX(id) 
    FROM ops.ingestion_runs 
    WHERE status='COMPLETED' 
      AND job_type='identity_run'
)
  AND reason_code='MULTIPLE_CANDIDATES'
ORDER BY created_at DESC 
LIMIT 5;

-- ============================================
-- 5) DISTRIBUCIÓN DE CONFIDENCE_LEVEL POR RUN
-- ============================================
-- Muestra: confidence_level y conteo por run
-- Útil para: Validar que MEDIUM confidence se está generando (R3)
SELECT 
    confidence_level,
    COUNT(*) as count
FROM canon.identity_links
WHERE run_id = (
    SELECT MAX(id) 
    FROM ops.ingestion_runs 
    WHERE status='COMPLETED' 
      AND job_type='identity_run'
)
GROUP BY 1
ORDER BY 2 DESC;

-- ============================================
-- 6) MATCHED POR REGLA (R1, R2, R3, R4)
-- ============================================
-- Muestra: match_rule y conteo
-- Útil para: Ver qué reglas están funcionando más
SELECT 
    match_rule,
    COUNT(*) as count
FROM canon.identity_links
WHERE run_id = (
    SELECT MAX(id) 
    FROM ops.ingestion_runs 
    WHERE status='COMPLETED' 
      AND job_type='identity_run'
)
GROUP BY 1
ORDER BY 2 DESC;

-- ============================================
-- 7) RESUMEN DE RUN ESPECÍFICO
-- ============================================
-- Muestra: estadísticas agregadas de un run específico
-- Útil para: Reporte completo de una corrida
-- NOTA: Reemplazar :run_id con el ID del run a analizar
SELECT 
    'Matched' as tipo,
    COUNT(*) as total
FROM canon.identity_links
WHERE run_id = :run_id
UNION ALL
SELECT 
    'Unmatched' as tipo,
    COUNT(*) as total
FROM canon.identity_unmatched
WHERE run_id = :run_id;

-- ============================================
-- 8) VALIDACIÓN: LINKS SIN RUN_ID
-- ============================================
-- Muestra: links que no tienen run_id asignado (debería ser 0)
-- Útil para: Detectar problemas de trazabilidad
SELECT 
    COUNT(*) as links_sin_run_id
FROM canon.identity_links
WHERE run_id IS NULL;

-- ============================================
-- 9) VALIDACIÓN: UNMATCHED SIN RUN_ID
-- ============================================
-- Muestra: unmatched que no tienen run_id asignado (debería ser 0)
-- Útil para: Detectar problemas de trazabilidad
SELECT 
    COUNT(*) as unmatched_sin_run_id
FROM canon.identity_unmatched
WHERE run_id IS NULL;

-- ============================================
-- 10) COMPARACIÓN ENTRE RUNS
-- ============================================
-- Muestra: comparación de matched/unmatched entre últimos 2 runs
-- Útil para: Ver tendencias entre corridas
SELECT 
    r.id as run_id,
    r.started_at,
    COUNT(DISTINCT l.id) as matched_count,
    COUNT(DISTINCT u.id) as unmatched_count,
    CASE 
        WHEN COUNT(DISTINCT l.id) + COUNT(DISTINCT u.id) > 0 
        THEN ROUND(100.0 * COUNT(DISTINCT l.id) / (COUNT(DISTINCT l.id) + COUNT(DISTINCT u.id)), 2)
        ELSE 0 
    END as match_rate_pct
FROM ops.ingestion_runs r
LEFT JOIN canon.identity_links l ON l.run_id = r.id
LEFT JOIN canon.identity_unmatched u ON u.run_id = r.id
WHERE r.status = 'COMPLETED'
  AND r.job_type = 'identity_run'
GROUP BY r.id, r.started_at
ORDER BY r.started_at DESC
LIMIT 5;



























