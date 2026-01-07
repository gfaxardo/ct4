-- ============================================================================
-- FASE 1: Comentarios SQL para Vistas que Mezclan Conceptos
-- ============================================================================
-- PROPÓSITO:
-- Agregar comentarios SQL claros en vistas existentes que mezclan ACHIEVED y PAID,
-- sin modificar la lógica existente. Solo agregar claridad semántica.
--
-- REGLAS:
-- - SOLO agregar comentarios (COMMENT ON VIEW / COMMENT ON COLUMN)
-- - NO modificar lógica SQL
-- - NO agregar columnas nuevas
-- - Mantener compatibilidad hacia atrás
-- ============================================================================

-- ============================================================================
-- 1. ops.v_claims_payment_status_cabinet
-- ============================================================================
-- NOTA: Esta vista MEZCLA ACHIEVED (desde v_payment_calculation) con PAID (desde ledger).
-- Se mantiene por compatibilidad, pero para nueva lógica usar las vistas separadas:
-- - ops.v_cabinet_milestones_achieved (solo ACHIEVED)
-- - ops.v_cabinet_milestones_paid (solo PAID)
-- - ops.v_cabinet_milestones_reconciled (JOIN explícito)

COMMENT ON VIEW ops.v_claims_payment_status_cabinet IS 
'Vista orientada a cobranza que MEZCLA ACHIEVED (milestones logrados) con PAID (pagos reconocidos). Fuentes: ops.v_payment_calculation (ACHIEVED) + ops.v_yango_payments_ledger_latest_enriched (PAID). NOTA: Para nueva lógica, preferir las vistas separadas: v_cabinet_milestones_achieved, v_cabinet_milestones_paid, v_cabinet_milestones_reconciled.';

-- El campo milestone_value viene de ACHIEVED
COMMENT ON COLUMN ops.v_claims_payment_status_cabinet.milestone_value IS 
'Valor del milestone alcanzado (1, 5, o 25). Fuente: ops.v_payment_calculation (ACHIEVED). NOTA: Este campo representa el milestone logrado, no el pagado.';

-- El campo paid_flag viene de PAID
COMMENT ON COLUMN ops.v_claims_payment_status_cabinet.paid_flag IS 
'Flag indicando si el claim tiene al menos un pago asociado. Fuente: ops.v_yango_payments_ledger_latest_enriched (PAID). NOTA: Este campo representa el pago reconocido, no el milestone logrado.';

-- ============================================================================
-- 2. ops.v_payments_driver_matrix_cabinet
-- ============================================================================
-- NOTA: Esta vista usa campos que se llaman "achieved_flag" pero vienen de
-- v_claims_payment_status_cabinet que mezcla ACHIEVED + PAID. El nombre es ambiguo.

-- Agregar comentario en la vista principal
COMMENT ON VIEW ops.v_payments_driver_matrix_cabinet IS 
'Vista de PRESENTACIÓN (no recalcula reglas) que muestra 1 fila por driver con columnas por milestones M1/M5/M25 y estados Yango/Scout. NOTA IMPORTANTE: Los campos m1_achieved_flag, m5_achieved_flag, m25_achieved_flag provienen de ops.v_claims_payment_status_cabinet que MEZCLA ACHIEVED (logrado) con PAID (pagado). El nombre "achieved_flag" es ambiguo. Para nueva lógica, preferir las vistas separadas: v_cabinet_milestones_achieved, v_cabinet_milestones_paid, v_cabinet_milestones_reconciled.';

-- Comentarios en campos específicos que son ambiguos
COMMENT ON COLUMN ops.v_payments_driver_matrix_cabinet.m1_achieved_flag IS 
'Flag indicando si el driver alcanzó M1 según ops.v_claims_payment_status_cabinet. NOTA: Este campo viene de una vista que mezcla ACHIEVED (logrado) con PAID (pagado). El nombre "achieved_flag" es ambiguo. Para milestones puramente logrados, usar ops.v_cabinet_milestones_achieved. Para milestones pagados, usar ops.v_cabinet_milestones_paid.';

COMMENT ON COLUMN ops.v_payments_driver_matrix_cabinet.m5_achieved_flag IS 
'Flag indicando si el driver alcanzó M5 según ops.v_claims_payment_status_cabinet. NOTA: Este campo viene de una vista que mezcla ACHIEVED (logrado) con PAID (pagado). El nombre "achieved_flag" es ambiguo. Para milestones puramente logrados, usar ops.v_cabinet_milestones_achieved. Para milestones pagados, usar ops.v_cabinet_milestones_paid.';

COMMENT ON COLUMN ops.v_payments_driver_matrix_cabinet.m25_achieved_flag IS 
'Flag indicando si el driver alcanzó M25 según ops.v_claims_payment_status_cabinet. NOTA: Este campo viene de una vista que mezcla ACHIEVED (logrado) con PAID (pagado). El nombre "achieved_flag" es ambiguo. Para milestones puramente logrados, usar ops.v_cabinet_milestones_achieved. Para milestones pagados, usar ops.v_cabinet_milestones_paid.';

COMMENT ON COLUMN ops.v_payments_driver_matrix_cabinet.m1_yango_payment_status IS 
'Estado de pago Yango para M1: PAID, PAID_MISAPPLIED, UNPAID. Fuente: ops.v_yango_cabinet_claims_for_collection. NOTA: Este campo representa el pago reconocido, no el milestone logrado.';

COMMENT ON COLUMN ops.v_payments_driver_matrix_cabinet.m5_yango_payment_status IS 
'Estado de pago Yango para M5: PAID, PAID_MISAPPLIED, UNPAID. Fuente: ops.v_yango_cabinet_claims_for_collection. NOTA: Este campo representa el pago reconocido, no el milestone logrado.';

COMMENT ON COLUMN ops.v_payments_driver_matrix_cabinet.m25_yango_payment_status IS 
'Estado de pago Yango para M25: PAID, PAID_MISAPPLIED, UNPAID. Fuente: ops.v_yango_cabinet_claims_for_collection. NOTA: Este campo representa el pago reconocido, no el milestone logrado.';

-- ============================================================================
-- 3. ops.v_yango_cabinet_claims_for_collection
-- ============================================================================
-- NOTA: Esta vista está basada en v_claims_payment_status_cabinet que mezcla conceptos.

COMMENT ON VIEW ops.v_yango_cabinet_claims_for_collection IS 
'Vista FINAL y cobrable para Yango Cabinet. Indica qué Yango debe pagar (UNPAID), qué ya pagó (PAID) y qué pagó mal (PAID_MISAPPLIED). NOTA: Esta vista está basada en ops.v_claims_payment_status_cabinet que MEZCLA ACHIEVED (logrado) con PAID (pagado). El campo yango_payment_status representa el pago reconocido. Para nueva lógica de reconciliación, considerar usar ops.v_cabinet_milestones_reconciled.';

COMMENT ON COLUMN ops.v_yango_cabinet_claims_for_collection.yango_payment_status IS 
'Estado canónico del pago para Yango: PAID (pagado correctamente), PAID_MISAPPLIED (pagó pero a otro milestone), UNPAID (no pagado). NOTA: Este campo representa el pago reconocido, no el milestone logrado. Para milestones logrados, usar ops.v_cabinet_milestones_achieved.';

-- ============================================================================
-- FIN DE COMENTARIOS
-- ============================================================================








