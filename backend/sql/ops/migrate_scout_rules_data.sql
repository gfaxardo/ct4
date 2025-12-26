-- ============================================================================
-- Migración de Datos: Poblar milestone_type y milestone_value desde milestone_trips
-- ============================================================================
-- Paso 2: Migrar datos existentes
-- ============================================================================

BEGIN;

-- Esta migración ya se hizo en migrate_scout_rules_milestone_type.sql
-- Verificar que todos los registros tengan milestone_value poblado
SELECT 
    COUNT(*) AS total_rules,
    COUNT(*) FILTER (WHERE milestone_type = 'trips') AS trips_rules,
    COUNT(*) FILTER (WHERE milestone_type = 'connection') AS connection_rules,
    COUNT(*) FILTER (WHERE milestone_value IS NULL) AS rules_with_null_value,
    COUNT(*) FILTER (WHERE milestone_value > 0) AS rules_with_value
FROM ops.scout_payment_rules;

-- Verificar migración
SELECT 
    COUNT(*) AS total_rules,
    COUNT(*) FILTER (WHERE milestone_type = 'trips') AS trips_rules,
    COUNT(*) FILTER (WHERE milestone_type = 'connection') AS connection_rules,
    COUNT(*) FILTER (WHERE milestone_value > 0) AS rules_with_value
FROM ops.scout_payment_rules;

COMMIT;

