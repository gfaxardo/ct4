-- ============================================================================
-- Verificación de Comentarios SQL: PAID_WITHOUT_ACHIEVEMENT
-- ============================================================================
-- PROPÓSITO:
-- Verificar que los comentarios SQL se aplicaron correctamente sobre:
-- - ops.v_cabinet_milestones_reconciled (vista)
-- - ops.v_cabinet_milestones_reconciled.reconciliation_status (columna)
-- ============================================================================
-- INSTRUCCIONES:
-- Ejecutar estos queries en Postgres (read-only, no modifican nada)
-- ============================================================================

-- Query 1: Ver comentario de la vista
SELECT 
    obj_description(
        'ops.v_cabinet_milestones_reconciled'::regclass,
        'pg_class'
    ) AS view_comment;

-- Query 2: Ver comentario de la columna reconciliation_status
SELECT 
    col_description(
        'ops.v_cabinet_milestones_reconciled'::regclass,
        attnum
    ) AS column_comment
FROM pg_attribute
WHERE attrelid = 'ops.v_cabinet_milestones_reconciled'::regclass
  AND attname = 'reconciliation_status';

-- ============================================================================
-- INTERPRETACIÓN:
-- - Si view_comment es NULL: El comentario de la vista NO está presente
-- - Si column_comment es NULL: El comentario de la columna NO está presente
-- - Si ambos son NOT NULL: Comentarios correctamente persistidos
-- ============================================================================





