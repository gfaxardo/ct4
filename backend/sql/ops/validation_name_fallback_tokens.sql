-- ============================================================================
-- VALIDACIÓN: Fallback por Nombre con Tokens Ordenados
-- Objetivo: Validar que el matching con tokens ordenados funciona correctamente
-- y permite matches cuando el orden de nombres varía
-- ============================================================================

-- 1) PRUEBA DE FUNCIONES DE NORMALIZACIÓN
-- Verificar que las funciones funcionan correctamente
SELECT 
    'Prueba funciones' AS test,
    ops.normalize_name_basic('Luis Fabio Quispe Anyosa') AS basic_1,
    ops.normalize_name_basic('Quispe Anyosa Luis Fabio') AS basic_2,
    ops.normalize_name_tokens_sorted('Luis Fabio Quispe Anyosa') AS sorted_1,
    ops.normalize_name_tokens_sorted('Quispe Anyosa Luis Fabio') AS sorted_2,
    -- Debe mostrar: basic_1 != basic_2, pero sorted_1 = sorted_2
    CASE 
        WHEN ops.normalize_name_basic('Luis Fabio Quispe Anyosa') != ops.normalize_name_basic('Quispe Anyosa Luis Fabio') 
        THEN 'OK: basic diferente' 
        ELSE 'ERROR: basic igual' 
    END AS basic_check,
    CASE 
        WHEN ops.normalize_name_tokens_sorted('Luis Fabio Quispe Anyosa') = ops.normalize_name_tokens_sorted('Quispe Anyosa Luis Fabio')
        THEN 'OK: sorted igual' 
        ELSE 'ERROR: sorted diferente' 
    END AS sorted_check;

-- 2) DISTRIBUCIÓN DE match_rule EN RAW CURRENT
-- Ver cuántos usan upstream vs fallback
SELECT 
    match_rule,
    match_confidence,
    COUNT(*) AS count_rows,
    COUNT(*) FILTER (WHERE driver_id IS NOT NULL) AS count_with_driver_id,
    COUNT(*) FILTER (WHERE person_key IS NOT NULL) AS count_with_person_key
FROM ops.v_yango_payments_raw_current_aliases
GROUP BY match_rule, match_confidence
ORDER BY match_rule, match_confidence;

-- 3) CASOS DONDE TOKENS_SORTED AYUDA (full_norm no matchea, tokens_sorted sí)
-- Ejemplos de casos donde el orden de nombres varía
SELECT 
    r.raw_driver_name AS payment_name,
    r.driver_name_normalized AS payment_normalized,
    r.match_rule AS payment_match_rule,
    d.full_name_raw AS driver_name,
    d.full_name_normalized_basic AS driver_normalized_basic,
    d.full_name_normalized_tokens_sorted AS driver_normalized_tokens,
    ops.normalize_name_basic(r.raw_driver_name) AS payment_norm_basic,
    ops.normalize_name_tokens_sorted(r.raw_driver_name) AS payment_norm_tokens
FROM ops.v_yango_payments_raw_current_aliases r
INNER JOIN ops.v_driver_name_index_extended d
    ON ops.normalize_name_tokens_sorted(r.raw_driver_name) = d.full_name_normalized_tokens_sorted
    AND ops.normalize_name_tokens_sorted(r.raw_driver_name) IS NOT NULL
WHERE r.match_rule IN ('name_tokens_unique')
    AND (
        ops.normalize_name_basic(r.raw_driver_name) != d.full_name_normalized_basic
        OR ops.normalize_name_basic(r.raw_driver_name) IS NULL
    )
LIMIT 20;

-- 4) DISTRIBUCIÓN DE match_rule EN LEDGER ENRIQUECIDO
SELECT 
    match_rule,
    match_confidence,
    identity_source,
    COUNT(*) AS count_rows,
    COUNT(*) FILTER (WHERE driver_id_final IS NOT NULL) AS count_with_driver_id,
    COUNT(*) FILTER (WHERE person_key_final IS NOT NULL) AS count_with_person_key,
    COUNT(*) FILTER (WHERE is_paid = true) AS count_paid
FROM ops.v_yango_payments_ledger_latest_enriched
GROUP BY match_rule, match_confidence, identity_source
ORDER BY match_rule, match_confidence, identity_source;

-- 5) CASOS AMBIGUOS (múltiples matches)
-- Identificar casos donde hay múltiples posibles matches
SELECT 
    match_rule,
    match_confidence,
    COUNT(*) AS count_ambiguous,
    COUNT(DISTINCT driver_name_normalized) AS count_distinct_names
FROM ops.v_yango_payments_ledger_latest_enriched
WHERE match_rule = 'ambiguous'
GROUP BY match_rule, match_confidence;

-- 6) COMPARACIÓN: UPSTREAM vs FALLBACK
SELECT 
    'Upstream (original)' AS source_type,
    COUNT(*) AS count_rows,
    COUNT(*) FILTER (WHERE is_paid = true) AS count_paid
FROM ops.v_yango_payments_ledger_latest_enriched
WHERE identity_source = 'original'

UNION ALL

SELECT 
    'Fallback (enriched_by_name)' AS source_type,
    COUNT(*) AS count_rows,
    COUNT(*) FILTER (WHERE is_paid = true) AS count_paid
FROM ops.v_yango_payments_ledger_latest_enriched
WHERE identity_source = 'enriched_by_name'

UNION ALL

SELECT 
    'Sin identidad (none)' AS source_type,
    COUNT(*) AS count_rows,
    COUNT(*) FILTER (WHERE is_paid = true) AS count_paid
FROM ops.v_yango_payments_ledger_latest_enriched
WHERE identity_source = 'none';

-- 7) TOP 20 CASOS ENRIQUECIDOS POR TOKENS (ejemplos)
-- Ver casos donde tokens_sorted permitió el match
SELECT 
    raw_driver_name,
    driver_name_normalized,
    match_rule,
    match_confidence,
    identity_source,
    driver_id_original,
    driver_id_final,
    person_key_original,
    person_key_final,
    is_paid
FROM ops.v_yango_payments_ledger_latest_enriched
WHERE match_rule IN ('name_full_unique', 'name_tokens_unique')
    AND identity_source = 'enriched_by_name'
ORDER BY match_rule, pay_date DESC NULLS LAST
LIMIT 20;

-- 8) RESUMEN: DISTRIBUCIÓN POR CONFIDENCE Y SOURCE
SELECT 
    match_confidence,
    identity_source,
    COUNT(*) AS count_rows,
    COUNT(*) FILTER (WHERE driver_id_final IS NOT NULL OR person_key_final IS NOT NULL) AS count_with_identity,
    COUNT(*) FILTER (WHERE is_paid = true) AS count_paid
FROM ops.v_yango_payments_ledger_latest_enriched
GROUP BY match_confidence, identity_source
ORDER BY 
    CASE match_confidence 
        WHEN 'high' THEN 1
        WHEN 'medium' THEN 2
        WHEN 'low' THEN 3
        WHEN 'unknown' THEN 4
        ELSE 5
    END,
    identity_source;



