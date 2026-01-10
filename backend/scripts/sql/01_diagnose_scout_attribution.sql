-- ============================================================================
-- DIAGNÓSTICO: SCOUT ATTRIBUTION
-- ============================================================================
-- Objetivo: Calcular métricas clave ANTES de aplicar fixes
-- Ejecución: Idempotente (solo consultas SELECT)
-- ============================================================================

-- ============================================================================
-- MÉTRICA 1: Total de personas
-- ============================================================================
-- Definición: distinct person_key en identity_registry (canónico)
-- ============================================================================

SELECT 
    'total_persons' AS metric,
    COUNT(DISTINCT person_key) AS value
FROM canon.identity_registry;

-- ============================================================================
-- MÉTRICA 2: Personas con scout satisfactorio
-- ============================================================================
-- Definición: personas con attributed_scout_id en lead_ledger (source-of-truth)
-- ============================================================================

SELECT 
    'persons_with_scout_satisfactory' AS metric,
    COUNT(DISTINCT person_key) AS value
FROM observational.lead_ledger
WHERE attributed_scout_id IS NOT NULL;

-- ============================================================================
-- MÉTRICA 3: Personas con scout en eventos pero NO en ledger (GAP)
-- ============================================================================
-- Definición: tienen scout_id en lead_events pero NO attributed_scout_id en lead_ledger
-- ============================================================================

SELECT 
    'persons_scout_in_events_not_ledger' AS metric,
    COUNT(DISTINCT le.person_key) AS value
FROM observational.lead_events le
WHERE le.scout_id IS NOT NULL
    AND le.person_key IS NOT NULL
    AND NOT EXISTS (
        SELECT 1 FROM observational.lead_ledger ll
        WHERE ll.person_key = le.person_key
            AND ll.attributed_scout_id IS NOT NULL
    );

-- ============================================================================
-- MÉTRICA 4: Eventos sin scout_id (GAP)
-- ============================================================================
-- ============================================================================

SELECT 
    'events_without_scout_id' AS metric,
    COUNT(*) AS value
FROM observational.lead_events
WHERE scout_id IS NULL 
    AND (payload_json IS NULL OR payload_json->>'scout_id' IS NULL);

-- ============================================================================
-- MÉTRICA 5: scouting_daily con scout_id - Cobertura
-- ============================================================================
-- Cuántas tienen identity_links, lead_events, llegan a lead_ledger
-- ============================================================================

-- 5a: scouting_daily total con scout_id
SELECT 
    'scouting_daily_total_with_scout' AS metric,
    COUNT(*) AS value
FROM public.module_ct_scouting_daily
WHERE EXISTS (
    SELECT 1 FROM information_schema.tables 
    WHERE table_schema = 'public' AND table_name = 'module_ct_scouting_daily'
)
    AND scout_id IS NOT NULL;

-- 5b: scouting_daily con scout_id que tienen identity_links
SELECT 
    'scouting_daily_with_identity_links' AS metric,
    COUNT(DISTINCT sd.id) AS value
FROM public.module_ct_scouting_daily sd
WHERE EXISTS (
    SELECT 1 FROM information_schema.tables 
    WHERE table_schema = 'public' AND table_name = 'module_ct_scouting_daily'
)
    AND sd.scout_id IS NOT NULL
    AND EXISTS (
        SELECT 1 FROM canon.identity_links il
        WHERE il.source_table = 'module_ct_scouting_daily'
            AND il.source_pk = sd.id::TEXT
    );

-- 5c: scouting_daily con scout_id que tienen lead_events
SELECT 
    'scouting_daily_with_lead_events' AS metric,
    COUNT(DISTINCT sd.id) AS value
FROM public.module_ct_scouting_daily sd
WHERE EXISTS (
    SELECT 1 FROM information_schema.tables 
    WHERE table_schema = 'public' AND table_name = 'module_ct_scouting_daily'
)
    AND sd.scout_id IS NOT NULL
    AND EXISTS (
        SELECT 1 FROM canon.identity_links il
        JOIN observational.lead_events le ON le.source_table = il.source_table
            AND le.source_pk = il.source_pk
        WHERE il.source_table = 'module_ct_scouting_daily'
            AND il.source_pk = sd.id::TEXT
    );

-- 5d: scouting_daily con scout_id que llegan a lead_ledger con scout satisfactorio
SELECT 
    'scouting_daily_with_ledger_scout' AS metric,
    COUNT(DISTINCT sd.id) AS value
FROM public.module_ct_scouting_daily sd
WHERE EXISTS (
    SELECT 1 FROM information_schema.tables 
    WHERE table_schema = 'public' AND table_name = 'module_ct_scouting_daily'
)
    AND sd.scout_id IS NOT NULL
    AND EXISTS (
        SELECT 1 FROM canon.identity_links il
        JOIN observational.lead_ledger ll ON ll.person_key = il.person_key
        WHERE il.source_table = 'module_ct_scouting_daily'
            AND il.source_pk = sd.id::TEXT
            AND ll.attributed_scout_id IS NOT NULL
    );

