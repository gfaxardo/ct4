-- Test directo: verificar si hay registros que deberían insertarse

-- 1. Contar registros en la vista fuente que NO están en el ledger
-- (usando payment_key y state_hash como en la función)
SELECT 
    COUNT(*) as should_insert,
    MIN(rc.pay_date) as min_date,
    MAX(rc.pay_date) as max_date
FROM ops.v_yango_payments_raw_current_aliases rc
WHERE NOT EXISTS (
    SELECT 1 
    FROM ops.yango_payment_status_ledger l 
    WHERE l.payment_key = rc.payment_key
        AND l.state_hash = rc.state_hash
);

-- 2. Si hay registros pendientes, mostrar algunos ejemplos
SELECT 
    rc.source_pk,
    rc.pay_date,
    rc.milestone_value,
    rc.payment_key,
    rc.state_hash,
    rc.driver_name_normalized
FROM ops.v_yango_payments_raw_current_aliases rc
WHERE NOT EXISTS (
    SELECT 1 
    FROM ops.yango_payment_status_ledger l 
    WHERE l.payment_key = rc.payment_key
        AND l.state_hash = rc.state_hash
)
ORDER BY rc.pay_date DESC
LIMIT 5;

-- 3. Verificar si hay registros en module_ct_cabinet_payments que no generan filas en la vista
SELECT 
    COUNT(*) as raw_without_view_rows
FROM public.module_ct_cabinet_payments p
WHERE p.date >= '2025-12-18'
    AND NOT EXISTS (
        SELECT 1 
        FROM ops.v_yango_payments_raw_current_aliases v
        WHERE v.source_pk::integer = p.id
    );

