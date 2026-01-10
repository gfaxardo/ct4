-- ============================================================================
-- VERIFICACIÓN: Vistas de Scout Attribution
-- ============================================================================
-- Objetivo: Validar que las vistas funcionan correctamente
-- Ejecución: Idempotente (solo consultas SELECT)
-- ============================================================================

-- ============================================================================
-- VALIDACIÓN 1: ops.v_scout_attribution (1 fila por person_key)
-- ============================================================================

DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM information_schema.views WHERE table_schema = 'ops' AND table_name = 'v_scout_attribution') THEN
        RAISE NOTICE 'VALIDACIÓN: v_scout_attribution existe, verificando...';
    ELSE
        RAISE NOTICE 'WARN: ops.v_scout_attribution no existe todavía';
    END IF;
END $$;

-- Si la vista existe, ejecutar validación
SELECT 
    'VALIDACIÓN: v_scout_attribution sin duplicados' AS check_type,
    COUNT(*) AS total_rows,
    COUNT(DISTINCT person_key) AS distinct_person_keys,
    CASE 
        WHEN COUNT(*) = COUNT(DISTINCT person_key) THEN 'OK: Sin duplicados'
        ELSE 'ERROR: Hay duplicados'
    END AS status
FROM ops.v_scout_attribution
WHERE EXISTS (SELECT 1 FROM information_schema.views WHERE table_schema = 'ops' AND table_name = 'v_scout_attribution');

-- ============================================================================
-- VALIDACIÓN 2: Conflictos (listar top 50)
-- ============================================================================

DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM information_schema.views WHERE table_schema = 'ops' AND table_name = 'v_scout_attribution_conflicts') THEN
        RAISE NOTICE 'VALIDACIÓN: v_scout_attribution_conflicts existe, verificando...';
    ELSE
        RAISE NOTICE 'WARN: ops.v_scout_attribution_conflicts no existe todavía';
    END IF;
END $$;

-- Si la vista existe, ejecutar validación
SELECT 
    'VALIDACIÓN: Conflictos detectados' AS check_type,
    COUNT(*) AS total_conflicts,
    (SELECT COUNT(DISTINCT unnest_scout_id) FROM ops.v_scout_attribution_conflicts, unnest(scout_ids) AS unnest_scout_id) AS distinct_scouts_in_conflicts
FROM ops.v_scout_attribution_conflicts
WHERE EXISTS (SELECT 1 FROM information_schema.views WHERE table_schema = 'ops' AND table_name = 'v_scout_attribution_conflicts');

-- Mostrar top 50 conflictos (solo si la vista existe)
SELECT 
    person_key,
    distinct_scout_count,
    scout_ids,
    source_tables,
    first_attribution_date,
    last_attribution_date,
    total_records
FROM ops.v_scout_attribution_conflicts
WHERE EXISTS (SELECT 1 FROM information_schema.views WHERE table_schema = 'ops' AND table_name = 'v_scout_attribution_conflicts')
ORDER BY distinct_scout_count DESC, total_records DESC
LIMIT 50;

-- ============================================================================
-- VALIDACIÓN 3: Cobertura antes/después
-- ============================================================================

-- 3a: % scouting_daily con identity_links > 0
SELECT 
    'COBERTURA: scouting_daily con identity_links' AS metric,
    total_with_scout,
    with_identity_links,
    CASE 
        WHEN total_with_scout > 0 THEN 
            ROUND((with_identity_links::NUMERIC / total_with_scout * 100), 2)
        ELSE 0 
    END AS pct_coverage
FROM (
    SELECT 
        (SELECT COUNT(*) FROM public.module_ct_scouting_daily 
         WHERE EXISTS (SELECT 1 FROM information_schema.tables 
                       WHERE table_schema = 'public' AND table_name = 'module_ct_scouting_daily')
           AND scout_id IS NOT NULL) AS total_with_scout,
        (SELECT COUNT(DISTINCT sd.id)
         FROM public.module_ct_scouting_daily sd
         WHERE EXISTS (SELECT 1 FROM information_schema.tables 
                       WHERE table_schema = 'public' AND table_name = 'module_ct_scouting_daily')
           AND sd.scout_id IS NOT NULL
           AND EXISTS (
               SELECT 1 FROM canon.identity_links il
               WHERE il.source_table = 'module_ct_scouting_daily'
                   AND il.source_pk = sd.id::TEXT
           )) AS with_identity_links
) coverage;

-- 3b: % scouting_daily que llega a lead_ledger con scout satisfactorio > 0
SELECT 
    'COBERTURA: scouting_daily -> lead_ledger scout satisfactorio' AS metric,
    total_with_scout,
    with_ledger_scout,
    CASE 
        WHEN total_with_scout > 0 THEN 
            ROUND((with_ledger_scout::NUMERIC / total_with_scout * 100), 2)
        ELSE 0 
    END AS pct_coverage,
    CASE 
        WHEN total_with_scout > 0 AND with_ledger_scout = 0 THEN 'WARN: Cobertura 0%'
        WHEN total_with_scout > 0 AND with_ledger_scout > 0 THEN 'OK: Cobertura > 0%'
        ELSE 'INFO: Sin datos'
    END AS status
