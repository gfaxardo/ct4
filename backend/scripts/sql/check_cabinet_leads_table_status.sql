-- Script para verificar el estado de la tabla module_ct_cabinet_leads
-- y determinar qué fechas ya están procesadas

-- 1. Verificar si la tabla existe
SELECT 
    EXISTS (
        SELECT 1 FROM information_schema.tables 
        WHERE table_schema = 'public' 
        AND table_name = 'module_ct_cabinet_leads'
    ) AS table_exists;

-- 2. Si existe, contar registros
SELECT COUNT(*) AS total_rows
FROM public.module_ct_cabinet_leads;

-- 3. Fecha máxima en la tabla
SELECT 
    MAX(lead_created_at::date) AS max_lead_date,
    MIN(lead_created_at::date) AS min_lead_date,
    COUNT(DISTINCT external_id) AS unique_external_ids
FROM public.module_ct_cabinet_leads
WHERE lead_created_at IS NOT NULL;

-- 4. Fecha máxima procesada en lead_events (cabinet)
SELECT 
    MAX(event_date) AS max_event_date,
    COUNT(*) AS total_cabinet_events
FROM observational.lead_events
WHERE source_table = 'module_ct_cabinet_leads';

-- 5. Fecha máxima procesada en identity_links (cabinet)
SELECT 
    MAX(snapshot_date::date) AS max_snapshot_date,
    COUNT(DISTINCT source_pk) AS processed_external_ids
FROM canon.identity_links
WHERE source_table = 'module_ct_cabinet_leads';

-- 6. Distribución de fechas en la tabla (últimos 30 días)
SELECT 
    lead_created_at::date AS fecha,
    COUNT(*) AS registros
FROM public.module_ct_cabinet_leads
WHERE lead_created_at IS NOT NULL
GROUP BY lead_created_at::date
ORDER BY fecha DESC
LIMIT 30;

-- 7. Comparación: qué external_ids están en la tabla pero no procesados
SELECT 
    COUNT(DISTINCT m.external_id) AS unprocessed_external_ids
FROM public.module_ct_cabinet_leads m
LEFT JOIN canon.identity_links il 
    ON il.source_table = 'module_ct_cabinet_leads' 
    AND il.source_pk = m.external_id::text
WHERE il.id IS NULL;

