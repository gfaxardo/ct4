-- ============================================================================
-- Vista Materializada: ops.mv_cabinet_financial_14d
-- ============================================================================
-- PROPÓSITO:
-- Vista materializada de ops.v_cabinet_financial_14d para mejorar el
-- rendimiento de consultas frecuentes. Se debe refrescar periódicamente.
-- ============================================================================
-- USO:
-- - Consultas frecuentes de reportes financieros
-- - Dashboards que requieren datos actualizados periódicamente
-- - Análisis de cobranza que no requieren datos en tiempo real
-- ============================================================================
-- REFRESH:
-- Ejecutar: REFRESH MATERIALIZED VIEW ops.mv_cabinet_financial_14d;
-- Se recomienda refrescar diariamente o después de actualizaciones de claims
-- ============================================================================

DROP MATERIALIZED VIEW IF EXISTS ops.mv_cabinet_financial_14d CASCADE;

CREATE MATERIALIZED VIEW ops.mv_cabinet_financial_14d AS
SELECT * FROM ops.v_cabinet_financial_14d;

-- Índices en la vista materializada para optimizar consultas
CREATE INDEX idx_mv_cabinet_financial_14d_driver_id 
ON ops.mv_cabinet_financial_14d(driver_id);

CREATE INDEX idx_mv_cabinet_financial_14d_lead_date 
ON ops.mv_cabinet_financial_14d(lead_date);

CREATE INDEX idx_mv_cabinet_financial_14d_amount_due 
ON ops.mv_cabinet_financial_14d(amount_due_yango DESC) 
WHERE amount_due_yango > 0;

CREATE INDEX idx_mv_cabinet_financial_14d_expected_total 
ON ops.mv_cabinet_financial_14d(expected_total_yango DESC) 
WHERE expected_total_yango > 0;

-- Comentarios
COMMENT ON MATERIALIZED VIEW ops.mv_cabinet_financial_14d IS 
'Vista materializada de ops.v_cabinet_financial_14d para mejorar rendimiento de consultas frecuentes. Se debe refrescar periódicamente (diariamente recomendado).';

