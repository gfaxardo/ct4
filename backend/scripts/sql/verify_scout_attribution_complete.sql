-- ============================================================================
-- VERIFICACIÓN COMPLETA: Scout Attribution Fix
-- ============================================================================
-- Este script verifica:
-- 1. Grano de vistas (1 fila por person_key/driver_id)
-- 2. Coverage (antes/después)
-- 3. Conflictos
-- 4. scouting_daily específicamente
-- ============================================================================

-- ============================================================================
-- 1. VERIFICAR GRANO DE VISTAS
-- ============================================================================

-- Verificar que v_scout_attribution tiene 1 fila por person_key
SELECT 
    'Verificación de grano: v_scout_attribution' AS check_name,
    COUNT(*) AS total_rows,
    COUNT(DISTINCT person_key) AS distinct_person_keys,
    COUNT(*) - COUNT(DISTINCT person_key) AS duplicates,
    CASE 
        WHEN COUNT(*) = COUNT(DISTINCT person_key) THEN 'OK'
        ELSE 'ERROR: Hay duplicados'
    END AS status
FROM ops.v_scout_attribution
WHERE person_key IS NOT NULL;

-- Verificar que v_scout_attribution tiene 1 fila por driver_id (si existe)
SELECT 
    'Verificación de grano: v_scout_attribution por driver_id' AS check_name,
    COUNT(*) AS total_rows,
    COUNT(DISTINCT driver_id) AS distinct_driver_ids,
    COUNT(*) - COUNT(DISTINCT driver_id) AS duplicates,
    CASE 
        WHEN COUNT(*) = COUNT(DISTINCT driver_id) OR COUNT(DISTINCT driver_id) = 0 THEN 'OK'
        ELSE 'WARNING: Hay duplicados por driver_id'
    END AS status
FROM ops.v_scout_attribution
WHERE driver_id IS NOT NULL;

-- ============================================================================
-- 2. COVERAGE: ANTES/DESPUÉS
-- ============================================================================

-- Coverage global: personas con scout satisfactorio (lead_ledger)
WITH stats AS (
    SELECT 
        (SELECT COUNT(DISTINCT person_key) FROM canon.identity_registry) AS total_persons,
        (SELECT COUNT(DISTINCT person_key) FROM observational.lead_ledger WHERE attributed_scout_id IS NOT NULL) AS persons_with_scout
)
SELECT 
    'Coverage global: Scout satisfactorio' AS metric,
    total_persons,
    persons_with_scout,
    total_persons - persons_with_scout AS persons_without_scout,
    ROUND((persons_with_scout::NUMERIC / NULLIF(total_persons, 0) * 100), 2) AS pct_with_scout,
    ROUND(((total_persons - persons_with_scout)::NUMERIC / NULLIF(total_persons, 0) * 100), 2) AS pct_without_scout
FROM stats;

-- Coverage por categoría (después del fix)
SELECT 
    'Coverage por categoría (después del fix)' AS metric,
    categoria,
    COUNT(*) AS count,
    ROUND(COUNT(*)::NUMERIC / (SELECT COUNT(*) FROM ops.v_persons_without_scout_categorized) * 100, 2) AS pct
FROM ops.v_persons_without_scout_categorized
GROUP BY categoria
ORDER BY count DESC;

-- ============================================================================
-- 3. SCOUTING_DAILY: COVERAGE ESPECÍFICO
-- ============================================================================

-- Coverage scouting_daily: identity_links
SELECT 
    'scouting_daily: Coverage identity_links' AS metric,
    (SELECT COUNT(*) FROM public.module_ct_scouting_daily WHERE scout_id IS NOT NULL) AS total_with_scout_id,
    (SELECT COUNT(DISTINCT sd.id) FROM public.module_ct_scouting_daily sd
     WHERE sd.scout_id IS NOT NULL
     AND EXISTS (
         SELECT 1 FROM canon.identity_links il
         WHERE il.source_table = 'module_ct_scouting_daily'
         AND il.source_pk = sd.id::TEXT
     )) AS with_identity_links,
    ROUND((
        SELECT COUNT(DISTINCT sd.id) FROM public.module_ct_scouting_daily sd
        WHERE sd.scout_id IS NOT NULL
        AND EXISTS (
            SELECT 1 FROM canon.identity_links il
            WHERE il.source_table = 'module_ct_scouting_daily'
            AND il.source_pk = sd.id::TEXT
        )
    )::NUMERIC / NULLIF((
        SELECT COUNT(*) FROM public.module_ct_scouting_daily WHERE scout_id IS NOT NULL
    ), 0) * 100, 2) AS pct_with_identity_links;

