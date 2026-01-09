-- Verificar que el ledger se actualizó correctamente

-- Fecha máxima ahora en el ledger
SELECT 
    'yango_payment_status_ledger' AS source,
    MAX(pay_date) as max_pay_date,
    MAX(snapshot_at) as max_snapshot_at,
    COUNT(*) as total_rows,
    COUNT(*) FILTER (WHERE pay_date >= '2025-12-18') as rows_since_dec18
FROM ops.yango_payment_status_ledger;

-- Comparar con la fuente RAW
SELECT 
    'module_ct_cabinet_payments (RAW)' AS source,
    MAX(date) as max_date,
    MAX(created_at) as max_created_at,
    COUNT(*) as total_rows,
    COUNT(*) FILTER (WHERE date >= '2025-12-18') as rows_since_dec18
FROM public.module_ct_cabinet_payments;

-- Verificar si todavía hay registros pendientes
SELECT 
    COUNT(*) as still_pending
FROM ops.v_yango_payments_raw_current_aliases rc
WHERE NOT EXISTS (
    SELECT 1 
    FROM ops.yango_payment_status_ledger l 
    WHERE l.payment_key = rc.payment_key
        AND l.state_hash = rc.state_hash
);



