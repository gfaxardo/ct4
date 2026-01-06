-- ============================================================================
-- Vista Materializada: ops.mv_payments_driver_matrix_cabinet
-- ============================================================================
-- PROPÓSITO:
-- Vista materializada de ops.v_payments_driver_matrix_cabinet para mejorar
-- significativamente el rendimiento de queries. Esta vista se actualiza
-- periódicamente (recomendado: cada hora o según necesidad operativa).
-- ============================================================================
-- VENTAJAS:
-- 1. Rendimiento: Queries 10-100x más rápidas que la vista normal
-- 2. Índices: Permite crear índices en columnas filtradas frecuentemente
-- 3. Estabilidad: No depende de cálculos en tiempo real
-- ============================================================================
-- REFRESH:
-- - Manual: REFRESH MATERIALIZED VIEW ops.mv_payments_driver_matrix_cabinet;
-- - Automático: Ver script backend/scripts/sql/refresh_mv_driver_matrix.sql
-- ============================================================================
-- NOTA:
-- Esta vista materializada es un COPY de la vista normal. Si la vista normal
-- cambia, esta debe recrearse o refrescarse para mantener consistencia.
-- ============================================================================

-- Configurar timeout más largo para la creación (10 minutos)
SET statement_timeout = '600s';

-- Crear vista materializada
-- NOTA: Si falla por timeout, la vista normal es extremadamente lenta.
-- En ese caso, considerar crear la vista materializada con filtros iniciales
-- o optimizar primero la vista normal.
CREATE MATERIALIZED VIEW IF NOT EXISTS ops.mv_payments_driver_matrix_cabinet AS
SELECT * FROM ops.v_payments_driver_matrix_cabinet;

-- Resetear timeout
RESET statement_timeout;

-- Índices para mejorar rendimiento de queries frecuentes
-- Índice compuesto para filtros comunes: origin_tag + week_start
CREATE INDEX IF NOT EXISTS idx_mv_driver_matrix_origin_week 
ON ops.mv_payments_driver_matrix_cabinet(origin_tag, week_start DESC NULLS LAST);

-- Índice para filtro por funnel_status
CREATE INDEX IF NOT EXISTS idx_mv_driver_matrix_funnel_status 
ON ops.mv_payments_driver_matrix_cabinet(funnel_status) 
WHERE funnel_status IS NOT NULL;

-- Índice para filtro por driver_id (búsquedas específicas)
CREATE INDEX IF NOT EXISTS idx_mv_driver_matrix_driver_id 
ON ops.mv_payments_driver_matrix_cabinet(driver_id);

-- Índice para filtro por lead_date
CREATE INDEX IF NOT EXISTS idx_mv_driver_matrix_lead_date 
ON ops.mv_payments_driver_matrix_cabinet(lead_date DESC NULLS LAST);

-- Índice parcial para only_pending (drivers con milestones pendientes)
CREATE INDEX IF NOT EXISTS idx_mv_driver_matrix_pending 
ON ops.mv_payments_driver_matrix_cabinet(driver_id, week_start DESC) 
WHERE (
    (m1_achieved_flag = true AND (m1_yango_payment_status IS NULL OR m1_yango_payment_status = 'UNPAID'))
    OR (m5_achieved_flag = true AND (m5_yango_payment_status IS NULL OR m5_yango_payment_status = 'UNPAID'))
    OR (m25_achieved_flag = true AND (m25_yango_payment_status IS NULL OR m25_yango_payment_status = 'UNPAID'))
);

-- Índice compuesto para ordenamiento común: week_start + driver_name
CREATE INDEX IF NOT EXISTS idx_mv_driver_matrix_order_week_name 
ON ops.mv_payments_driver_matrix_cabinet(week_start DESC NULLS LAST, driver_name ASC NULLS LAST);

-- Comentarios
COMMENT ON MATERIALIZED VIEW ops.mv_payments_driver_matrix_cabinet IS 
'Vista materializada de ops.v_payments_driver_matrix_cabinet para mejorar rendimiento. Se actualiza periódicamente. Usar REFRESH MATERIALIZED VIEW para actualizar datos.';

