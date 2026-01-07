-- Verificar cadena completa: lead_events -> v_conversion_metrics -> v_payment_calculation -> v_cabinet_financial_14d

-- 1. lead_events (fuente base) - eventos de cabinet
SELECT 
    'lead_events (cabinet)' as source,
    MAX(event_date) as max_event_date,
    COUNT(DISTINCT person_key) as total_persons,
    COUNT(DISTINCT person_key) FILTER (WHERE event_date >= '2025-12-15') as persons_since_dec15
FROM observational.lead_events
WHERE payload_json->>'origin_tag' = 'cabinet'
    OR source_table IN ('module_ct_cabinet_leads', 'module_ct_scouting_daily');

-- 2. v_conversion_metrics (cabinet) - fecha máxima
SELECT 
    'v_conversion_metrics (cabinet)' as source,
    MAX(lead_date) as max_lead_date,
    COUNT(DISTINCT driver_id) as total_drivers,
    COUNT(DISTINCT driver_id) FILTER (WHERE lead_date >= '2025-12-15') as drivers_since_dec15
FROM observational.v_conversion_metrics
WHERE origin_tag = 'cabinet'
    AND driver_id IS NOT NULL
    AND lead_date IS NOT NULL;

-- 3. v_payment_calculation (cabinet) - fecha máxima
SELECT 
    'v_payment_calculation (cabinet)' as source,
    MAX(lead_date) as max_lead_date,
    COUNT(DISTINCT driver_id) as total_drivers,
    COUNT(DISTINCT driver_id) FILTER (WHERE lead_date >= '2025-12-15') as drivers_since_dec15
FROM ops.v_payment_calculation
WHERE origin_tag = 'cabinet'
    AND driver_id IS NOT NULL
    AND lead_date IS NOT NULL;

-- 4. v_cabinet_financial_14d (FINAL) - fecha máxima
SELECT 
    'v_cabinet_financial_14d (FINAL)' as source,
    MAX(lead_date) as max_lead_date,
    COUNT(*) as total_drivers,
    COUNT(*) FILTER (WHERE lead_date >= '2025-12-15') as drivers_since_dec15
FROM ops.v_cabinet_financial_14d;

