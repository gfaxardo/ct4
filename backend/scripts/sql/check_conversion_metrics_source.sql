-- Verificar fuente de lead_date en v_conversion_metrics

-- 1. v_conversion_metrics (cabinet) - fecha máxima
SELECT 
    'v_conversion_metrics (cabinet)' as source,
    MAX(lead_date) as max_lead_date,
    COUNT(DISTINCT driver_id) as total_drivers,
    COUNT(DISTINCT driver_id) FILTER (WHERE lead_date >= '2025-12-15') as drivers_since_dec15
FROM observational.v_conversion_metrics
WHERE origin_tag = 'cabinet'
    AND driver_id IS NOT NULL
    AND lead_date IS NOT NULL;

-- 2. Verificar si module_ct_cabinet_leads tiene datos más recientes
SELECT 
    'module_ct_cabinet_leads (RAW)' as source,
    MAX(lead_created_at::date) as max_lead_date,
    COUNT(*) as total_rows,
    COUNT(*) FILTER (WHERE lead_created_at::date >= '2025-12-15') as rows_since_dec15
FROM public.module_ct_cabinet_leads
WHERE lead_created_at IS NOT NULL;


