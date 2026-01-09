-- Verificar el gap entre module_ct_cabinet_payments y yango_payment_ledger

-- 1. Fechas máximas en cada fuente
SELECT 
    'module_ct_cabinet_payments (RAW)' AS source,
    MAX(date) as max_business_date,
    MAX(created_at) as max_ingestion_ts,
    COUNT(*) as total_rows,
    COUNT(*) FILTER (WHERE date >= '2025-12-18') as rows_since_dec18
FROM public.module_ct_cabinet_payments
WHERE date IS NOT NULL;

SELECT 
    'yango_payment_ledger (PROCESSED)' AS source,
    MAX(pay_date) as max_business_date,
    MAX(snapshot_at) as max_ingestion_ts,
    COUNT(*) as total_rows,
    COUNT(*) FILTER (WHERE pay_date >= '2025-12-18') as rows_since_dec18
FROM ops.yango_payment_ledger
WHERE pay_date IS NOT NULL;

-- 2. Registros en RAW desde el 18/12 que NO están en el ledger
-- (comparando por source_pk y pay_date)
SELECT 
    COUNT(*) as pending_to_ingest,
    MIN(p.date) as min_pending_date,
    MAX(p.date) as max_pending_date
FROM public.module_ct_cabinet_payments p
WHERE p.date >= '2025-12-18'
    AND NOT EXISTS (
        SELECT 1 
        FROM ops.yango_payment_ledger l 
        WHERE l.source_pk = p.id::text
            AND l.pay_date = p.date
    );

-- 3. Muestra algunos registros pendientes de ingesta
SELECT 
    p.id,
    p.date,
    p.driver,
    p.trip_1,
    p.trip_5,
    p.trip_25,
    p.created_at
FROM public.module_ct_cabinet_payments p
WHERE p.date >= '2025-12-18'
    AND NOT EXISTS (
        SELECT 1 
        FROM ops.yango_payment_ledger l 
        WHERE l.source_pk = p.id::text
            AND l.pay_date = p.date
    )
ORDER BY p.date DESC, p.id DESC
LIMIT 10;

-- 4. Verificar si la vista v_yango_payments_raw_current_aliases tiene datos
SELECT 
    COUNT(*) as total_rows_in_view,
    MAX(pay_date) as max_pay_date,
    COUNT(*) FILTER (WHERE pay_date >= '2025-12-18') as rows_since_dec18
FROM ops.v_yango_payments_raw_current_aliases;

-- 5. Verificar registros en la vista que no están en el ledger
SELECT 
    COUNT(*) as pending_from_view,
    MIN(rc.pay_date) as min_pending_date,
    MAX(rc.pay_date) as max_pending_date
FROM ops.v_yango_payments_raw_current_aliases rc
WHERE rc.pay_date >= '2025-12-18'
    AND NOT EXISTS (
        SELECT 1 
        FROM ops.yango_payment_ledger l 
        WHERE l.payment_key = rc.payment_key
            AND l.state_hash = rc.state_hash
    );