-- ============================================================================
-- MÉTRICA 6: % Cobertura "Satisfactorio"
-- ============================================================================
-- Porcentaje de scouting_daily con scout_id que llegan a lead_ledger con scout
-- ============================================================================

SELECT 
    'scouting_daily_coverage_satisfactory_pct' AS metric,
    CASE 
        WHEN total_with_scout > 0 THEN 
            ROUND((with_ledger_scout::NUMERIC / total_with_scout * 100), 2)
        ELSE 0 
    END AS value
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

-- ============================================================================
-- MÉTRICA 7: Diagnóstico de por qué 0% cobertura (si aplica)
-- ============================================================================
-- ============================================================================

-- 7a: scouting_daily SIN identity_links
SELECT 
    'scouting_daily_no_identity_links' AS metric,
    COUNT(*) AS value
FROM public.module_ct_scouting_daily sd
WHERE EXISTS (
    SELECT 1 FROM information_schema.tables 
    WHERE table_schema = 'public' AND table_name = 'module_ct_scouting_daily'
)
    AND sd.scout_id IS NOT NULL
    AND NOT EXISTS (
        SELECT 1 FROM canon.identity_links il
        WHERE il.source_table = 'module_ct_scouting_daily'
            AND il.source_pk = sd.id::TEXT
    );

-- 7b: scouting_daily CON identity_links pero SIN lead_ledger
SELECT 
    'scouting_daily_with_links_no_ledger' AS metric,
    COUNT(DISTINCT sd.id) AS value
FROM public.module_ct_scouting_daily sd
WHERE EXISTS (
    SELECT 1 FROM information_schema.tables 
    WHERE table_schema = 'public' AND table_name = 'module_ct_scouting_daily'
)
    AND sd.scout_id IS NOT NULL
    AND EXISTS (
        SELECT 1 FROM canon.identity_links il
        WHERE il.source_table = 'module_ct_scouting_daily'
            AND il.source_pk = sd.id::TEXT
    )
    AND NOT EXISTS (
        SELECT 1 FROM canon.identity_links il
        JOIN observational.lead_ledger ll ON ll.person_key = il.person_key
        WHERE il.source_table = 'module_ct_scouting_daily'
            AND il.source_pk = sd.id::TEXT
    );

-- ============================================================================
-- MÉTRICA 8: Distribución de scouts en lead_events (top 20)
-- ============================================================================
-- ============================================================================

SELECT 
    'scout_distribution' AS metric_type,
    scout_id,
    COUNT(*) AS event_count,
    COUNT(DISTINCT person_key) AS distinct_persons,
    ROUND(COUNT(*)::NUMERIC / NULLIF((SELECT COUNT(*) FROM observational.lead_events WHERE scout_id IS NOT NULL), 0) * 100, 2) AS pct_of_assigned
FROM observational.lead_events
WHERE scout_id IS NOT NULL
GROUP BY scout_id
ORDER BY event_count DESC
LIMIT 20;

-- ============================================================================
-- RESUMEN CONSOLIDADO
-- ============================================================================
-- ============================================================================

SELECT 
    '=== RESUMEN DIAGNÓSTICO SCOUT ATTRIBUTION ===' AS section;

SELECT 
    metric,
    value,
    CASE 
        WHEN metric = 'scouting_daily_coverage_satisfactory_pct' AND value::NUMERIC = 0 THEN 'WARN: Cobertura 0% - Revisar pipeline'
        WHEN metric LIKE '%gap%' AND value::NUMERIC > 0 THEN 'WARN: Gap detectado'
        ELSE 'OK'
    END AS status
FROM (
    SELECT 'total_persons' AS metric, COUNT(DISTINCT person_key)::TEXT AS value FROM canon.identity_registry
    UNION ALL
    SELECT 'persons_with_scout_satisfactory', COUNT(DISTINCT person_key)::TEXT FROM observational.lead_ledger WHERE attributed_scout_id IS NOT NULL
    UNION ALL
    SELECT 'persons_scout_in_events_not_ledger', COUNT(DISTINCT le.person_key)::TEXT FROM observational.lead_events le WHERE le.scout_id IS NOT NULL AND le.person_key IS NOT NULL AND NOT EXISTS (SELECT 1 FROM observational.lead_ledger ll WHERE ll.person_key = le.person_key AND ll.attributed_scout_id IS NOT NULL)
    UNION ALL
    SELECT 'events_without_scout_id', COUNT(*)::TEXT FROM observational.lead_events WHERE scout_id IS NULL AND (payload_json IS NULL OR payload_json->>'scout_id' IS NULL)
) metrics
ORDER BY metric;

