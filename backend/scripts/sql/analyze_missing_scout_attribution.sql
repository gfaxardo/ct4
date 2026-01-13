-- ============================================================================
-- ANÁLISIS: REGISTROS SIN SCOUT Y RAZONES
-- ============================================================================
-- Objetivo: Identificar cuántos registros no tienen scout y por qué
-- ============================================================================

-- ============================================================================
-- QUERY 1: TOTAL DE REGISTROS SIN SCOUT
-- ============================================================================

-- Total de personas en identity_registry
SELECT 
    'Total personas en identity_registry' AS metric,
    COUNT(*) AS count
FROM canon.identity_registry;

-- Personas con scout (desde lead_ledger)
SELECT 
    'Personas CON scout (desde lead_ledger)' AS metric,
    COUNT(DISTINCT person_key) AS count
FROM observational.lead_ledger
WHERE attributed_scout_id IS NOT NULL;

-- Personas SIN scout (desde lead_ledger)
SELECT 
    'Personas SIN scout (desde lead_ledger)' AS metric,
    COUNT(DISTINCT person_key) AS count
FROM observational.lead_ledger
WHERE attributed_scout_id IS NULL;

-- Gap: Personas en identity_registry pero sin scout
SELECT 
    'GAP: Personas en identity_registry SIN scout' AS metric,
    COUNT(DISTINCT ir.person_key) AS count
FROM canon.identity_registry ir
LEFT JOIN observational.lead_ledger ll 
    ON ll.person_key = ir.person_key 
    AND ll.attributed_scout_id IS NOT NULL
WHERE ll.person_key IS NULL;

-- ============================================================================
-- QUERY 2: ANÁLISIS POR FUENTE - ¿Por qué no tienen scout?
-- ============================================================================

-- Personas con lead_events pero sin scout_id
SELECT 
    'Personas con lead_events pero SIN scout_id' AS metric,
    COUNT(DISTINCT person_key) AS count
FROM observational.lead_events
WHERE person_key IS NOT NULL
    AND scout_id IS NULL
    AND (payload_json IS NULL OR payload_json->>'scout_id' IS NULL);

-- Personas con lead_events que SÍ tienen scout_id
SELECT 
    'Personas con lead_events que SÍ tienen scout_id' AS metric,
    COUNT(DISTINCT person_key) AS count
FROM observational.lead_events
WHERE person_key IS NOT NULL
    AND (
        scout_id IS NOT NULL
        OR (payload_json IS NOT NULL AND payload_json->>'scout_id' IS NOT NULL)
    );

-- Personas con identity_links pero sin lead_events con scout
SELECT 
    'Personas con identity_links pero SIN lead_events con scout' AS metric,
    COUNT(DISTINCT il.person_key) AS count
FROM canon.identity_links il
LEFT JOIN observational.lead_events le 
    ON le.person_key = il.person_key
    AND (
        le.scout_id IS NOT NULL
        OR (le.payload_json IS NOT NULL AND le.payload_json->>'scout_id' IS NOT NULL)
    )
WHERE le.person_key IS NULL;

-- ============================================================================
-- QUERY 3: ANÁLISIS POR SOURCE_TABLE EN LEAD_EVENTS
-- ============================================================================

-- Distribución de lead_events por source_table y presencia de scout_id
SELECT 
    le.source_table,
    COUNT(*) AS total_events,
    COUNT(DISTINCT le.person_key) AS distinct_persons,
    COUNT(*) FILTER (WHERE le.scout_id IS NOT NULL OR (le.payload_json IS NOT NULL AND le.payload_json->>'scout_id' IS NOT NULL)) AS events_with_scout,
    COUNT(*) FILTER (WHERE le.scout_id IS NULL AND (le.payload_json IS NULL OR le.payload_json->>'scout_id' IS NULL)) AS events_without_scout,
    ROUND(
        COUNT(*) FILTER (WHERE le.scout_id IS NOT NULL OR (le.payload_json IS NOT NULL AND le.payload_json->>'scout_id' IS NOT NULL))::NUMERIC / 
        NULLIF(COUNT(*), 0) * 100, 
        2
    ) AS pct_with_scout
FROM observational.lead_events le
WHERE le.person_key IS NOT NULL
GROUP BY le.source_table
ORDER BY total_events DESC;

-- ============================================================================
-- QUERY 4: ANÁLISIS DE LEAD_LEDGER - ¿Por qué no tienen attributed_scout_id?
-- ============================================================================

-- Distribución de lead_ledger por atribución
SELECT 
    'Total en lead_ledger' AS metric,
    COUNT(*) AS count
