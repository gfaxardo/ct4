-- ============================================================================
-- Script de Ejecución: Comentarios PAID_WITHOUT_ACHIEVEMENT
-- ============================================================================
-- Este script verifica que el objeto sea VIEW y luego ejecuta los COMMENT ON
-- ============================================================================

-- PASO 1: Verificar tipo de objeto
DO $$
DECLARE
    object_type text;
BEGIN
    SELECT 
        CASE c.relkind
            WHEN 'v' THEN 'VIEW'
            WHEN 'm' THEN 'MATERIALIZED VIEW'
            WHEN 'r' THEN 'TABLE'
            ELSE 'OTHER'
        END
    INTO object_type
    FROM pg_class c
    INNER JOIN pg_namespace n ON n.oid = c.relnamespace
    WHERE n.nspname = 'ops'
        AND c.relname = 'v_cabinet_milestones_reconciled';
    
    IF object_type IS NULL THEN
        RAISE EXCEPTION 'El objeto ops.v_cabinet_milestones_reconciled no existe';
    ELSIF object_type != 'VIEW' THEN
        RAISE EXCEPTION 'El objeto ops.v_cabinet_milestones_reconciled es % (no es VIEW). Deteniendo ejecución.', object_type;
    ELSE
        RAISE NOTICE 'Verificación OK: ops.v_cabinet_milestones_reconciled es VIEW';
    END IF;
END $$;

-- PASO 2: Ejecutar COMMENT ON VIEW
COMMENT ON VIEW ops.v_cabinet_milestones_reconciled IS 
'Vista de reconciliación que hace JOIN explícito entre ACHIEVED (operativo) y PAID (pagos Yango). Expone reconciliation_status que categoriza cada milestone en 4 estados mutuamente excluyentes: OK, ACHIEVED_NOT_PAID, PAID_WITHOUT_ACHIEVEMENT, NOT_APPLICABLE. Grano: (driver_id, milestone_value). IMPORTANTE: PAID_WITHOUT_ACHIEVEMENT es válido y esperado (no es un bug). Indica que Yango pagó según sus criterios upstream, sin evidencia suficiente en nuestro sistema operativo. Subtipos: UPSTREAM_OVERPAYMENT (~79%) e INSUFFICIENT_TRIPS_CONFIRMED (~21%). Principio: el pasado no se corrige, se explica. NO recalcular milestones históricos ni modificar pagos pasados. Ver: docs/policies/ct4_reconciliation_status_policy.md y docs/runbooks/paid_without_achievement_expected_behavior.md';

-- PASO 3: Ejecutar COMMENT ON COLUMN
COMMENT ON COLUMN ops.v_cabinet_milestones_reconciled.reconciliation_status IS 
'Estado de reconciliación (mutuamente excluyente): OK (alcanzado y pagado), ACHIEVED_NOT_PAID (alcanzado pero no pagado), PAID_WITHOUT_ACHIEVEMENT (pagado pero no alcanzado), NOT_APPLICABLE (ni alcanzado ni pagado - no debería aparecer en producción). IMPORTANTE: PAID_WITHOUT_ACHIEVEMENT es válido y esperado (no es un bug). Yango pagó según sus criterios upstream, sin evidencia suficiente en summary_daily. Subtipos: UPSTREAM_OVERPAYMENT (~79%, lógica propia de Yango) e INSUFFICIENT_TRIPS_CONFIRMED (~21%, trips insuficientes en ventana). Principio: el pasado no se corrige, se explica. NO recalcular milestones históricos, NO modificar reglas pasadas, NO reabrir pagos ya ejecutados. Queries de diagnóstico: fase2_clasificacion_masiva_paid_without_achievement.sql, fase2_diagnostic_paid_without_achievement.sql. Ver: docs/policies/ct4_reconciliation_status_policy.md y docs/runbooks/paid_without_achievement_expected_behavior.md';

-- Confirmación
DO $$
BEGIN
    RAISE NOTICE 'COMMENT ON ejecutado correctamente sobre VIEW ops.v_cabinet_milestones_reconciled';
END $$;




