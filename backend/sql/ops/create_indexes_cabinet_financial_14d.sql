-- ============================================================================
-- Índices para optimizar ops.v_cabinet_financial_14d
-- ============================================================================
-- PROPÓSITO:
-- Crear índices en las tablas base para mejorar el rendimiento de las
-- consultas de la vista ops.v_cabinet_financial_14d
-- ============================================================================
-- NOTA:
-- observational.v_conversion_metrics es una vista, por lo que los índices
-- deben crearse en las tablas base que la componen. Estos índices ya deberían
-- existir si la vista está bien optimizada.
-- ============================================================================

-- Índices en public.summary_daily (ya deberían existir, pero verificamos)
-- Estos índices son críticos para el rendimiento de la vista

-- Índice compuesto para joins y filtros por driver_id + fecha
CREATE INDEX IF NOT EXISTS idx_summary_daily_driver_date 
ON public.summary_daily(driver_id, date_file) 
WHERE driver_id IS NOT NULL AND date_file IS NOT NULL;

-- Índice para filtros por fecha
CREATE INDEX IF NOT EXISTS idx_summary_daily_date_file 
ON public.summary_daily(date_file) 
WHERE date_file IS NOT NULL;

-- Índice para filtros por viajes completados
CREATE INDEX IF NOT EXISTS idx_summary_daily_trips 
ON public.summary_daily(driver_id, count_orders_completed) 
WHERE driver_id IS NOT NULL AND count_orders_completed > 0;

-- Índices en ops.v_claims_payment_status_cabinet
-- Nota: Esta es una vista, por lo que los índices deben crearse en las
-- tablas base que la componen. Si existe una vista materializada asociada,
-- los índices se crearán en la vista materializada.

-- Comentarios (solo si los índices existen)
DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM pg_indexes WHERE indexname = 'idx_summary_daily_driver_date') THEN
        EXECUTE 'COMMENT ON INDEX idx_summary_daily_driver_date IS ''Índice para optimizar joins y filtros por driver_id + date_file en summary_daily.''';
    END IF;
    
    IF EXISTS (SELECT 1 FROM pg_indexes WHERE indexname = 'idx_summary_daily_date_file') THEN
        EXECUTE 'COMMENT ON INDEX idx_summary_daily_date_file IS ''Índice para optimizar filtros por date_file en summary_daily.''';
    END IF;
    
    IF EXISTS (SELECT 1 FROM pg_indexes WHERE indexname = 'idx_summary_daily_trips') THEN
        EXECUTE 'COMMENT ON INDEX idx_summary_daily_trips IS ''Índice para optimizar filtros por viajes completados en summary_daily.''';
    END IF;
END $$;

