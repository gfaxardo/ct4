-- ============================================================================
-- FIX: Eventos sin scout_id (Categoría A - principalmente module_ct_cabinet_leads)
-- ============================================================================
-- OBJETIVO: Detectar y documentar eventos sin scout_id para análisis posterior
-- 
-- ESTRATEGIA:
-- 1. Identificar eventos sin scout_id
-- 2. Buscar posibles fuentes de scout_id (referral_link_id, etc.)
-- 3. Si hay mapping disponible, backfill scout_id
-- 4. Si no, crear alerta para revisión manual
-- ============================================================================

-- ============================================================================
-- PASO 1: Identificar eventos sin scout_id
-- ============================================================================

CREATE OR REPLACE VIEW ops.v_events_missing_scout_id AS
SELECT 
    le.id AS event_id,
    le.person_key,
    le.source_table,
    le.source_pk,
    le.event_date,
    le.scout_id AS current_scout_id,
    le.payload_json->>'scout_id' AS scout_id_in_payload,
    le.payload_json->>'referral_link_id' AS referral_link_id,
    le.payload_json->>'recruiter_id' AS recruiter_id,
    le.payload_json->>'utm_source' AS utm_source,
    le.payload_json->>'utm_campaign' AS utm_campaign,
    le.created_at
FROM observational.lead_events le
WHERE le.person_key IS NOT NULL
    AND le.scout_id IS NULL
    AND (le.payload_json IS NULL OR le.payload_json->>'scout_id' IS NULL)
    AND le.source_table = 'module_ct_cabinet_leads'
ORDER BY le.event_date DESC, le.created_at DESC;

-- ============================================================================
-- PASO 2: Verificar si existe tabla de scouts con referral_link_id
-- ============================================================================

-- Verificar si existe tabla module_ct_scouts_list o similar
DO $$
DECLARE
    scouts_table_exists BOOLEAN;
    referral_column_exists BOOLEAN;
BEGIN
    -- Verificar si existe tabla de scouts
    SELECT EXISTS (
        SELECT 1 FROM information_schema.tables 
        WHERE table_schema = 'public' 
        AND table_name = 'module_ct_scouts_list'
    ) INTO scouts_table_exists;
    
    IF scouts_table_exists THEN
        -- Verificar si tiene columna referral_link_id
        SELECT EXISTS (
            SELECT 1 FROM information_schema.columns
            WHERE table_schema = 'public'
            AND table_name = 'module_ct_scouts_list'
            AND column_name = 'referral_link_id'
        ) INTO referral_column_exists;
        
        IF referral_column_exists THEN
            RAISE NOTICE 'Tabla module_ct_scouts_list existe con referral_link_id';
        ELSE
            RAISE NOTICE 'Tabla module_ct_scouts_list existe pero sin referral_link_id';
        END IF;
    ELSE
        RAISE NOTICE 'Tabla module_ct_scouts_list NO existe';
    END IF;
END $$;

-- ============================================================================
-- PASO 3: Intentar backfill desde referral_link_id (si existe mapping)
-- ============================================================================

-- Este bloque solo se ejecuta si existe la tabla y columna
DO $$
DECLARE
    updated_count INTEGER := 0;
    rec RECORD;
    scout_id_found INTEGER;
BEGIN
    -- Verificar si existe tabla y columna
    IF EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_schema = 'public'
        AND table_name = 'module_ct_scouts_list'
        AND column_name = 'referral_link_id'
    ) THEN
        -- Intentar backfill para eventos con referral_link_id
        FOR rec IN 
            SELECT 
                le.id,
                le.person_key,
                le.source_pk,
                (le.payload_json->>'referral_link_id')::TEXT AS referral_link_id
            FROM observational.lead_events le
            WHERE le.person_key IS NOT NULL
                AND le.scout_id IS NULL
                AND le.payload_json IS NOT NULL
                AND le.payload_json->>'referral_link_id' IS NOT NULL
                AND le.source_table = 'module_ct_cabinet_leads'
        LOOP
            -- Buscar scout_id por referral_link_id
            SELECT s.scout_id INTO scout_id_found
            FROM public.module_ct_scouts_list s
            WHERE s.referral_link_id = rec.referral_link_id
            LIMIT 1;
            
            IF scout_id_found IS NOT NULL THEN
                -- Actualizar evento con scout_id
                UPDATE observational.lead_events
                SET 
                    scout_id = scout_id_found,
                    payload_json = COALESCE(payload_json, '{}'::jsonb) || jsonb_build_object(
                        'scout_id', scout_id_found,
                        'scout_backfilled_from_referral_link', true,
                        'scout_backfill_timestamp', NOW()
                    ),
                    payload_json = payload_json || jsonb_build_object(
                        'scout_backfilled_from_referral_link', true,
                        'scout_backfill_timestamp', NOW()
                    )
                WHERE id = rec.id
                    AND scout_id IS NULL;
                
                IF FOUND THEN
                    updated_count := updated_count + 1;
                END IF;
            END IF;
        END LOOP;
        
        RAISE NOTICE 'Actualizados % eventos con scout_id desde referral_link_id', updated_count;
    ELSE
        RAISE NOTICE 'No se puede hacer backfill: tabla/columna no existe';
    END IF;
END $$;

-- ============================================================================
-- PASO 4: Crear vista de alertas para casos sin solución automática
-- ============================================================================

CREATE OR REPLACE VIEW ops.v_cabinet_leads_missing_scout_alerts AS
SELECT 
    DATE(le.event_date) AS event_date,
    COUNT(*) AS events_count,
    COUNT(DISTINCT le.person_key) AS distinct_persons,
    array_agg(DISTINCT le.source_pk) FILTER (WHERE le.source_pk IS NOT NULL) AS sample_source_pks,
    MIN(le.event_date) AS first_event,
    MAX(le.event_date) AS last_event
FROM observational.lead_events le
WHERE le.person_key IS NOT NULL
    AND le.scout_id IS NULL
    AND (le.payload_json IS NULL OR le.payload_json->>'scout_id' IS NULL)
    AND le.source_table = 'module_ct_cabinet_leads'
GROUP BY DATE(le.event_date)
ORDER BY event_date DESC;

-- ============================================================================
-- RESUMEN
-- ============================================================================

SELECT 
    'RESUMEN EVENTOS SIN SCOUT_ID' AS summary,
    (SELECT COUNT(*) FROM ops.v_events_missing_scout_id) AS total_events_sin_scout,
    (SELECT COUNT(DISTINCT person_key) FROM ops.v_events_missing_scout_id) AS distinct_persons,
    (SELECT COUNT(*) FROM ops.v_cabinet_leads_missing_scout_alerts) AS dias_con_eventos_sin_scout;

-- Distribución por día (últimos 30 días)
SELECT 
    event_date,
    events_count,
    distinct_persons
FROM ops.v_cabinet_leads_missing_scout_alerts
WHERE event_date >= CURRENT_DATE - INTERVAL '30 days'
ORDER BY event_date DESC
LIMIT 30;

