-- Verificar nombres de tablas relacionadas con yango payments

-- Verificar si existe ops.yango_payment_ledger
SELECT 
    'ops.yango_payment_ledger' AS table_name,
    EXISTS (
        SELECT 1 
        FROM information_schema.tables 
        WHERE table_schema = 'ops' 
            AND table_name = 'yango_payment_ledger'
    ) AS exists;

-- Verificar si existe ops.yango_payment_status_ledger
SELECT 
    'ops.yango_payment_status_ledger' AS table_name,
    EXISTS (
        SELECT 1 
        FROM information_schema.tables 
        WHERE table_schema = 'ops' 
            AND table_name = 'yango_payment_status_ledger'
    ) AS exists;

-- Verificar fechas máximas en cada tabla (si existen)
SELECT 
    'yango_payment_ledger' AS table_name,
    MAX(pay_date) as max_pay_date,
    MAX(snapshot_at) as max_snapshot_at,
    COUNT(*) as total_rows
FROM ops.yango_payment_ledger
WHERE EXISTS (
    SELECT 1 
    FROM information_schema.tables 
    WHERE table_schema = 'ops' 
        AND table_name = 'yango_payment_ledger'
);

SELECT 
    'yango_payment_status_ledger' AS table_name,
    MAX(pay_date) as max_pay_date,
    MAX(snapshot_at) as max_snapshot_at,
    COUNT(*) as total_rows
FROM ops.yango_payment_status_ledger
WHERE EXISTS (
    SELECT 1 
    FROM information_schema.tables 
    WHERE table_schema = 'ops' 
        AND table_name = 'yango_payment_status_ledger'
);



