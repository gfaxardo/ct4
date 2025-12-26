-- ============================================================================
-- Ingestión de public.module_ct_migrations hacia observational.lead_events
-- ============================================================================
-- Objetivo: Insertar registros de module_ct_migrations en lead_events con
-- source_table='module_ct_migrations' para desbloquear fleet_migration en
-- v_conversion_metrics y v_payment_calculation.
--
-- El script es idempotente: no duplica registros si ya existen.
-- ============================================================================

BEGIN;

-- Paso 1: Mostrar conteo antes
SELECT 'before_lead_events_count' AS k, COUNT(*) AS v FROM observational.lead_events;

-- Paso 2: Insertar registros de module_ct_migrations
WITH src AS (
    -- Normalizar y mapear columnas de module_ct_migrations
    SELECT 
        id::text AS source_pk,
        'module_ct_migrations' AS source_table,
        -- Usar hire_date como event_date (fecha del lead/migración)
        -- Si hire_date es NULL, usar created_at como fallback
        COALESCE(hire_date::date, created_at::date) AS event_date,
        scout_id,
        -- Crear payload_json con información relevante para identidad
        jsonb_build_object(
            'driver_id', driver_id,
            'driver_name', driver_name,
            'scout_name', scout_name,
            'hire_date', hire_date,
            'created_at', created_at,
            'updated_at', updated_at
        ) AS payload_json,
        -- created_at para timestamp de creación del evento en lead_events
        COALESCE(created_at, NOW()) AS created_at_ts
    FROM public.module_ct_migrations
    WHERE id IS NOT NULL
)
INSERT INTO observational.lead_events (
    source_table,
    source_pk,
    event_date,
    person_key,
    scout_id,
    payload_json,
    created_at
)
SELECT 
    src.source_table,
    src.source_pk,
    src.event_date,
    NULL AS person_key,
    src.scout_id,
    src.payload_json,
    src.created_at_ts
FROM src
-- Anti-join: solo insertar si no existe ya este registro
WHERE NOT EXISTS (
    SELECT 1
    FROM observational.lead_events le
    WHERE le.source_table = src.source_table
        AND le.source_pk = src.source_pk
)
-- Ordenar por id para insertar de forma determinista
ORDER BY src.source_pk;

-- Paso 3: Mostrar conteo después
SELECT 'after_lead_events_count' AS k, COUNT(*) AS v FROM observational.lead_events;

-- Paso 4: Mostrar cuántas filas se insertaron
SELECT 'inserted_rows' AS k, 
       (SELECT COUNT(*) FROM observational.lead_events WHERE source_table = 'module_ct_migrations') AS v;

COMMIT;

-- Paso 5: Verificación de estructura insertada
SELECT 
    'module_ct_migrations_inserted' AS source,
    COUNT(*) AS count,
    MIN(event_date) AS min_event_date,
    MAX(event_date) AS max_event_date,
    COUNT(DISTINCT scout_id) AS distinct_scouts
FROM observational.lead_events
WHERE source_table = 'module_ct_migrations';

