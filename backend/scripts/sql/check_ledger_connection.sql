-- Verificar conexión entre yango_payment_status_ledger y yango_payment_ledger

-- 1. Verificar si ops.yango_payment_ledger es una vista o tabla
SELECT 
    table_type,
    table_name
FROM information_schema.tables
WHERE table_schema = 'ops'
    AND table_name IN ('yango_payment_ledger', 'yango_payment_status_ledger');

-- 2. Si es una vista, ver su definición
SELECT 
    view_definition
FROM information_schema.views
WHERE table_schema = 'ops'
    AND table_name = 'yango_payment_ledger';

-- 3. Verificar fechas máximas en ambas
SELECT 
    'yango_payment_status_ledger (TABLA REAL)' AS source,
    MAX(pay_date) as max_pay_date,
    MAX(snapshot_at) as max_snapshot_at,
    COUNT(*) as total_rows
FROM ops.yango_payment_status_ledger;

SELECT 
    'yango_payment_ledger (VISTA/ALIAS)' AS source,
    MAX(pay_date) as max_pay_date,
    MAX(snapshot_at) as max_snapshot_at,
    COUNT(*) as total_rows
FROM ops.yango_payment_ledger;

-- 4. Verificar cuántos registros hay en payment_status_ledger desde el 18/12
SELECT 
    COUNT(*) as total_since_dec18,
    MIN(pay_date) as min_date,
    MAX(pay_date) as max_date
FROM ops.yango_payment_status_ledger
WHERE pay_date >= '2025-12-18';


