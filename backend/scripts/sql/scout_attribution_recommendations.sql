-- ============================================================================
-- RECOMENDACIONES: SOURCE OF TRUTH Y VISTA CANÓNICA
-- ============================================================================

-- ============================================================================
-- ANÁLISIS DE FUENTES Y PRIORIDAD
-- ============================================================================

/*
PRIORIDAD DE FUENTES (de mayor a menor confiabilidad):

1. observational.lead_ledger.attributed_scout_id
   - Source of Truth PRINCIPAL (ya procesado y atribuido)
   - Grano: 1 fila por person_key (después de atribución)
   - Actualizado por proceso de atribución de leads
   - Confiabilidad: ALTA (ya pasó por reglas de atribución)

2. observational.lead_events.scout_id
   - Fuente de eventos de leads originales
   - Puede tener múltiples eventos por person_key
   - Útil para auditoría histórica y trazabilidad
   - Confiabilidad: MEDIA-ALTA (datos operativos directos)
   - Nota: scout_id puede estar en columna directa o en payload_json->>'scout_id'

3. public.module_ct_migrations.scout_id (si existe)
   - Fuente de migraciones de flota
   - Tiene scout_id y scout_name
   - Confiabilidad: MEDIA-ALTA (datos de migración)

4. public.module_ct_scouting_daily.scout_id (si existe)
   - Fuente de scouting diario
   - Puede tener múltiples registros por driver
   - Confiabilidad: MEDIA (datos operativos)

5. Otras tablas con campos relacionados (recruiter, referral, etc.)
   - Fuentes secundarias
   - Requieren validación cruzada
   - Confiabilidad: BAJA-MEDIA

NOTA: Ya existe ops.v_attribution_canonical que hace atribución de scouts.
Esta vista propuesta complementa y unifica todas las fuentes.
*/

-- ============================================================================
-- PROPUESTA DE VISTA: ops.v_scout_attribution_raw
-- ============================================================================

CREATE OR REPLACE VIEW ops.v_scout_attribution_raw AS
WITH 
-- Fuente 1: observational.lead_ledger (Source of Truth Principal - ya atribuido)
lead_ledger_attribution AS (
    SELECT 
        ll.person_key,
        NULL::TEXT AS driver_id,  -- No tiene driver_id directo
        NULL::TEXT AS driver_license,  -- No disponible en lead_ledger
        NULL::TEXT AS driver_phone,  -- No disponible en lead_ledger
        ll.attributed_scout_id AS scout_id,
        COALESCE(ll.attribution_rule, 'lead_ledger') AS acquisition_method,
        'observational.lead_ledger' AS source_table,
        ll.person_key::TEXT AS source_pk,  -- Usar person_key como source_pk ya que no hay id
        ll.updated_at AS attribution_date,
        ll.updated_at AS created_at,
        1 AS priority  -- Mayor prioridad (ya procesado)
    FROM observational.lead_ledger ll
    WHERE ll.attributed_scout_id IS NOT NULL
),

-- Fuente 2: observational.lead_events (eventos de leads)
lead_events_attribution AS (
    SELECT 
        le.person_key,
        NULL::TEXT AS driver_id,
        NULL::TEXT AS driver_license,
        NULL::TEXT AS driver_phone,
        -- Extraer scout_id: primero desde columna directa, luego desde payload_json
        COALESCE(
            le.scout_id,
            NULLIF((le.payload_json->>'scout_id'), '')::INTEGER
        ) AS scout_id,
        le.source_table AS acquisition_method,
        'observational.lead_events' AS source_table,
        le.source_pk,
        le.event_date AS attribution_date,
        le.created_at,
        2 AS priority
    FROM observational.lead_events le
    WHERE (
        le.scout_id IS NOT NULL
        OR (le.payload_json IS NOT NULL AND le.payload_json->>'scout_id' IS NOT NULL)
    )
),

-- Fuente 3: public.module_ct_migrations (si existe)
migrations_attribution AS (
    SELECT 
        NULL::UUID AS person_key,  -- No tiene person_key directo
        mm.driver_id::TEXT,
        NULL::TEXT AS driver_license,  -- No disponible directamente
        NULL::TEXT AS driver_phone,  -- No disponible directamente
        mm.scout_id,
        'module_ct_migrations' AS acquisition_method,
        'public.module_ct_migrations' AS source_table,
        mm.id::TEXT AS source_pk,
        COALESCE(mm.hire_date, mm.created_at::DATE) AS attribution_date,
        COALESCE(mm.created_at, mm.hire_date::TIMESTAMP) AS created_at,
        3 AS priority
    FROM public.module_ct_migrations mm
    WHERE mm.scout_id IS NOT NULL
        AND EXISTS (
            SELECT 1 FROM information_schema.tables 
            WHERE table_schema = 'public' AND table_name = 'module_ct_migrations'
        )
),

-- Fuente 4: public.module_ct_scouting_daily (si existe)
-- NOTA: Ahora incluye person_key desde identity_links si existe
scouting_daily_attribution AS (
    SELECT 
        il.person_key,  -- Ahora puede tener person_key desde identity_links
        NULL::TEXT AS driver_id,
        sd.driver_license,
        sd.driver_phone,
        sd.scout_id,
        COALESCE(sd.acquisition_method, 'scouting_daily') AS acquisition_method,
        'public.module_ct_scouting_daily' AS source_table,
        sd.id::TEXT AS source_pk,
        COALESCE(sd.registration_date, sd.created_at::DATE) AS attribution_date,
        COALESCE(sd.created_at, sd.registration_date::TIMESTAMP) AS created_at,
        4 AS priority
    FROM public.module_ct_scouting_daily sd
    LEFT JOIN canon.identity_links il 
        ON il.source_table = 'module_ct_scouting_daily'
        AND il.source_pk = sd.id::TEXT
    WHERE sd.scout_id IS NOT NULL
        AND EXISTS (
            SELECT 1 FROM information_schema.tables 
            WHERE table_schema = 'public' AND table_name = 'module_ct_scouting_daily'
        )
)