FROM (
    SELECT 
        (SELECT COUNT(*) FROM public.module_ct_scouting_daily 
         WHERE EXISTS (SELECT 1 FROM information_schema.tables 
                       WHERE table_schema = 'public' AND table_name = 'module_ct_scouting_daily')
           AND scout_id IS NOT NULL) AS total_with_scout,
        (SELECT COUNT(DISTINCT sd.id)
         FROM public.module_ct_scouting_daily sd
         WHERE EXISTS (SELECT 1 FROM information_schema.tables 
                       WHERE table_schema = 'public' AND table_name = 'module_ct_scouting_daily')
           AND sd.scout_id IS NOT NULL
           AND EXISTS (
               SELECT 1 FROM canon.identity_links il
               JOIN observational.lead_ledger ll ON ll.person_key = il.person_key
               WHERE il.source_table = 'module_ct_scouting_daily'
                   AND il.source_pk = sd.id::TEXT
                   AND ll.attributed_scout_id IS NOT NULL
           )) AS with_ledger_scout
) coverage;

-- 3c: Personas con scout satisfactorio (baseline vs después)
SELECT 
    'COBERTURA: Personas con scout satisfactorio' AS metric,
    total_persons,
    persons_with_scout,
    CASE 
        WHEN total_persons > 0 THEN 
            ROUND((persons_with_scout::NUMERIC / total_persons * 100), 2)
        ELSE 0 
    END AS pct_coverage
FROM (
    SELECT 
        (SELECT COUNT(DISTINCT person_key) FROM canon.identity_registry) AS total_persons,
        (SELECT COUNT(DISTINCT person_key) FROM observational.lead_ledger 
         WHERE attributed_scout_id IS NOT NULL) AS persons_with_scout
) coverage;

-- ============================================================================
-- VALIDACIÓN 4: ops.v_yango_collection_with_scout (si existe)
-- ============================================================================

SELECT 
    'VALIDACIÓN: v_yango_collection_with_scout' AS check_type,
    COUNT(*) AS total_claims,
    COUNT(*) FILTER (WHERE is_scout_resolved = true) AS claims_with_scout,
    CASE 
        WHEN COUNT(*) > 0 THEN 
            ROUND((COUNT(*) FILTER (WHERE is_scout_resolved = true)::NUMERIC / COUNT(*) * 100), 2)
        ELSE 0 
    END AS pct_with_scout
FROM ops.v_yango_collection_with_scout
WHERE EXISTS (
    SELECT 1 FROM information_schema.views 
    WHERE table_schema = 'ops' AND table_name = 'v_yango_collection_with_scout'
);

-- ============================================================================
-- RESUMEN FINAL DE VERIFICACIÓN
-- ============================================================================

SELECT 
    '=== RESUMEN VERIFICACIÓN SCOUT ATTRIBUTION ===' AS section;

SELECT 
    'v_scout_attribution sin duplicados' AS check_name,
    CASE 
        WHEN EXISTS (SELECT 1 FROM information_schema.views WHERE table_schema = 'ops' AND table_name = 'v_scout_attribution')
            AND (SELECT COUNT(*) FROM ops.v_scout_attribution) = 
                (SELECT COUNT(DISTINCT person_key) FROM ops.v_scout_attribution)
        THEN 'PASS'
        WHEN EXISTS (SELECT 1 FROM information_schema.views WHERE table_schema = 'ops' AND table_name = 'v_scout_attribution')
        THEN 'FAIL'
        ELSE 'SKIP: Vista no existe'
    END AS status;

SELECT 
    'Conflictos detectados' AS check_name,
    CASE 
        WHEN EXISTS (SELECT 1 FROM information_schema.views WHERE table_schema = 'ops' AND table_name = 'v_scout_attribution_conflicts')
        THEN (SELECT COUNT(*)::TEXT FROM ops.v_scout_attribution_conflicts)
        ELSE 'N/A'
    END AS conflict_count,
    CASE 
        WHEN EXISTS (SELECT 1 FROM information_schema.views WHERE table_schema = 'ops' AND table_name = 'v_scout_attribution_conflicts')
            AND (SELECT COUNT(*) FROM ops.v_scout_attribution_conflicts) = 0 
        THEN 'PASS'
        WHEN EXISTS (SELECT 1 FROM information_schema.views WHERE table_schema = 'ops' AND table_name = 'v_scout_attribution_conflicts')
        THEN 'WARN: Hay conflictos (revisar manualmente)'
        ELSE 'SKIP: Vista no existe'
    END AS status;

