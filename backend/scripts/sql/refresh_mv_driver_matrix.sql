-- ============================================================================
-- Script: Refresh Vista Materializada Driver Matrix
-- ============================================================================
-- PROPÓSITO:
-- Refrescar la vista materializada ops.mv_payments_driver_matrix_cabinet
-- para mantener los datos actualizados.
-- ============================================================================
-- USO:
-- - Manual: psql $DATABASE_URL -f backend/scripts/sql/refresh_mv_driver_matrix.sql
-- - Automático: Configurar cron job o scheduler para ejecutar periódicamente
-- ============================================================================
-- FRECUENCIA RECOMENDADA:
-- - Producción: Cada hora (o según necesidad operativa)
-- - Desarrollo: Según necesidad
-- ============================================================================
-- NOTA:
-- El refresh puede tardar varios minutos dependiendo del tamaño de los datos.
-- Durante el refresh, la vista materializada sigue disponible con datos antiguos.
-- ============================================================================

-- Configurar timeout más largo para el refresh (5 minutos)
SET statement_timeout = '300s';

-- Log inicio
DO $$
BEGIN
    RAISE NOTICE 'Iniciando refresh de ops.mv_payments_driver_matrix_cabinet a las %', NOW();
END $$;

-- Refrescar vista materializada
-- CONCURRENTLY permite queries durante el refresh, pero requiere índices únicos
-- Si no hay índices únicos, usar REFRESH sin CONCURRENTLY
BEGIN;

-- Intentar refresh CONCURRENTLY (más seguro, permite queries durante refresh)
-- Si falla, usar refresh normal
DO $$
BEGIN
    REFRESH MATERIALIZED VIEW CONCURRENTLY ops.mv_payments_driver_matrix_cabinet;
    RAISE NOTICE 'Refresh CONCURRENTLY completado exitosamente';
EXCEPTION
    WHEN OTHERS THEN
        RAISE WARNING 'Refresh CONCURRENTLY falló: %. Intentando refresh normal...', SQLERRM;
        REFRESH MATERIALIZED VIEW ops.mv_payments_driver_matrix_cabinet;
        RAISE NOTICE 'Refresh normal completado exitosamente';
END $$;

COMMIT;

-- Log fin
DO $$
BEGIN
    RAISE NOTICE 'Refresh de ops.mv_payments_driver_matrix_cabinet completado a las %', NOW();
END $$;

-- Resetear timeout
RESET statement_timeout;

