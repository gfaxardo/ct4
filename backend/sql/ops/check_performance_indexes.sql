-- ============================================================================
-- Script para verificar índices y proponer optimizaciones de rendimiento
-- ============================================================================

-- 1. Verificar índices en ops.yango_payments_ledger (tabla base)
SELECT 
    schemaname,
    tablename,
    indexname,
    indexdef
FROM pg_indexes
WHERE schemaname = 'ops'
    AND tablename LIKE '%yango_payments%'
ORDER BY tablename, indexname;

-- 2. Verificar índices en public.drivers
SELECT 
    schemaname,
    tablename,
    indexname,
    indexdef
FROM pg_indexes
WHERE schemaname = 'public'
    AND tablename = 'drivers'
ORDER BY indexname;

-- 3. Verificar tamaño de las tablas/vistas
SELECT 
    schemaname,
    tablename,
    pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) AS size
FROM pg_tables
WHERE schemaname IN ('ops', 'public')
    AND tablename LIKE '%yango%'
ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC;

-- 4. Proponer índices para optimizar los JOINs
-- Estos índices deberían crearse en las tablas base si no existen:

-- Para ops.yango_payments_ledger (si existe como tabla):
-- CREATE INDEX IF NOT EXISTS idx_yango_payments_ledger_driver_milestone_paid 
--     ON ops.yango_payments_ledger(driver_id, milestone_value, is_paid) 
--     WHERE is_paid = true;
--
-- CREATE INDEX IF NOT EXISTS idx_yango_payments_ledger_person_milestone_paid 
--     ON ops.yango_payments_ledger(person_key, milestone_value, is_paid) 
--     WHERE is_paid = true AND person_key IS NOT NULL;

-- Para public.drivers:
-- CREATE INDEX IF NOT EXISTS idx_drivers_driver_id 
--     ON public.drivers(driver_id);









