-- ============================================================================
-- Vista: ops.v_payments_driver_matrix_cabinet (ENRIQUECIDA CON SCOUT)
-- ============================================================================
-- CAMBIOS: Agregado scout attribution (scout_id, scout_name, scout_quality_bucket)
-- ============================================================================
-- NOTA: Este script debe aplicarse SOBRE el script original
-- Buscar la sección "driver_milestones AS" y agregar los JOINs y columnas
-- ============================================================================

-- IMPORTANTE: Este es un PATCH, no un script completo
-- Se debe aplicar manualmente al archivo original v_payments_driver_matrix_cabinet.sql

-- PASO 1: En el CTE "driver_milestones AS", después del último LEFT JOIN (antes de GROUP BY),
-- agregar:
LEFT JOIN ops.v_scout_attribution sa
    ON (sa.person_key = COALESCE(ca.person_key, ocd.person_key) 
        AND COALESCE(ca.person_key, ocd.person_key) IS NOT NULL)
    OR (sa.driver_id = COALESCE(ca.driver_id, dma.driver_id, ocd.driver_id) 
        AND COALESCE(ca.person_key, ocd.person_key) IS NULL 
        AND sa.person_key IS NULL)
LEFT JOIN ops.v_dim_scouts ds
    ON ds.scout_id = sa.scout_id

-- PASO 2: En el SELECT del CTE "driver_milestones", después de las columnas de milestone_inconsistency_notes
-- y antes de "FROM deterministic_milestones_agg dma", agregar:
-- Scout attribution
sa.scout_id,
ds.raw_name AS scout_name,
CASE 
    WHEN sa.source_table = 'observational.lead_ledger' THEN 'SATISFACTORY_LEDGER'
    WHEN sa.source_table = 'observational.lead_events' THEN 'EVENTS_ONLY'
    WHEN sa.source_table = 'public.module_ct_migrations' THEN 'MIGRATIONS_ONLY'
    WHEN sa.source_table = 'public.module_ct_scouting_daily' OR sa.source_table = 'module_ct_scouting_daily' THEN 'SCOUTING_DAILY_ONLY'
    WHEN sa.source_table = 'public.module_ct_cabinet_payments' THEN 'CABINET_PAYMENTS_ONLY'
    WHEN sa.scout_id IS NOT NULL THEN 'SCOUTING_DAILY_ONLY'
    ELSE 'MISSING'
END AS scout_quality_bucket,
CASE WHEN sa.scout_id IS NOT NULL THEN true ELSE false END AS is_scout_resolved

-- PASO 3: En el SELECT final (después de "FROM driver_milestones"), agregar las columnas:
-- Scout attribution
scout_id,
scout_name,
scout_quality_bucket,
is_scout_resolved

-- PASO 4: Agregar comentarios para las nuevas columnas (al final del archivo):
COMMENT ON COLUMN ops.v_payments_driver_matrix_cabinet.scout_id IS 
'Scout ID asignado al driver. Fuente canónica: ops.v_scout_attribution (agrega múltiples fuentes con prioridad).';

COMMENT ON COLUMN ops.v_payments_driver_matrix_cabinet.scout_name IS 
'Nombre del scout desde module_ct_scouts_list (raw_name).';

COMMENT ON COLUMN ops.v_payments_driver_matrix_cabinet.scout_quality_bucket IS 
'Calidad de la atribución scout basada en la fuente: SATISFACTORY_LEDGER (lead_ledger), EVENTS_ONLY, MIGRATIONS_ONLY, SCOUTING_DAILY_ONLY, CABINET_PAYMENTS_ONLY, MISSING.';

COMMENT ON COLUMN ops.v_payments_driver_matrix_cabinet.is_scout_resolved IS 
'Flag indicando si el scout está resuelto (true si hay scout_id de cualquier fuente, false si no).';
