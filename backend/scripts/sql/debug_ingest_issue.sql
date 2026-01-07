-- Debug: Verificar por qué la ingesta no está insertando registros

-- 1. Verificar cuántos registros hay en la vista fuente
SELECT 
    'v_yango_payments_raw_current_aliases' AS source,
    COUNT(*) as total_rows,
    MAX(pay_date) as max_pay_date,
    COUNT(*) FILTER (WHERE pay_date >= '2025-12-18') as rows_since_dec18
FROM ops.v_yango_payments_raw_current_aliases;

-- 2. Verificar cuántos de esos registros YA están en el ledger
-- (comparando por payment_key y state_hash)
SELECT 
    COUNT(*) as already_in_ledger,
    COUNT(*) FILTER (WHERE rc.pay_date >= '2025-12-18') as already_in_ledger_since_dec18
FROM ops.v_yango_payments_raw_current_aliases rc
WHERE EXISTS (
    SELECT 1 
    FROM ops.yango_payment_ledger l 
    WHERE l.payment_key = rc.payment_key
        AND l.state_hash = rc.state_hash
);

-- 3. Verificar cuántos registros NO están en el ledger (deberían insertarse)
SELECT 
    COUNT(*) as should_be_inserted,
    MIN(rc.pay_date) as min_pending_date,
    MAX(rc.pay_date) as max_pending_date
FROM ops.v_yango_payments_raw_current_aliases rc
WHERE NOT EXISTS (
    SELECT 1 
    FROM ops.yango_payment_ledger l 
    WHERE l.payment_key = rc.payment_key
        AND l.state_hash = rc.state_hash
);

-- 4. Muestra algunos registros que deberían insertarse
SELECT 
    rc.source_pk,
    rc.pay_date,
    rc.milestone_value,
    rc.payment_key,
    rc.state_hash,
    rc.driver_id,
    rc.person_key
FROM ops.v_yango_payments_raw_current_aliases rc
WHERE NOT EXISTS (
    SELECT 1 
    FROM ops.yango_payment_ledger l 
    WHERE l.payment_key = rc.payment_key
        AND l.state_hash = rc.state_hash
)
ORDER BY rc.pay_date DESC
LIMIT 10;

-- 5. Verificar si hay registros en el ledger con el mismo payment_key pero diferente state_hash
SELECT 
    COUNT(*) as same_payment_key_different_hash
FROM ops.v_yango_payments_raw_current_aliases rc
WHERE EXISTS (
    SELECT 1 
    FROM ops.yango_payment_ledger l 
    WHERE l.payment_key = rc.payment_key
        AND l.state_hash != rc.state_hash
);

