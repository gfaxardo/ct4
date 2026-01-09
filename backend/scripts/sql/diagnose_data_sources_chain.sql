-- Diagnóstico completo de la cadena de datos para identificar dónde se corta

-- 1. Fuente RAW: module_ct_cabinet_payments (tabla base)
SELECT 
    'module_ct_cabinet_payments (RAW)' as source,
    MAX(date) as max_date,
    MAX(created_at::date) as max_created_at,
    COUNT(*) as total_rows,
    COUNT(*) FILTER (WHERE date >= '2025-12-15') as rows_since_dec15
FROM public.module_ct_cabinet_payments;

-- 2. Ledger: yango_payment_status_ledger (pagos procesados)
SELECT 
    'yango_payment_status_ledger' as source,
    MAX(pay_date) as max_date,
    MAX(created_at::date) as max_created_at,
    COUNT(*) as total_rows,
    COUNT(*) FILTER (WHERE pay_date >= '2025-12-15') as rows_since_dec15
FROM ops.yango_payment_status_ledger;

-- 3. Vista: v_payment_calculation (cabinet)
SELECT 
    'v_payment_calculation (cabinet)' as source,
    MAX(lead_date) as max_date,
    COUNT(DISTINCT driver_id) as total_drivers,
    COUNT(DISTINCT driver_id) FILTER (WHERE lead_date >= '2025-12-15') as drivers_since_dec15
FROM ops.v_payment_calculation
WHERE origin_tag = 'cabinet'
    AND driver_id IS NOT NULL
    AND lead_date IS NOT NULL;

-- 4. Vista: v_conversion_metrics (cabinet)
SELECT 
    'v_conversion_metrics (cabinet)' as source,
    MAX(lead_date) as max_date,
    COUNT(DISTINCT driver_id) as total_drivers,
    COUNT(DISTINCT driver_id) FILTER (WHERE lead_date >= '2025-12-15') as drivers_since_dec15
FROM observational.v_conversion_metrics
WHERE origin_tag = 'cabinet'
    AND driver_id IS NOT NULL
    AND lead_date IS NOT NULL;

-- 5. Vista final: v_cabinet_financial_14d
SELECT 
    'v_cabinet_financial_14d (FINAL)' as source,
    MAX(lead_date) as max_date,
    COUNT(*) as total_drivers,
    COUNT(*) FILTER (WHERE lead_date >= '2025-12-15') as drivers_since_dec15
FROM ops.v_cabinet_financial_14d;