-- UNION ALL de todas las fuentes
SELECT 
    person_key,
    driver_id,
    driver_license,
    driver_phone,
    scout_id,
    acquisition_method,
    source_table,
    source_pk,
    attribution_date,
    created_at,
    priority
FROM lead_ledger_attribution

UNION ALL

SELECT 
    person_key,
    driver_id,
    driver_license,
    driver_phone,
    scout_id,
    acquisition_method,
    source_table,
    source_pk,
    attribution_date,
    created_at,
    priority
FROM lead_events_attribution

UNION ALL

SELECT 
    person_key,
    driver_id,
    driver_license,
    driver_phone,
    scout_id,
    acquisition_method,
    source_table,
    source_pk,
    attribution_date,
    created_at,
    priority
FROM migrations_attribution

UNION ALL

SELECT 
    person_key,
    driver_id,
    driver_license,
    driver_phone,
    scout_id,
    acquisition_method,
    source_table,
    source_pk,
    attribution_date,
    created_at,
    priority
FROM scouting_daily_attribution;

-- ============================================================================
-- VISTA CANÓNICA: ops.v_scout_attribution (1 fila por driver_id)
-- ============================================================================

CREATE OR REPLACE VIEW ops.v_scout_attribution AS
WITH ranked_attributions AS (
    SELECT 
        COALESCE(driver_id, person_key::TEXT) AS driver_identifier,
        person_key,
        driver_id,
        driver_license,
        driver_phone,
        scout_id,
        acquisition_method,
        source_table,
        source_pk,
        attribution_date,
        created_at,
        priority,
        ROW_NUMBER() OVER (
            PARTITION BY COALESCE(driver_id, person_key::TEXT)
            ORDER BY 
                priority ASC,  -- Menor número = mayor prioridad
                attribution_date DESC,  -- Más reciente primero
                created_at DESC
        ) AS rn
    FROM ops.v_scout_attribution_raw
    WHERE scout_id IS NOT NULL
)
SELECT 
    driver_identifier,
    person_key,
    driver_id,
    driver_license,
    driver_phone,
    scout_id,
    acquisition_method,
    source_table,
    source_pk,
    attribution_date,
    created_at
FROM ranked_attributions
WHERE rn = 1;

-- ============================================================================
-- VISTA DE CONFLICTOS: ops.v_scout_attribution_conflicts
-- ============================================================================

CREATE OR REPLACE VIEW ops.v_scout_attribution_conflicts AS
SELECT 
    COALESCE(driver_id, person_key::TEXT) AS driver_identifier,
    person_key,
    driver_id,
    driver_license,
    driver_phone,
    COUNT(DISTINCT scout_id) AS distinct_scout_count,
    array_agg(DISTINCT scout_id) AS scout_ids,
    array_agg(DISTINCT source_table) AS source_tables,
    array_agg(DISTINCT acquisition_method) AS acquisition_methods,
    MIN(attribution_date) AS first_attribution,
    MAX(attribution_date) AS last_attribution,
    COUNT(*) AS total_attributions
FROM ops.v_scout_attribution_raw
    WHERE scout_id IS NOT NULL
GROUP BY 
    COALESCE(driver_id, person_key::TEXT),
    person_key,
    driver_id,
    driver_license,
    driver_phone
HAVING COUNT(DISTINCT scout_id) > 1;

-- ============================================================================
-- QUERIES DE VERIFICACIÓN
-- ============================================================================

-- Verificar cobertura por person_key
SELECT 
    'Total person_key con scout_id' AS metric,
    COUNT(DISTINCT person_key) AS count
FROM ops.v_scout_attribution
WHERE person_key IS NOT NULL;

-- Verificar cobertura por driver_id (si existe)
SELECT 
    'Total driver_id con scout_id' AS metric,
    COUNT(DISTINCT driver_id) AS count
FROM ops.v_scout_attribution
WHERE driver_id IS NOT NULL;

-- Verificar conflictos
SELECT 
    'Drivers con múltiples scouts' AS metric,
    COUNT(*) AS count
FROM ops.v_scout_attribution_conflicts;

-- Distribución por source_table
SELECT 
    source_table,
    COUNT(*) AS attribution_count,
    COUNT(DISTINCT COALESCE(driver_id, person_key::TEXT)) AS distinct_drivers,
    COUNT(DISTINCT scout_id) AS distinct_scouts
FROM ops.v_scout_attribution_raw
GROUP BY source_table
ORDER BY attribution_count DESC;

-- Distribución por acquisition_method
SELECT 
    acquisition_method,
    COUNT(*) AS attribution_count,
    COUNT(DISTINCT COALESCE(driver_id, person_key::TEXT)) AS distinct_drivers,
    COUNT(DISTINCT scout_id) AS distinct_scouts
FROM ops.v_scout_attribution_raw
GROUP BY acquisition_method
ORDER BY attribution_count DESC;