FROM observational.lead_ledger;

SELECT 
    'Con attributed_scout_id' AS metric,
    COUNT(*) AS count
FROM observational.lead_ledger
WHERE attributed_scout_id IS NOT NULL;

SELECT 
    'SIN attributed_scout_id' AS metric,
    COUNT(*) AS count
FROM observational.lead_ledger
WHERE attributed_scout_id IS NULL;

-- Razones por las que no tienen scout (según attribution_rule y confidence_level)
SELECT 
    attribution_rule,
    confidence_level,
    decision_status,
    COUNT(*) AS count,
    COUNT(*) FILTER (WHERE attributed_scout_id IS NOT NULL) AS with_scout,
    COUNT(*) FILTER (WHERE attributed_scout_id IS NULL) AS without_scout
FROM observational.lead_ledger
GROUP BY attribution_rule, confidence_level, decision_status
ORDER BY count DESC;

-- ============================================================================
-- QUERY 5: MUESTRA DE REGISTROS SIN SCOUT
-- ============================================================================

-- Muestra de personas sin scout (top 20)
SELECT 
    ir.person_key,
    ir.primary_full_name,
    ir.primary_phone,
    ir.primary_license,
    ir.created_at AS identity_created_at,
    -- Verificar si tiene lead_events
    (SELECT COUNT(*) FROM observational.lead_events le WHERE le.person_key = ir.person_key) AS lead_events_count,
    -- Verificar si tiene lead_ledger
    CASE WHEN ll.person_key IS NOT NULL THEN 'YES' ELSE 'NO' END AS has_lead_ledger,
    -- Verificar source_tables en identity_links
    (SELECT string_agg(DISTINCT il.source_table, ', ') 
     FROM canon.identity_links il 
     WHERE il.person_key = ir.person_key) AS source_tables
FROM canon.identity_registry ir
LEFT JOIN observational.lead_ledger ll 
    ON ll.person_key = ir.person_key 
    AND ll.attributed_scout_id IS NOT NULL
WHERE ll.person_key IS NULL
ORDER BY ir.created_at DESC
LIMIT 20;

-- ============================================================================
-- QUERY 6: ANÁLISIS DE FUENTES ORIGINALES SIN SCOUT_ID
-- ============================================================================

-- module_ct_migrations sin scout_id (si existe)
SELECT 
    'module_ct_migrations SIN scout_id' AS metric,
    COUNT(*) AS count
FROM public.module_ct_migrations
WHERE EXISTS (
    SELECT 1 FROM information_schema.tables 
    WHERE table_schema = 'public' AND table_name = 'module_ct_migrations'
)
AND scout_id IS NULL;

-- module_ct_scouting_daily sin scout_id (si existe)
SELECT 
    'module_ct_scouting_daily SIN scout_id' AS metric,
    COUNT(*) AS count
FROM public.module_ct_scouting_daily
WHERE EXISTS (
    SELECT 1 FROM information_schema.tables 
    WHERE table_schema = 'public' AND table_name = 'module_ct_scouting_daily'
)
AND scout_id IS NULL;

-- ============================================================================
-- QUERY 7: RESUMEN EJECUTIVO
-- ============================================================================

WITH stats AS (
    SELECT 
        (SELECT COUNT(*) FROM canon.identity_registry) AS total_persons,
        (SELECT COUNT(DISTINCT person_key) FROM observational.lead_ledger WHERE attributed_scout_id IS NOT NULL) AS persons_with_scout,
        (SELECT COUNT(DISTINCT person_key) FROM observational.lead_ledger WHERE attributed_scout_id IS NULL) AS persons_without_scout_in_ledger,
        (SELECT COUNT(DISTINCT person_key) FROM observational.lead_events 
         WHERE person_key IS NOT NULL 
         AND (scout_id IS NOT NULL OR (payload_json IS NOT NULL AND payload_json->>'scout_id' IS NOT NULL))) AS persons_with_scout_in_events
)
SELECT 
    'RESUMEN EJECUTIVO' AS summary,
    total_persons,
    persons_with_scout AS personas_con_scout_atribuido,
    total_persons - persons_with_scout AS personas_sin_scout_atribuido,
    ROUND((persons_with_scout::NUMERIC / NULLIF(total_persons, 0) * 100), 2) AS pct_con_scout,
    ROUND(((total_persons - persons_with_scout)::NUMERIC / NULLIF(total_persons, 0) * 100), 2) AS pct_sin_scout,
    persons_with_scout_in_events AS personas_con_scout_en_eventos,
    persons_without_scout_in_ledger AS personas_sin_scout_en_ledger
FROM stats;





