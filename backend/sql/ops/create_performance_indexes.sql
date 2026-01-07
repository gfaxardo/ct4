-- ============================================================================
-- Script para crear índices que optimizan el rendimiento de las vistas
-- de claims cabinet
-- ============================================================================
-- NOTA: Estos índices deben crearse en las tablas base, no en las vistas.
-- Ejecutar este script puede tomar varios minutos dependiendo del tamaño
-- de las tablas.
-- ============================================================================

-- 1. Índice para optimizar búsquedas por driver_id + milestone_value + is_paid
--    en ops.yango_payments_ledger (si existe como tabla física)
--    NOTA: Verificar primero si la tabla existe antes de crear el índice
DO $$
BEGIN
    IF EXISTS (
        SELECT 1 
        FROM information_schema.tables 
        WHERE table_schema = 'ops' 
        AND table_name = 'yango_payments_ledger'
    ) THEN
        CREATE INDEX IF NOT EXISTS idx_yango_payments_ledger_driver_milestone_paid 
            ON ops.yango_payments_ledger(driver_id, milestone_value, is_paid) 
            WHERE is_paid = true;
        
        RAISE NOTICE 'Indice idx_yango_payments_ledger_driver_milestone_paid creado';
    ELSE
        RAISE NOTICE 'Tabla ops.yango_payments_ledger no existe, saltando indice';
    END IF;
END $$;

-- 2. Índice para optimizar búsquedas por person_key + milestone_value + is_paid
DO $$
BEGIN
    IF EXISTS (
        SELECT 1 
        FROM information_schema.tables 
        WHERE table_schema = 'ops' 
        AND table_name = 'yango_payments_ledger'
    ) THEN
        CREATE INDEX IF NOT EXISTS idx_yango_payments_ledger_person_milestone_paid 
            ON ops.yango_payments_ledger(person_key, milestone_value, is_paid) 
            WHERE is_paid = true AND person_key IS NOT NULL;
        
        RAISE NOTICE 'Indice idx_yango_payments_ledger_person_milestone_paid creado';
    ELSE
        RAISE NOTICE 'Tabla ops.yango_payments_ledger no existe, saltando indice';
    END IF;
END $$;

-- 3. Índice para optimizar búsquedas por payment_key (usado en JOINs)
DO $$
BEGIN
    IF EXISTS (
        SELECT 1 
        FROM information_schema.tables 
        WHERE table_schema = 'ops' 
        AND table_name = 'yango_payments_ledger'
    ) THEN
        CREATE INDEX IF NOT EXISTS idx_yango_payments_ledger_payment_key 
            ON ops.yango_payments_ledger(payment_key);
        
        RAISE NOTICE 'Indice idx_yango_payments_ledger_payment_key creado';
    ELSE
        RAISE NOTICE 'Tabla ops.yango_payments_ledger no existe, saltando indice';
    END IF;
END $$;

-- 4. Índice en public.drivers para optimizar JOINs
CREATE INDEX IF NOT EXISTS idx_drivers_driver_id 
    ON public.drivers(driver_id);

-- 5. Verificar índices creados
SELECT 
    schemaname,
    tablename,
    indexname,
    indexdef
FROM pg_indexes
WHERE schemaname IN ('ops', 'public')
    AND (
        tablename LIKE '%yango_payments%'
        OR (tablename = 'drivers' AND indexname = 'idx_drivers_driver_id')
    )
ORDER BY tablename, indexname;















