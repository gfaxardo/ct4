-- ============================================================================
-- Seed de Reglas Partner Reales con Vigencia
-- ============================================================================
-- Versiona reglas activas anteriores e inserta nuevas reglas con montos configurados
-- ============================================================================

-- ============================================================================
-- CONFIG: Montos y vigencia (ajustar según necesidades)
-- ============================================================================
-- TODO: Actualizar amounts cuando Gonzalo proporcione montos reales
DO $$
DECLARE
    valid_from_config DATE := DATE '2025-11-01';
    currency_config VARCHAR(3) := 'PEN';
    amount_trip_1 NUMERIC(12, 2) := 0.00;
    amount_trip_5 NUMERIC(12, 2) := 0.00;
    amount_trip_25 NUMERIC(12, 2) := 0.00;
BEGIN
    -- A) Cerrar reglas activas actuales (solo las de window_days=14 y milestone_trips in (1,5,25))
    -- Versionar: 
    --   - Si valid_from < valid_from_config: set valid_to = valid_from_config - 1 day, is_active=false
    --   - Si valid_from >= valid_from_config: solo set is_active=false (ya están en la nueva vigencia)
    UPDATE ops.partner_payment_rules
    SET 
        valid_to = CASE 
            WHEN valid_from < valid_from_config 
            THEN (valid_from_config - INTERVAL '1 day')::date
            ELSE valid_to  -- Mantener valid_to existente si valid_from >= valid_from_config
        END,
        is_active = FALSE,
        updated_at = NOW()
    WHERE is_active = TRUE
      AND window_days = 14
      AND milestone_trips IN (1, 5, 25)
      AND (valid_to IS NULL OR valid_to >= valid_from_config);

    -- B) Actualizar o insertar nuevas reglas (idempotente)
    -- Cabinet: trips 1/5/25 (14d)
    WITH new_rules AS (
        SELECT * FROM (VALUES
            (1, amount_trip_1),
            (5, amount_trip_5),
            (25, amount_trip_25)
        ) AS rules(milestone_trips, amount)
    )
    -- Actualizar reglas existentes
    UPDATE ops.partner_payment_rules ppr
    SET 
        amount = nr.amount,
        currency = currency_config,
        valid_to = NULL,
        is_active = TRUE,
        updated_at = NOW()
    FROM new_rules nr
    WHERE ppr.origin_tag = 'cabinet'
        AND ppr.window_days = 14
        AND ppr.milestone_trips = nr.milestone_trips
        AND ppr.valid_from = valid_from_config;

    -- Insertar reglas nuevas (solo las que no existen)
    WITH new_rules AS (
        SELECT * FROM (VALUES
            (1, amount_trip_1),
            (5, amount_trip_5),
            (25, amount_trip_25)
        ) AS rules(milestone_trips, amount)
    )
    INSERT INTO ops.partner_payment_rules (
        origin_tag,
        window_days,
        milestone_trips,
        amount,
        currency,
        valid_from,
        valid_to,
        is_active
    )
    SELECT 
        'cabinet' AS origin_tag,
        14 AS window_days,
        nr.milestone_trips,
        nr.amount,
        currency_config AS currency,
        valid_from_config AS valid_from,
        NULL AS valid_to,
        TRUE AS is_active
    FROM new_rules nr
    WHERE NOT EXISTS (
        SELECT 1
        FROM ops.partner_payment_rules ppr
        WHERE ppr.origin_tag = 'cabinet'
            AND ppr.window_days = 14
            AND ppr.milestone_trips = nr.milestone_trips
            AND ppr.valid_from = valid_from_config
    );

    -- Fleet Migration: trips 1/5/25 (14d)
    WITH new_rules AS (
        SELECT * FROM (VALUES
            (1, amount_trip_1),
            (5, amount_trip_5),
            (25, amount_trip_25)
        ) AS rules(milestone_trips, amount)
    )
    -- Actualizar reglas existentes
    UPDATE ops.partner_payment_rules ppr
    SET 
        amount = nr.amount,
        currency = currency_config,
        valid_to = NULL,
        is_active = TRUE,
        updated_at = NOW()
    FROM new_rules nr
    WHERE ppr.origin_tag = 'fleet_migration'
        AND ppr.window_days = 14
        AND ppr.milestone_trips = nr.milestone_trips
        AND ppr.valid_from = valid_from_config;

    -- Insertar reglas nuevas (solo las que no existen)
    WITH new_rules AS (
        SELECT * FROM (VALUES
            (1, amount_trip_1),
            (5, amount_trip_5),
            (25, amount_trip_25)
        ) AS rules(milestone_trips, amount)
    )
    INSERT INTO ops.partner_payment_rules (
        origin_tag,
        window_days,
        milestone_trips,
        amount,
        currency,
        valid_from,
        valid_to,
        is_active
    )
    SELECT 
        'fleet_migration' AS origin_tag,
        14 AS window_days,
        nr.milestone_trips,
        nr.amount,
        currency_config AS currency,
        valid_from_config AS valid_from,
        NULL AS valid_to,
        TRUE AS is_active
    FROM new_rules nr
    WHERE NOT EXISTS (
        SELECT 1
        FROM ops.partner_payment_rules ppr
        WHERE ppr.origin_tag = 'fleet_migration'
            AND ppr.window_days = 14
            AND ppr.milestone_trips = nr.milestone_trips
            AND ppr.valid_from = valid_from_config
    );
END $$;

-- ============================================================================
-- VERIFICACIÓN 1: Conteo de reglas activas
-- ============================================================================
SELECT 
    'active_partner_rules' AS metric,
    COUNT(*) AS count
FROM ops.partner_payment_rules
WHERE is_active;

SELECT 
    origin_tag,
    milestone_trips,
    window_days,
    amount,
    currency,
    valid_from,
    valid_to,
    is_active
FROM ops.partner_payment_rules
WHERE is_active
ORDER BY origin_tag, milestone_trips;

