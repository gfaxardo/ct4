-- ============================================================================
-- ANÁLISIS: COBERTURA DE SCOUT EN SCOUTING_DAILY
-- ============================================================================
-- Objetivo: Qué % de registros en scouting_daily con scout_id están
-- considerados como "con scout satisfactorio" en el sistema (lead_ledger)
-- ============================================================================

-- ============================================================================
-- QUERY 1: TOTAL DE REGISTROS EN SCOUTING_DAILY CON SCOUT_ID
-- ============================================================================

SELECT 
    'Total registros en module_ct_scouting_daily' AS metric,
    COUNT(*) AS count
FROM public.module_ct_scouting_daily
WHERE EXISTS (
    SELECT 1 FROM information_schema.tables 
    WHERE table_schema = 'public' AND table_name = 'module_ct_scouting_daily'
);

SELECT 
    'Registros CON scout_id' AS metric,
    COUNT(*) AS count
FROM public.module_ct_scouting_daily
WHERE EXISTS (
    SELECT 1 FROM information_schema.tables 
    WHERE table_schema = 'public' AND table_name = 'module_ct_scouting_daily'
)
AND scout_id IS NOT NULL;

SELECT 
    'Registros SIN scout_id' AS metric,
    COUNT(*) AS count
FROM public.module_ct_scouting_daily
WHERE EXISTS (
    SELECT 1 FROM information_schema.tables 
    WHERE table_schema = 'public' AND table_name = 'module_ct_scouting_daily'
)
AND scout_id IS NULL;

-- ============================================================================
-- QUERY 2: REGISTROS CON SCOUT_ID QUE TIENEN PERSON_KEY ASOCIADO
-- ============================================================================

-- Registros con scout_id que tienen identity_link (tienen person_key)
SELECT 
    'Registros con scout_id que tienen person_key (identity_links)' AS metric,
    COUNT(DISTINCT sd.id) AS count
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

-- Registros con scout_id que NO tienen person_key
SELECT 
    'Registros con scout_id que NO tienen person_key' AS metric,
    COUNT(DISTINCT sd.id) AS count
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

-- ============================================================================
-- QUERY 3: REGISTROS CON SCOUT_ID QUE TIENEN SCOUT ATRIBUIDO EN LEAD_LEDGER
-- ============================================================================

-- Registros con scout_id que tienen attributed_scout_id en lead_ledger
SELECT 
    'Registros con scout_id que tienen scout atribuido en lead_ledger' AS metric,
    COUNT(DISTINCT sd.id) AS count
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

-- Registros con scout_id que NO tienen scout atribuido en lead_ledger
SELECT 
    'Registros con scout_id que NO tienen scout atribuido en lead_ledger' AS metric,
    COUNT(DISTINCT sd.id) AS count
FROM public.module_ct_scouting_daily sd
WHERE EXISTS (
    SELECT 1 FROM information_schema.tables 
    WHERE table_schema = 'public' AND table_name = 'module_ct_scouting_daily'
)
AND sd.scout_id IS NOT NULL
AND (
    -- No tienen identity_link
    NOT EXISTS (
        SELECT 1 FROM canon.identity_links il
        WHERE il.source_table = 'module_ct_scouting_daily'
            AND il.source_pk = sd.id::TEXT
    )
    OR
    -- Tienen identity_link pero no lead_ledger con scout
    NOT EXISTS (
        SELECT 1 FROM canon.identity_links il
        JOIN observational.lead_ledger ll ON ll.person_key = il.person_key
        WHERE il.source_table = 'module_ct_scouting_daily'
            AND il.source_pk = sd.id::TEXT
            AND ll.attributed_scout_id IS NOT NULL
    )
);

-- ============================================================================
-- QUERY 4: ANÁLISIS DETALLADO - MATCHING DE SCOUT_ID
-- ============================================================================

-- Verificar si el scout_id de scouting_daily coincide con el attributed_scout_id
SELECT 
    'Registros donde scout_id coincide con attributed_scout_id' AS metric,
    COUNT(DISTINCT sd.id) AS count
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
        AND ll.attributed_scout_id = sd.scout_id
);

-- Registros donde scout_id NO coincide (conflicto)
SELECT 
    'Registros donde scout_id NO coincide con attributed_scout_id' AS metric,
    COUNT(DISTINCT sd.id) AS count
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
        AND ll.attributed_scout_id != sd.scout_id
);

-- ============================================================================
-- QUERY 5: RESUMEN EJECUTIVO CON PORCENTAJES
-- ============================================================================

