-- ============================================================================
-- DIAGNÓSTICO COMPLETO: ATRIBUCIÓN DE CONDUCTORES A SCOUTS
-- Objetivo: Identificar todas las fuentes de datos para scout_id/recruiter
-- ============================================================================

-- ============================================================================
-- QUERY 1: INVENTARIO DE COLUMNAS CANDIDATAS
-- Busca en todos los schemas (public, canon, ops) columnas relacionadas
-- ============================================================================

SELECT 
    table_schema,
    table_name,
    column_name,
    data_type,
    is_nullable,
    column_default
FROM information_schema.columns
WHERE table_schema IN ('public', 'canon', 'ops')
    AND (
        column_name ILIKE '%scout%'
        OR column_name ILIKE '%recruit%'
        OR column_name ILIKE '%referr%'
        OR column_name ILIKE '%capt%'
        OR column_name ILIKE '%promot%'
        OR column_name ILIKE '%agent%'
        OR column_name ILIKE '%utm%'
        OR column_name ILIKE '%source%'
        OR column_name ILIKE '%campaign%'
        OR column_name ILIKE '%link%'
        OR column_name ILIKE '%owner%'
    )
ORDER BY table_schema, table_name, column_name;

-- ============================================================================
-- QUERY 2: PROFILING POR TABLA CANDIDATA
-- Para cada tabla con columnas relacionadas, obtiene estadísticas
-- ============================================================================

DO $$
DECLARE
    rec RECORD;
    total_rows BIGINT;
    non_null_count BIGINT;
    distinct_count BIGINT;
    scout_col TEXT;
    query_text TEXT;
BEGIN
    -- Crear tabla temporal para resultados
    CREATE TEMP TABLE IF NOT EXISTS scout_attribution_profiling (
        table_schema TEXT,
        table_name TEXT,
        scout_column TEXT,
        total_rows BIGINT,
        rows_with_scout BIGINT,
        distinct_scout_ids BIGINT,
        pct_populated NUMERIC(5,2),
        sample_data JSONB
    );

    -- Iterar sobre cada tabla candidata
    FOR rec IN 
        SELECT DISTINCT 
            c.table_schema,
            c.table_name,
            c.column_name AS scout_column
        FROM information_schema.columns c
        WHERE c.table_schema IN ('public', 'canon', 'ops')
            AND (
                c.column_name ILIKE '%scout%'
                OR c.column_name ILIKE '%recruit%'
                OR c.column_name ILIKE '%referr%'
                OR c.column_name ILIKE '%capt%'
                OR c.column_name ILIKE '%promot%'
                OR c.column_name ILIKE '%agent%'
                OR c.column_name ILIKE '%utm%'
                OR c.column_name ILIKE '%source%'
                OR c.column_name ILIKE '%campaign%'
                OR c.column_name ILIKE '%link%'
                OR c.column_name ILIKE '%owner%'
            )
        ORDER BY c.table_schema, c.table_name, c.column_name
    LOOP
        BEGIN
            -- Contar total de filas
            query_text := format('SELECT COUNT(*) FROM %I.%I', rec.table_schema, rec.table_name);
            EXECUTE query_text INTO total_rows;

            -- Contar filas con scout no null
            query_text := format(
                'SELECT COUNT(*) FROM %I.%I WHERE %I IS NOT NULL',
                rec.table_schema, rec.table_name, rec.scout_column
            );
            EXECUTE query_text INTO non_null_count;

            -- Contar distinct scout_ids
            query_text := format(
                'SELECT COUNT(DISTINCT %I) FROM %I.%I WHERE %I IS NOT NULL',
                rec.scout_column, rec.table_schema, rec.table_name, rec.scout_column
            );
            EXECUTE query_text INTO distinct_count;

            -- Obtener muestra de datos (10 filas)
            -- Intentar ordenar por updated_at, created_at, o cualquier columna de fecha
            query_text := format(
                'SELECT jsonb_agg(row_to_json(t)) FROM (
                    SELECT * FROM %I.%I 
                    WHERE %I IS NOT NULL
                    ORDER BY 
                        COALESCE(updated_at, created_at, modified_at, inserted_at) DESC NULLS LAST,
                        (SELECT column_name FROM information_schema.columns 
                         WHERE table_schema = %L AND table_name = %L 
                         AND data_type LIKE ''%%timestamp%%'' LIMIT 1) DESC
                    LIMIT 10
                ) t',
                rec.table_schema, rec.table_name, rec.scout_column,
                rec.table_schema, rec.table_name
            );
            
            -- Insertar resultados
            INSERT INTO scout_attribution_profiling (
                table_schema, table_name, scout_column, 
                total_rows, rows_with_scout, distinct_scout_ids,
                pct_populated, sample_data
            ) VALUES (
                rec.table_schema,
                rec.table_name,
                rec.scout_column,
                total_rows,
                non_null_count,
                distinct_count,
                CASE WHEN total_rows > 0 THEN (non_null_count::NUMERIC / total_rows * 100) ELSE 0 END,
                NULL -- sample_data se puede agregar después si es necesario
            );

        EXCEPTION WHEN OTHERS THEN
            -- Si hay error (tabla no existe, columna no existe, etc), registrar y continuar
            INSERT INTO scout_attribution_profiling (
                table_schema, table_name, scout_column,
                total_rows, rows_with_scout, distinct_scout_ids, pct_populated
            ) VALUES (
                rec.table_schema, rec.table_name, rec.scout_column,
                -1, -1, -1, -1
            );
        END;
    END LOOP;

    -- Mostrar resultados
    SELECT * FROM scout_attribution_profiling
    ORDER BY table_schema, table_name, scout_column;
