-- ============================================================================
-- Seed de Reglas Scout Reales con Vigencia
-- ============================================================================
-- Desactiva reglas baseline existentes e inserta nuevas reglas con montos reales
-- ============================================================================

BEGIN;

-- Paso 1: Actualizar reglas existentes o insertar nuevas
-- Para cabinet (window_days=7)
WITH new_rules AS (
    SELECT * FROM (VALUES
        ('connection', 1, 0.00),
        ('trips', 1, 20.00),
        ('trips', 5, 25.00),
        ('trips', 25, 55.00)
    ) AS rules(milestone_type, milestone_value, amount)
)
-- Actualizar reglas existentes
UPDATE ops.scout_payment_rules spr
SET 
    amount = nr.amount,
    is_active = true,
    updated_at = NOW()
FROM new_rules nr
WHERE spr.origin_tag = 'cabinet'
    AND spr.window_days = 7
    AND spr.milestone_type = nr.milestone_type
    AND spr.milestone_value = nr.milestone_value
    AND spr.valid_from = DATE '2025-11-03';

-- Insertar reglas nuevas (solo las que no existen)
WITH new_rules AS (
    SELECT * FROM (VALUES
        ('connection', 1, 0.00),
        ('trips', 1, 20.00),
        ('trips', 5, 25.00),
        ('trips', 25, 55.00)
    ) AS rules(milestone_type, milestone_value, amount)
)
INSERT INTO ops.scout_payment_rules (
    origin_tag,
    window_days,
    milestone_type,
    milestone_value,
    milestone_trips,
    amount,
    currency,
    valid_from,
    valid_to,
    is_active
)
SELECT 
    'cabinet' AS origin_tag,
    7 AS window_days,
    nr.milestone_type,
    nr.milestone_value,
    CASE WHEN nr.milestone_type = 'trips' THEN nr.milestone_value ELSE 1 END AS milestone_trips,
    nr.amount,
    'PEN' AS currency,
    DATE '2025-11-03' AS valid_from,
    NULL AS valid_to,
    true AS is_active
FROM new_rules nr
WHERE NOT EXISTS (
    SELECT 1
    FROM ops.scout_payment_rules spr
    WHERE spr.origin_tag = 'cabinet'
        AND spr.window_days = 7
        AND spr.milestone_type = nr.milestone_type
        AND spr.milestone_value = nr.milestone_value
        AND spr.valid_from = DATE '2025-11-03'
);

-- Para fleet_migration (window_days=7 según especificación)
WITH new_rules AS (
    SELECT * FROM (VALUES
        ('connection', 1, 0.00),
        ('trips', 50, 50.00)
    ) AS rules(milestone_type, milestone_value, amount)
)
-- Actualizar reglas existentes (ajustar window_days de 30 a 7 si es necesario)
UPDATE ops.scout_payment_rules spr
SET 
    window_days = 7,
    amount = nr.amount,
    is_active = true,
    updated_at = NOW()
FROM new_rules nr
WHERE spr.origin_tag = 'fleet_migration'
    AND spr.milestone_type = nr.milestone_type
    AND spr.milestone_value = nr.milestone_value
    AND spr.valid_from = DATE '2025-11-03';

-- Insertar reglas nuevas (solo las que no existen)
WITH new_rules AS (
    SELECT * FROM (VALUES
        ('connection', 1, 0.00),
        ('trips', 50, 50.00)
    ) AS rules(milestone_type, milestone_value, amount)
)
INSERT INTO ops.scout_payment_rules (
    origin_tag,
    window_days,
    milestone_type,
    milestone_value,
    milestone_trips,
    amount,
    currency,
    valid_from,
    valid_to,
    is_active
)
SELECT 
    'fleet_migration' AS origin_tag,
    7 AS window_days,
    nr.milestone_type,
    nr.milestone_value,
    CASE WHEN nr.milestone_type = 'trips' THEN nr.milestone_value ELSE 1 END AS milestone_trips,
    nr.amount,
    'PEN' AS currency,
    DATE '2025-11-03' AS valid_from,
    NULL AS valid_to,
    true AS is_active
FROM new_rules nr
WHERE NOT EXISTS (
    SELECT 1
    FROM ops.scout_payment_rules spr
    WHERE spr.origin_tag = 'fleet_migration'
        AND spr.window_days = 7
        AND spr.milestone_type = nr.milestone_type
        AND spr.milestone_value = nr.milestone_value
        AND spr.valid_from = DATE '2025-11-03'
);

-- Reporte de reglas activas después del seed
SELECT 
    'active_scout_rules' AS metric,
    COUNT(*) AS count
FROM ops.scout_payment_rules
WHERE is_active = true;

SELECT 
    origin_tag,
    window_days,
    milestone_type,
    milestone_value,
    amount,
    currency
FROM ops.scout_payment_rules
WHERE is_active = true
ORDER BY origin_tag, milestone_type, milestone_value;

COMMIT;

