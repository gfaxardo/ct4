-- ============================================================================
-- VERIFICACIONES: Scout Attribution
-- ============================================================================
-- Propósito: Validaciones obligatorias que deben pasar
-- Ejecución: Script de verificación (no modifica datos)
-- ============================================================================

-- ============================================================================
-- 1. VERIFICAR: ops.v_scout_attribution = 1 fila por person_key (sin duplicados)
-- ============================================================================

SELECT 
    'VERIFICACION_1: Duplicados en v_scout_attribution' AS check_type,
    COUNT(*) AS total_rows,
    COUNT(DISTINCT person_key) AS distinct_person_keys,
    CASE 
        WHEN COUNT(*) = COUNT(DISTINCT person_key) THEN 'OK: Sin duplicados'
        ELSE 'ERROR: Hay duplicados'
    END AS status
FROM ops.v_scout_attribution
WHERE EXISTS (
    SELECT 1 FROM information_schema.views
    WHERE table_schema = 'ops' AND table_name = 'v_scout_attribution'
);

-- ============================================================================
-- 2. VERIFICAR: Coverage scouting_daily - identity_links > 0%
-- ============================================================================

SELECT 
    'VERIFICACION_2: Coverage scouting_daily identity_links' AS check_type,
    COUNT(*) FILTER (WHERE scout_id IS NOT NULL) AS total_with_scout,
    COUNT(*) FILTER (
        WHERE scout_id IS NOT NULL 
        AND EXISTS (
            SELECT 1 FROM canon.identity_links il
            WHERE il.source_table = 'module_ct_scouting_daily'
                AND il.source_pk = sd.id::TEXT
        )
    ) AS with_identity,
    CASE 
        WHEN COUNT(*) FILTER (WHERE scout_id IS NOT NULL) = 0 THEN 'SKIP: No hay registros con scout'
        WHEN COUNT(*) FILTER (
            WHERE scout_id IS NOT NULL 
            AND EXISTS (
                SELECT 1 FROM canon.identity_links il
                WHERE il.source_table = 'module_ct_scouting_daily'
                    AND il.source_pk = sd.id::TEXT
            )
        ) > 0 THEN 'OK: Identity links > 0%'
        ELSE 'ERROR: Identity links = 0%'
    END AS status
FROM public.module_ct_scouting_daily sd
WHERE EXISTS (
    SELECT 1 FROM information_schema.tables
    WHERE table_schema = 'public' AND table_name = 'module_ct_scouting_daily'
);

-- ============================================================================
-- 3. VERIFICAR: ledger scout satisfactory > 0 si ledger existe
-- ============================================================================

SELECT 
    'VERIFICACION_3: Scout satisfactorio en lead_ledger' AS check_type,
    COUNT(DISTINCT ll.person_key) FILTER (WHERE ll.attributed_scout_id IS NOT NULL) AS satisfactory_count,
    COUNT(DISTINCT ll.person_key) AS total_ledger_entries,
    CASE 
        WHEN COUNT(DISTINCT ll.person_key) FILTER (WHERE ll.attributed_scout_id IS NOT NULL) > 0 
        THEN 'OK: Scout satisfactorio > 0'
        WHEN COUNT(DISTINCT ll.person_key) = 0 
        THEN 'SKIP: No hay entradas en lead_ledger'
        ELSE 'WARN: Scout satisfactorio = 0'
    END AS status
FROM observational.lead_ledger ll
WHERE EXISTS (
    SELECT 1 FROM information_schema.tables
    WHERE table_schema = 'observational' AND table_name = 'lead_ledger'
);

-- ============================================================================
-- 4. VERIFICAR: Conflictos listados y explicados
-- ============================================================================

SELECT 
    'VERIFICACION_4: Conflictos listados' AS check_type,
    COUNT(*) AS conflicts_count,
    CASE 
        WHEN EXISTS (
            SELECT 1 FROM information_schema.views
            WHERE table_schema = 'ops' AND table_name = 'v_scout_attribution_conflicts'
        ) THEN 'OK: Vista de conflictos existe'
        ELSE 'ERROR: Vista de conflictos no existe'
    END AS view_status,
    CASE 
        WHEN EXISTS (
            SELECT 1 FROM information_schema.views
            WHERE table_schema = 'ops' AND table_name = 'v_scout_attribution_conflicts'
        ) THEN 
            CASE 
                WHEN COUNT(*) = 0 THEN 'INFO: No hay conflictos'
                ELSE 'OK: Conflictos detectados y listados'
            END
        ELSE 'ERROR: No se puede verificar'
    END AS conflicts_status
FROM ops.v_scout_attribution_conflicts
WHERE EXISTS (
    SELECT 1 FROM information_schema.views
    WHERE table_schema = 'ops' AND table_name = 'v_scout_attribution_conflicts'
);

-- ============================================================================
-- 5. VERIFICAR: Cobranza Yango con scout - devuelve rows y % resolved
-- ============================================================================

SELECT 
    'VERIFICACION_5: Cobranza Yango con scout' AS check_type,
    COUNT(*) AS total_claims,
    COUNT(*) FILTER (WHERE is_scout_resolved = true) AS claims_with_scout,
    COUNT(*) FILTER (WHERE is_scout_resolved = false) AS claims_without_scout,
    CASE 
        WHEN COUNT(*) > 0 
        THEN ROUND((COUNT(*) FILTER (WHERE is_scout_resolved = true)::NUMERIC / COUNT(*) * 100), 2)
        ELSE 0
    END AS pct_resolved,
    CASE 
        WHEN EXISTS (
            SELECT 1 FROM information_schema.views
            WHERE table_schema = 'ops' AND table_name = 'v_yango_collection_with_scout'
        ) THEN 
            CASE 
                WHEN COUNT(*) > 0 THEN 'OK: Vista devuelve rows'
                ELSE 'WARN: Vista no devuelve rows'
            END
        ELSE 'ERROR: Vista no existe'
    END AS status
FROM ops.v_yango_collection_with_scout
WHERE EXISTS (
    SELECT 1 FROM information_schema.views
    WHERE table_schema = 'ops' AND table_name = 'v_yango_collection_with_scout'
);

-- ============================================================================
-- RESUMEN DE VERIFICACIONES
-- ============================================================================

SELECT 
    'RESUMEN' AS summary_type,
    COUNT(*) FILTER (WHERE status LIKE 'OK:%') AS checks_ok,
    COUNT(*) FILTER (WHERE status LIKE 'WARN:%') AS checks_warn,
    COUNT(*) FILTER (WHERE status LIKE 'ERROR:%') AS checks_error,
    COUNT(*) FILTER (WHERE status LIKE 'SKIP:%') AS checks_skip,
    COUNT(*) AS total_checks
FROM (
    -- Copiar resultados de verificaciones anteriores aquí si se necesita un resumen
    SELECT 'DUMMY' AS status
    LIMIT 0
) sub;

