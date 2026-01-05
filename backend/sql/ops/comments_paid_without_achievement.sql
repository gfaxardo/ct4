-- ============================================================================
-- Comentarios SQL: PAID_WITHOUT_ACHIEVEMENT - Comportamiento Esperado
-- ============================================================================
-- PROPÓSITO:
-- Agregar comentarios SQL (solo documentación, cero lógica) para explicar
-- que reconciliation_status = 'PAID_WITHOUT_ACHIEVEMENT' es válido y esperado.
--
-- REFERENCIAS:
-- - Política oficial: docs/policies/ct4_reconciliation_status_policy.md
-- - Runbook operativo: docs/runbooks/paid_without_achievement_expected_behavior.md
-- ============================================================================
-- INSTRUCCIONES DE EJECUCIÓN:
-- 1. Verificar tipo de objeto: ejecutar query de verificación (ver abajo)
-- 2. Ejecutar este script completo en Postgres (read-only, solo COMMENT)
-- 3. Verificar con: \d+ ops.v_cabinet_milestones_reconciled (psql)
-- ============================================================================

-- ============================================================================
-- VERIFICACIÓN: Tipo de objeto (ejecutar primero)
-- ============================================================================
-- Query para confirmar que ops.v_cabinet_milestones_reconciled es VIEW (no MATERIALIZED VIEW):
/*
SELECT 
    n.nspname AS schema_name,
    c.relname AS object_name,
    CASE c.relkind
        WHEN 'v' THEN 'VIEW'
        WHEN 'm' THEN 'MATERIALIZED VIEW'
        WHEN 'r' THEN 'TABLE'
        ELSE 'OTHER'
    END AS object_type
FROM pg_class c
INNER JOIN pg_namespace n ON n.oid = c.relnamespace
WHERE n.nspname = 'ops'
    AND c.relname = 'v_cabinet_milestones_reconciled';
*/
-- Resultado esperado: object_type = 'VIEW'

-- ============================================================================
-- COMENTARIO EN LA VISTA
-- ============================================================================
COMMENT ON VIEW ops.v_cabinet_milestones_reconciled IS 
'Vista de reconciliación que hace JOIN explícito entre ACHIEVED (operativo) y PAID (pagos Yango). Expone reconciliation_status que categoriza cada milestone en 4 estados mutuamente excluyentes: OK, ACHIEVED_NOT_PAID, PAID_WITHOUT_ACHIEVEMENT, NOT_APPLICABLE. Grano: (driver_id, milestone_value). IMPORTANTE: PAID_WITHOUT_ACHIEVEMENT es válido y esperado (no es un bug). Indica que Yango pagó según sus criterios upstream, sin evidencia suficiente en nuestro sistema operativo. Subtipos: UPSTREAM_OVERPAYMENT (~79%) e INSUFFICIENT_TRIPS_CONFIRMED (~21%). Principio: el pasado no se corrige, se explica. NO recalcular milestones históricos ni modificar pagos pasados. Ver: docs/policies/ct4_reconciliation_status_policy.md y docs/runbooks/paid_without_achievement_expected_behavior.md';

-- ============================================================================
-- COMENTARIO EN LA COLUMNA reconciliation_status
-- ============================================================================
COMMENT ON COLUMN ops.v_cabinet_milestones_reconciled.reconciliation_status IS 
'Estado de reconciliación (mutuamente excluyente): OK (alcanzado y pagado), ACHIEVED_NOT_PAID (alcanzado pero no pagado), PAID_WITHOUT_ACHIEVEMENT (pagado pero no alcanzado), NOT_APPLICABLE (ni alcanzado ni pagado - no debería aparecer en producción). IMPORTANTE: PAID_WITHOUT_ACHIEVEMENT es válido y esperado (no es un bug). Yango pagó según sus criterios upstream, sin evidencia suficiente en summary_daily. Subtipos: UPSTREAM_OVERPAYMENT (~79%, lógica propia de Yango) e INSUFFICIENT_TRIPS_CONFIRMED (~21%, trips insuficientes en ventana). Principio: el pasado no se corrige, se explica. NO recalcular milestones históricos, NO modificar reglas pasadas, NO reabrir pagos ya ejecutados. Queries de diagnóstico: fase2_clasificacion_masiva_paid_without_achievement.sql, fase2_diagnostic_paid_without_achievement.sql. Ver: docs/policies/ct4_reconciliation_status_policy.md y docs/runbooks/paid_without_achievement_expected_behavior.md';

