-- ============================================================================
-- Vista Alias: Pagos Yango Raw Current (Alias)
-- ============================================================================
-- Vista alias de ops.v_yango_payments_raw_current para mantener compatibilidad
-- con funciones y scripts que referencian esta vista.
-- ============================================================================

CREATE OR REPLACE VIEW ops.v_yango_payments_raw_current_aliases AS
SELECT * FROM ops.v_yango_payments_raw_current;

COMMENT ON VIEW ops.v_yango_payments_raw_current_aliases IS 
'Vista alias de ops.v_yango_payments_raw_current. Mantiene compatibilidad con funciones y scripts existentes.';