-- Coverage scouting_daily: lead_ledger
SELECT 
    'scouting_daily: Coverage lead_ledger' AS metric,
    (SELECT COUNT(*) FROM public.module_ct_scouting_daily WHERE scout_id IS NOT NULL) AS total_with_scout_id,
    (SELECT COUNT(DISTINCT sd.id) FROM public.module_ct_scouting_daily sd
     WHERE sd.scout_id IS NOT NULL
     AND EXISTS (
         SELECT 1 FROM canon.identity_links il
         JOIN observational.lead_ledger ll ON ll.person_key = il.person_key
         WHERE il.source_table = 'module_ct_scouting_daily'
         AND il.source_pk = sd.id::TEXT
         AND ll.attributed_scout_id IS NOT NULL
     )) AS with_lead_ledger_scout,
    ROUND((
        SELECT COUNT(DISTINCT sd.id) FROM public.module_ct_scouting_daily sd
        WHERE sd.scout_id IS NOT NULL
        AND EXISTS (
            SELECT 1 FROM canon.identity_links il
            JOIN observational.lead_ledger ll ON ll.person_key = il.person_key
            WHERE il.source_table = 'module_ct_scouting_daily'
            AND il.source_pk = sd.id::TEXT
            AND ll.attributed_scout_id IS NOT NULL
        )
    )::NUMERIC / NULLIF((
        SELECT COUNT(*) FROM public.module_ct_scouting_daily WHERE scout_id IS NOT NULL
    ), 0) * 100, 2) AS pct_with_lead_ledger_scout;

-- ============================================================================
-- 4. CONFLICTOS
-- ============================================================================

-- Contar conflictos
SELECT 
    'Conflictos: Total' AS metric,
    COUNT(*) AS total_conflicts,
    COUNT(DISTINCT person_key) AS distinct_person_keys,
    COUNT(DISTINCT driver_id) AS distinct_driver_ids
FROM ops.v_scout_attribution_conflicts;

-- Muestra de conflictos
SELECT 
    'Muestra de conflictos (Top 10)' AS tipo,
    driver_identifier,
    person_key,
    driver_id,
    distinct_scout_count,
    scout_ids,
    source_tables,
    first_attribution,
    last_attribution,
    total_attributions
FROM ops.v_scout_attribution_conflicts
ORDER BY distinct_scout_count DESC, total_attributions DESC
LIMIT 10;

-- ============================================================================
-- 5. DISTRIBUCIÓN POR SOURCE_TABLE
-- ============================================================================

SELECT 
    'Distribución por source_table' AS metric,
    source_table,
    COUNT(*) AS attribution_count,
    COUNT(DISTINCT COALESCE(driver_id, person_key::TEXT)) AS distinct_drivers,
    COUNT(DISTINCT scout_id) AS distinct_scouts
FROM ops.v_scout_attribution_raw
GROUP BY source_table
ORDER BY attribution_count DESC;

-- ============================================================================
-- 6. VALIDACIÓN: SCOUT COINCIDENTE EN SCOUTING_DAILY
-- ============================================================================

-- Verificar si scout_id de scouting_daily coincide con attributed_scout_id
SELECT 
    'scouting_daily: Scout coincidente' AS metric,
    COUNT(DISTINCT sd.id) AS total_scouting_daily,
    COUNT(DISTINCT sd.id) FILTER (
        WHERE EXISTS (
            SELECT 1 FROM canon.identity_links il
            JOIN observational.lead_ledger ll ON ll.person_key = il.person_key
            WHERE il.source_table = 'module_ct_scouting_daily'
            AND il.source_pk = sd.id::TEXT
            AND ll.attributed_scout_id = sd.scout_id
        )
    ) AS with_matching_scout,
    ROUND((
        COUNT(DISTINCT sd.id) FILTER (
            WHERE EXISTS (
                SELECT 1 FROM canon.identity_links il
                JOIN observational.lead_ledger ll ON ll.person_key = il.person_key
                WHERE il.source_table = 'module_ct_scouting_daily'
                AND il.source_pk = sd.id::TEXT
                AND ll.attributed_scout_id = sd.scout_id
            )
        )::NUMERIC / NULLIF(COUNT(DISTINCT sd.id), 0) * 100
    ), 2) AS pct_matching_scout
FROM public.module_ct_scouting_daily sd
WHERE sd.scout_id IS NOT NULL;

-- ============================================================================
-- 7. RESUMEN EJECUTIVO
-- ============================================================================

SELECT 
    'RESUMEN EJECUTIVO' AS summary,
    (SELECT COUNT(DISTINCT person_key) FROM canon.identity_registry) AS total_persons,
    (SELECT COUNT(DISTINCT person_key) FROM observational.lead_ledger WHERE attributed_scout_id IS NOT NULL) AS persons_with_scout_satisfactorio,
    (SELECT COUNT(*) FROM ops.v_scout_attribution_conflicts) AS total_conflicts,
    (SELECT COUNT(DISTINCT sd.id) FROM public.module_ct_scouting_daily sd
     WHERE sd.scout_id IS NOT NULL
     AND EXISTS (
         SELECT 1 FROM canon.identity_links il
         WHERE il.source_table = 'module_ct_scouting_daily'
         AND il.source_pk = sd.id::TEXT
     )) AS scouting_daily_with_identity_links,
    (SELECT COUNT(DISTINCT sd.id) FROM public.module_ct_scouting_daily sd
     WHERE sd.scout_id IS NOT NULL
     AND EXISTS (
         SELECT 1 FROM canon.identity_links il
         JOIN observational.lead_ledger ll ON ll.person_key = il.person_key
         WHERE il.source_table = 'module_ct_scouting_daily'
         AND il.source_pk = sd.id::TEXT
         AND ll.attributed_scout_id IS NOT NULL
     )) AS scouting_daily_with_lead_ledger_scout;