END $$;

-- ============================================================================
-- QUERY 3: PROFILING MANUAL POR TABLAS CONOCIDAS
-- Para tablas específicas que sabemos que tienen datos de scouts
-- ============================================================================

-- Tabla: observational.lead_events (principal fuente de scout_id)
SELECT 
    'observational.lead_events' AS table_name,
    'scout_id' AS scout_column,
    COUNT(*) AS total_rows,
    COUNT(scout_id) AS rows_with_scout,
    COUNT(DISTINCT scout_id) AS distinct_scout_ids,
    ROUND(COUNT(scout_id)::NUMERIC / NULLIF(COUNT(*), 0) * 100, 2) AS pct_populated
FROM observational.lead_events;

-- Tabla: observational.lead_ledger
SELECT 
    'observational.lead_ledger' AS table_name,
    'attributed_scout_id' AS scout_column,
    COUNT(*) AS total_rows,
    COUNT(attributed_scout_id) AS rows_with_scout,
    COUNT(DISTINCT attributed_scout_id) AS distinct_scout_ids,
    ROUND(COUNT(attributed_scout_id)::NUMERIC / NULLIF(COUNT(*), 0) * 100, 2) AS pct_populated
FROM observational.lead_ledger;

-- Tabla: ops.scouting_daily (si existe)
SELECT 
    'ops.scouting_daily' AS table_name,
    'scout_id' AS scout_column,
    COUNT(*) AS total_rows,
    COUNT(scout_id) AS rows_with_scout,
    COUNT(DISTINCT scout_id) AS distinct_scout_ids,
    ROUND(COUNT(scout_id)::NUMERIC / NULLIF(COUNT(*), 0) * 100, 2) AS pct_populated
FROM ops.scouting_daily
WHERE EXISTS (SELECT 1 FROM information_schema.tables 
              WHERE table_schema = 'ops' AND table_name = 'scouting_daily');

-- Tabla: public.module_ct_migrations (si existe)
SELECT 
    'public.module_ct_migrations' AS table_name,
    'scout_id' AS scout_column,
    COUNT(*) AS total_rows,
    COUNT(scout_id) AS rows_with_scout,
    COUNT(DISTINCT scout_id) AS distinct_scout_ids,
    ROUND(COUNT(scout_id)::NUMERIC / NULLIF(COUNT(*), 0) * 100, 2) AS pct_populated
FROM public.module_ct_migrations
WHERE EXISTS (SELECT 1 FROM information_schema.tables 
              WHERE table_schema = 'public' AND table_name = 'module_ct_migrations');

-- Tabla: public.module_ct_scouting_daily (si existe)
SELECT 
    'public.module_ct_scouting_daily' AS table_name,
    'scout_id' AS scout_column,
    COUNT(*) AS total_rows,
    COUNT(scout_id) AS rows_with_scout,
    COUNT(DISTINCT scout_id) AS distinct_scout_ids,
    ROUND(COUNT(scout_id)::NUMERIC / NULLIF(COUNT(*), 0) * 100, 2) AS pct_populated
FROM public.module_ct_scouting_daily
WHERE EXISTS (SELECT 1 FROM information_schema.tables 
              WHERE table_schema = 'public' AND table_name = 'module_ct_scouting_daily');

-- ============================================================================
-- QUERY 4: IDENTIFICAR COLUMNAS DE IDENTIFICACIÓN DE CONDUCTOR
-- Para poder hacer joins y atribuciones
-- ============================================================================

SELECT 
    table_schema,
    table_name,
    column_name,
    data_type
FROM information_schema.columns
WHERE table_schema IN ('public', 'canon', 'ops')
    AND (
        column_name ILIKE '%driver_id%'
        OR column_name ILIKE '%person_key%'
        OR column_name ILIKE '%license%'
        OR column_name ILIKE '%phone%'
        OR column_name ILIKE '%plate%'
        OR column_name ILIKE '%cedula%'
        OR column_name ILIKE '%dni%'
    )
ORDER BY table_schema, table_name, column_name;

-- ============================================================================
-- QUERY 5: TOP CONFLICTOS - Mismo driver/license/phone asignado a 2+ scouts
-- ============================================================================

