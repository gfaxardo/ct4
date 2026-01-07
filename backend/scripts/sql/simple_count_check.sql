-- Verificación simple: contar registros en cada fuente

-- Registros en module_ct_cabinet_payments desde el 18/12
SELECT 
    COUNT(*) as total_in_raw,
    MIN(date) as min_date,
    MAX(date) as max_date
FROM public.module_ct_cabinet_payments
WHERE date >= '2025-12-18';

-- Registros en yango_payment_status_ledger desde el 18/12
SELECT 
    COUNT(*) as total_in_ledger,
    MIN(pay_date) as min_date,
    MAX(pay_date) as max_date
FROM ops.yango_payment_status_ledger
WHERE pay_date >= '2025-12-18';

-- Verificar si la vista yango_payment_ledger existe y cuántos registros tiene
SELECT 
    COUNT(*) as total_in_view,
    MIN(pay_date) as min_date,
    MAX(pay_date) as max_date
FROM ops.yango_payment_ledger
WHERE pay_date >= '2025-12-18';


