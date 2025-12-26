-- ============================================================================
-- Migración: Agregar milestone_type y milestone_value a scout_payment_rules
-- ============================================================================
-- Paso 1: Agregar nuevas columnas
-- ============================================================================

BEGIN;

-- Agregar milestone_type con valor por defecto 'trips'
ALTER TABLE ops.scout_payment_rules
ADD COLUMN IF NOT EXISTS milestone_type TEXT NOT NULL DEFAULT 'trips';

-- Agregar milestone_value con valor por defecto 0 (temporalmente nullable para migración)
ALTER TABLE ops.scout_payment_rules
ADD COLUMN IF NOT EXISTS milestone_value INTEGER;

-- Migrar datos ANTES de agregar constraint NOT NULL
UPDATE ops.scout_payment_rules
SET milestone_value = milestone_trips
WHERE milestone_value IS NULL;

-- Ahora hacer NOT NULL
ALTER TABLE ops.scout_payment_rules
ALTER COLUMN milestone_value SET NOT NULL;

-- Y agregar default 0 para futuras inserciones
ALTER TABLE ops.scout_payment_rules
ALTER COLUMN milestone_value SET DEFAULT 0;

-- Eliminar constraints si existen antes de agregar
ALTER TABLE ops.scout_payment_rules
DROP CONSTRAINT IF EXISTS chk_scout_milestone_type;

ALTER TABLE ops.scout_payment_rules
DROP CONSTRAINT IF EXISTS chk_scout_milestone_value;

-- Agregar constraint para milestone_type
ALTER TABLE ops.scout_payment_rules
ADD CONSTRAINT chk_scout_milestone_type 
CHECK (milestone_type IN ('trips', 'connection'));

-- Agregar constraint para milestone_value
ALTER TABLE ops.scout_payment_rules
ADD CONSTRAINT chk_scout_milestone_value 
CHECK (
    (milestone_type = 'trips' AND milestone_value > 0) OR
    (milestone_type = 'connection' AND milestone_value >= 0)
);

-- Actualizar unique constraint para incluir milestone_type y milestone_value
-- Primero eliminar constraint antiguo
ALTER TABLE ops.scout_payment_rules
DROP CONSTRAINT IF EXISTS uq_scout_payment_rule;

-- Crear nuevo constraint con milestone_type y milestone_value
ALTER TABLE ops.scout_payment_rules
ADD CONSTRAINT uq_scout_payment_rule 
UNIQUE (origin_tag, window_days, milestone_type, milestone_value, valid_from);

COMMENT ON COLUMN ops.scout_payment_rules.milestone_type IS 
'Tipo de milestone: trips (viajes completados) o connection (primera conexión). Default: trips (legacy).';

COMMENT ON COLUMN ops.scout_payment_rules.milestone_value IS 
'Valor del milestone: para trips es el número de viajes (1,5,25,50), para connection generalmente es 1.';

COMMENT ON COLUMN ops.scout_payment_rules.milestone_trips IS 
'[DEPRECATED/LEGACY] Usar milestone_value cuando milestone_type=trips. Se mantiene por compatibilidad.';

COMMIT;