-- Conflictos por person_key en lead_events
SELECT 
    'observational.lead_events' AS source_table,
    'person_key' AS match_field,
    person_key,
    COUNT(DISTINCT scout_id) AS distinct_scouts,
    array_agg(DISTINCT scout_id) AS scout_ids,
    COUNT(*) AS total_records
FROM observational.lead_events
WHERE person_key IS NOT NULL 
    AND scout_id IS NOT NULL
GROUP BY person_key
HAVING COUNT(DISTINCT scout_id) > 1
ORDER BY distinct_scouts DESC, total_records DESC
LIMIT 20;

-- Conflictos por person_key en lead_ledger
SELECT 
    'observational.lead_ledger' AS source_table,
    'person_key' AS match_field,
    person_key,
    COUNT(DISTINCT attributed_scout_id) AS distinct_scouts,
    array_agg(DISTINCT attributed_scout_id) AS scout_ids,
    COUNT(*) AS total_records
FROM observational.lead_ledger
WHERE person_key IS NOT NULL 
    AND attributed_scout_id IS NOT NULL
GROUP BY person_key
HAVING COUNT(DISTINCT attributed_scout_id) > 1
ORDER BY distinct_scouts DESC, total_records DESC
LIMIT 20;

-- ============================================================================
-- QUERY 6: MUESTRA DE DATOS POR TABLA CANDIDATA
-- ============================================================================

-- Muestra de observational.lead_events con scout_id
SELECT 
    'observational.lead_events' AS table_name,
    id,
    person_key,
    source_table,
    source_pk,
    scout_id,
    event_date,
    payload_json->>'scout_id' AS scout_id_from_payload,
    created_at
FROM observational.lead_events
WHERE scout_id IS NOT NULL
    OR (payload_json IS NOT NULL AND payload_json->>'scout_id' IS NOT NULL)
ORDER BY COALESCE(event_date, created_at) DESC
LIMIT 10;

-- Muestra de observational.lead_ledger con attributed_scout_id
SELECT 
    'observational.lead_ledger' AS table_name,
    id,
    person_key,
    attributed_scout_id,
    attribution_confidence,
    attribution_rule,
    created_at,
    updated_at
FROM observational.lead_ledger
WHERE attributed_scout_id IS NOT NULL
ORDER BY COALESCE(updated_at, created_at) DESC
LIMIT 10;

-- Muestra de public.module_ct_migrations con scout_id (si existe)
SELECT 
    'public.module_ct_migrations' AS table_name,
    id,
    driver_id,
    scout_id,
    scout_name,
    hire_date,
    created_at
FROM public.module_ct_migrations
WHERE EXISTS (SELECT 1 FROM information_schema.tables 
              WHERE table_schema = 'public' AND table_name = 'module_ct_migrations')
    AND scout_id IS NOT NULL
ORDER BY COALESCE(hire_date, created_at) DESC
LIMIT 10;

-- ============================================================================
-- QUERY 7: ANÁLISIS DE COBERTURA - Qué % de drivers tienen scout_id
-- ============================================================================

-- Cobertura de scout_id en lead_events
SELECT 
    'Cobertura de scout_id en observational.lead_events' AS metric,
    COUNT(*) AS total_events,
    COUNT(scout_id) AS events_with_scout,
    COUNT(*) - COUNT(scout_id) AS events_without_scout,
    ROUND(COUNT(scout_id)::NUMERIC / NULLIF(COUNT(*), 0) * 100, 2) AS pct_with_scout
FROM observational.lead_events;

-- Cobertura de attributed_scout_id en lead_ledger
SELECT 
    'Cobertura de attributed_scout_id en observational.lead_ledger' AS metric,
    COUNT(*) AS total_ledger_entries,
    COUNT(attributed_scout_id) AS entries_with_scout,
    COUNT(*) - COUNT(attributed_scout_id) AS entries_without_scout,
    ROUND(COUNT(attributed_scout_id)::NUMERIC / NULLIF(COUNT(*), 0) * 100, 2) AS pct_with_scout
FROM observational.lead_ledger;

-- Distribución de scouts en lead_events (top 20)
SELECT 
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
-- QUERY 8: VERIFICAR SI HAY OTRAS TABLAS DE ATRIBUCIÓN
-- ============================================================================

-- Buscar tablas que puedan tener relaciones scout-driver
SELECT 
    t.table_schema,
    t.table_name,
    string_agg(c.column_name, ', ' ORDER BY c.column_name) AS relevant_columns
FROM information_schema.tables t
JOIN information_schema.columns c 
    ON t.table_schema = c.table_schema 
    AND t.table_name = c.table_name
WHERE t.table_schema IN ('public', 'canon', 'ops')
    AND t.table_type = 'BASE TABLE'
    AND (
        c.column_name ILIKE '%scout%'
        OR c.column_name ILIKE '%driver%'
        OR c.column_name ILIKE '%person_key%'
    )
GROUP BY t.table_schema, t.table_name
HAVING COUNT(DISTINCT c.column_name) >= 2  -- Al menos 2 columnas relevantes
ORDER BY t.table_schema, t.table_name;

