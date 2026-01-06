-- ============================================================================
-- Script: Crear Índices para Optimizar Driver Matrix
-- ============================================================================
-- PROPÓSITO:
-- Crear índices en tablas base (NO vistas) para mejorar el rendimiento
-- de las vistas dependientes que alimentan v_payments_driver_matrix_cabinet.
-- ============================================================================
-- NOTA:
-- No se pueden crear índices directamente en vistas, solo en tablas/materializadas.
-- Este script solo crea índices en tablas reales.
-- ============================================================================

-- Índices en public.drivers (tabla real)
-- driver_id para joins (probablemente ya existe, pero asegurarse)
CREATE INDEX IF NOT EXISTS idx_drivers_driver_id 
ON public.drivers(driver_id) 
WHERE driver_id IS NOT NULL;

-- Índices en public.summary_daily (tabla real, usada por múltiples vistas)
-- driver_id + date_file para filtros y joins
CREATE INDEX IF NOT EXISTS idx_summary_daily_driver_date 
ON public.summary_daily(driver_id, date_file) 
WHERE driver_id IS NOT NULL AND date_file IS NOT NULL;

-- date_file para filtros de fecha
CREATE INDEX IF NOT EXISTS idx_summary_daily_date_file 
ON public.summary_daily(date_file) 
WHERE date_file IS NOT NULL;

-- count_orders_completed para filtros de viajes
CREATE INDEX IF NOT EXISTS idx_summary_daily_trips 
ON public.summary_daily(driver_id, count_orders_completed) 
WHERE driver_id IS NOT NULL AND count_orders_completed > 0;

-- Comentarios (sintaxis correcta sin IF EXISTS)
DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM pg_indexes WHERE indexname = 'idx_drivers_driver_id') THEN
        COMMENT ON INDEX idx_drivers_driver_id IS 
        'Índice para optimizar joins por driver_id en public.drivers';
    END IF;
    
    IF EXISTS (SELECT 1 FROM pg_indexes WHERE indexname = 'idx_summary_daily_driver_date') THEN
        COMMENT ON INDEX idx_summary_daily_driver_date IS 
        'Índice para optimizar joins y filtros por driver_id + date_file en public.summary_daily';
    END IF;
    
    IF EXISTS (SELECT 1 FROM pg_indexes WHERE indexname = 'idx_summary_daily_date_file') THEN
        COMMENT ON INDEX idx_summary_daily_date_file IS 
        'Índice para optimizar filtros por date_file en public.summary_daily';
    END IF;
    
    IF EXISTS (SELECT 1 FROM pg_indexes WHERE indexname = 'idx_summary_daily_trips') THEN
        COMMENT ON INDEX idx_summary_daily_trips IS 
        'Índice para optimizar filtros por viajes completados en public.summary_daily';
    END IF;
END $$;
