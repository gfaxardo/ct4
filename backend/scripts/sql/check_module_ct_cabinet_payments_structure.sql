-- Verificar estructura de module_ct_cabinet_payments
SELECT 
    column_name, 
    data_type,
    is_nullable
FROM information_schema.columns 
WHERE table_schema = 'public' 
    AND table_name = 'module_ct_cabinet_payments' 
ORDER BY ordinal_position;

-- Verificar fechas máximas en module_ct_cabinet_payments
SELECT 
    MAX(date) as max_date, 
    MAX(created_at) as max_created_at, 
    MAX(updated_at) as max_updated_at,
    COUNT(*) as total_rows
FROM public.module_ct_cabinet_payments;

-- Verificar fechas máximas en yango_payment_ledger
SELECT 
    MAX(pay_date) as max_pay_date, 
    MAX(snapshot_at) as max_snapshot_at, 
    COUNT(*) as total_rows
FROM ops.yango_payment_ledger;

-- Verificar última ejecución de ingest_yango_payments_snapshot
SELECT 
    MAX(snapshot_at) as last_snapshot_at,
    COUNT(*) as total_snapshots
FROM ops.yango_payment_ledger;



