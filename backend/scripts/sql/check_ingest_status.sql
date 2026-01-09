-- Verificar estado de la ingesta
-- Comparar fechas máximas entre fuente RAW y ledger

-- Fecha máxima en la fuente RAW (module_ct_cabinet_payments)
SELECT 
    'module_ct_cabinet_payments (RAW)' AS source,
    MAX(date) as max_business_date,
    MAX(created_at) as max_ingestion_ts,
    COUNT(*) as total_rows
FROM public.module_ct_cabinet_payments
WHERE date IS NOT NULL;

-- Fecha máxima en el ledger procesado
SELECT 
    'yango_payment_ledger (PROCESSED)' AS source,
    MAX(pay_date) as max_business_date,
    MAX(snapshot_at) as max_ingestion_ts,
    COUNT(*) as total_rows
FROM ops.yango_payment_ledger
WHERE pay_date IS NOT NULL;

-- Registros en RAW que no están en el ledger (últimos 30 días)
SELECT 
    COUNT(*) as pending_to_ingest
FROM public.module_ct_cabinet_payments p
WHERE p.date >= CURRENT_DATE - INTERVAL '30 days'
    AND NOT EXISTS (
        SELECT 1 
        FROM ops.yango_payment_ledger l 
        WHERE l.source_pk = p.id::text
            AND l.pay_date = p.date
    );



