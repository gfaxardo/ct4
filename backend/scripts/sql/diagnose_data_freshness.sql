-- ============================================================================
-- Diagnóstico: ¿Por qué los datos solo llegan hasta el 14/12/2025?
-- ============================================================================
-- Verifica:
-- 1. Fechas más recientes en tablas fuente (scouting_daily, cabinet_leads)
-- 2. Fechas más recientes en lead_events
-- 3. Fechas más recientes en v_conversion_metrics
-- 4. Fechas más recientes en v_cabinet_financial_14d
-- 5. Estado de ingestion_runs recientes
-- ============================================================================

-- 1. Fechas más recientes en tablas fuente
SELECT 
    '1. TABLAS FUENTE' AS section,
    'module_ct_scouting_daily' AS source,
    MAX(registration_date::date) AS max_date,
    COUNT(*) FILTER (WHERE registration_date::date >= '2025-12-14') AS records_since_14dec
FROM public.module_ct_scouting_daily;

-- 2. Fechas más recientes en lead_events (cabinet)
SELECT 
    '2. LEAD_EVENTS' AS section,
    'lead_events (cabinet)' AS source,
    MAX(event_date) AS max_date,
    COUNT(*) FILTER (WHERE event_date >= '2025-12-14') AS records_since_14dec,
    COUNT(*) FILTER (WHERE payload_json->>'origin_tag' = 'cabinet' AND event_date >= '2025-12-14') AS cabinet_records_since_14dec
FROM observational.lead_events
WHERE payload_json->>'origin_tag' = 'cabinet';

-- 3. Fechas más recientes en v_conversion_metrics (cabinet)
SELECT 
    '3. CONVERSION_METRICS' AS section,
    'v_conversion_metrics (cabinet)' AS source,
    MAX(lead_date) AS max_date,
    COUNT(*) FILTER (WHERE lead_date >= '2025-12-14') AS records_since_14dec
FROM observational.v_conversion_metrics
WHERE origin_tag = 'cabinet'
    AND driver_id IS NOT NULL;

-- 4. Fechas más recientes en v_cabinet_financial_14d
SELECT 
    '4. FINANCIAL_14D' AS section,
    'v_cabinet_financial_14d' AS source,
    MAX(lead_date) AS max_date,
    COUNT(*) FILTER (WHERE lead_date >= '2025-12-14') AS records_since_14dec
FROM ops.v_cabinet_financial_14d;

-- 5. Estado de ingestion_runs recientes (últimas 10)
SELECT 
    '5. INGESTION_RUNS' AS section,
    id AS run_id,
    started_at,
    completed_at,
    status,
    scope_date_from,
    scope_date_to,
    stats->>'processed' AS processed,
    stats->>'matched' AS matched,
    error_message
FROM ops.ingestion_runs
ORDER BY started_at DESC
LIMIT 10;

-- 6. Verificar si hay eventos de scouting_daily sin procesar (últimos 30 días)
SELECT 
    '6. SCOUTING_DAILY SIN PROCESAR' AS section,
    COUNT(*) AS unprocessed_count,
    MIN(registration_date::date) AS min_date,
    MAX(registration_date::date) AS max_date
FROM public.module_ct_scouting_daily sd
WHERE registration_date::date >= CURRENT_DATE - INTERVAL '30 days'
    AND NOT EXISTS (
        SELECT 1
        FROM observational.lead_events le
        WHERE le.source_table = 'module_ct_scouting_daily'
            AND le.source_pk = (
                sd.scout_id::text || '|' || 
                COALESCE(sd.driver_phone, '') || '|' || 
                COALESCE(sd.driver_license, '') || '|' || 
                COALESCE(sd.registration_date::text, '')
            )
    );

-- 7. Verificar si hay eventos de cabinet_leads sin procesar (últimos 30 días)
-- NOTA: module_ct_cabinet_leads puede no existir, verificar primero
-- SELECT 
--     '7. CABINET_LEADS SIN PROCESAR' AS section,
--     COUNT(*) AS unprocessed_count,
--     MIN(lead_created_at::date) AS min_date,
--     MAX(lead_created_at::date) AS max_date
-- FROM public.module_ct_cabinet_leads cl
-- WHERE lead_created_at::date >= CURRENT_DATE - INTERVAL '30 days'
--     AND NOT EXISTS (
--         SELECT 1
--         FROM observational.lead_events le
--         WHERE le.source_table = 'module_ct_cabinet_leads'
--             AND le.source_pk = COALESCE(cl.external_id, cl.id::text)
--     );