WITH stats AS (
    SELECT 
        (SELECT COUNT(*) FROM public.module_ct_scouting_daily 
         WHERE EXISTS (SELECT 1 FROM information_schema.tables 
                      WHERE table_schema = 'public' AND table_name = 'module_ct_scouting_daily')
         AND scout_id IS NOT NULL) AS total_with_scout_id,
        
        (SELECT COUNT(DISTINCT sd.id) FROM public.module_ct_scouting_daily sd
         WHERE EXISTS (SELECT 1 FROM information_schema.tables 
                      WHERE table_schema = 'public' AND table_name = 'module_ct_scouting_daily')
         AND sd.scout_id IS NOT NULL
         AND EXISTS (
             SELECT 1 FROM canon.identity_links il
             JOIN observational.lead_ledger ll ON ll.person_key = il.person_key
             WHERE il.source_table = 'module_ct_scouting_daily'
                 AND il.source_pk = sd.id::TEXT
                 AND ll.attributed_scout_id IS NOT NULL
         )) AS with_scout_attributed,
        
        (SELECT COUNT(DISTINCT sd.id) FROM public.module_ct_scouting_daily sd
         WHERE EXISTS (SELECT 1 FROM information_schema.tables 
                      WHERE table_schema = 'public' AND table_name = 'module_ct_scouting_daily')
         AND sd.scout_id IS NOT NULL
         AND EXISTS (
             SELECT 1 FROM canon.identity_links il
             JOIN observational.lead_ledger ll ON ll.person_key = il.person_key
             WHERE il.source_table = 'module_ct_scouting_daily'
                 AND il.source_pk = sd.id::TEXT
                 AND ll.attributed_scout_id = sd.scout_id
         )) AS with_matching_scout
)
SELECT 
    'RESUMEN EJECUTIVO' AS summary,
    total_with_scout_id AS total_registros_con_scout_id,
    with_scout_attributed AS registros_con_scout_atribuido,
    total_with_scout_id - with_scout_attributed AS registros_sin_scout_atribuido,
    ROUND((with_scout_attributed::NUMERIC / NULLIF(total_with_scout_id, 0) * 100), 2) AS pct_con_scout_atribuido,
    ROUND(((total_with_scout_id - with_scout_attributed)::NUMERIC / NULLIF(total_with_scout_id, 0) * 100), 2) AS pct_sin_scout_atribuido,
    with_matching_scout AS registros_con_scout_coincidente,
    ROUND((with_matching_scout::NUMERIC / NULLIF(total_with_scout_id, 0) * 100), 2) AS pct_con_scout_coincidente
FROM stats;

-- ============================================================================
-- QUERY 6: MUESTRA DE CASOS SIN SCOUT ATRIBUIDO
-- ============================================================================

-- Muestra de registros con scout_id pero sin scout atribuido
SELECT 
    sd.id AS scouting_daily_id,
    sd.scout_id AS scout_id_en_fuente,
    sd.driver_phone,
    sd.driver_license,
    sd.registration_date,
    -- Verificar si tiene person_key
    CASE WHEN il.person_key IS NOT NULL THEN 'YES' ELSE 'NO' END AS tiene_person_key,
    -- Verificar si tiene lead_ledger
    CASE WHEN ll.person_key IS NOT NULL THEN 'YES' ELSE 'NO' END AS tiene_lead_ledger,
    -- Scout atribuido (si existe)
    ll.attributed_scout_id AS scout_atribuido,
    -- Coincide?
    CASE 
        WHEN ll.attributed_scout_id = sd.scout_id THEN 'SI'
        WHEN ll.attributed_scout_id IS NOT NULL THEN 'NO (conflicto)'
        ELSE 'NO (sin atribuir)'
    END AS scout_coincide
FROM public.module_ct_scouting_daily sd
LEFT JOIN canon.identity_links il 
    ON il.source_table = 'module_ct_scouting_daily'
    AND il.source_pk = sd.id::TEXT
LEFT JOIN observational.lead_ledger ll 
    ON ll.person_key = il.person_key
WHERE EXISTS (
    SELECT 1 FROM information_schema.tables 
    WHERE table_schema = 'public' AND table_name = 'module_ct_scouting_daily'
)
AND sd.scout_id IS NOT NULL
AND (
    il.person_key IS NULL
    OR ll.attributed_scout_id IS NULL
    OR ll.attributed_scout_id != sd.scout_id
)
ORDER BY sd.registration_date DESC
LIMIT 20;


