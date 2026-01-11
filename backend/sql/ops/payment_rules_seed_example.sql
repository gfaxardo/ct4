-- Seeds de Ejemplo para Reglas de Pago (Paso 7)
-- Este archivo contiene ejemplos de INSERTs para poblar las tablas de reglas de pago
-- IMPORTANTE: Los montos son placeholders (0 o 1) y deben ser reemplazados con valores reales

-- ============================================================================
-- REGLAS PARA PARTNERS (Yango→Yego)
-- ============================================================================

-- Regla para cabinet, ventana 14 días, milestone 1 viaje
INSERT INTO ops.partner_payment_rules (
    origin_tag, window_days, milestone_trips, amount, currency, 
    valid_from, valid_to, is_active, notes
) VALUES (
    'cabinet', 14, 1, 1.00, 'PEN',
    '2024-01-01'::DATE, NULL, true,
    'Ejemplo: Pago por primer viaje en ventana de 14 días para leads de cabinet'
) ON CONFLICT (origin_tag, window_days, milestone_trips, valid_from) DO NOTHING;

-- Regla para cabinet, ventana 14 días, milestone 5 viajes
INSERT INTO ops.partner_payment_rules (
    origin_tag, window_days, milestone_trips, amount, currency, 
    valid_from, valid_to, is_active, notes
) VALUES (
    'cabinet', 14, 5, 1.00, 'PEN',
    '2024-01-01'::DATE, NULL, true,
    'Ejemplo: Pago por alcanzar 5 viajes en ventana de 14 días para leads de cabinet'
) ON CONFLICT (origin_tag, window_days, milestone_trips, valid_from) DO NOTHING;

-- Regla para cabinet, ventana 14 días, milestone 25 viajes
INSERT INTO ops.partner_payment_rules (
    origin_tag, window_days, milestone_trips, amount, currency, 
    valid_from, valid_to, is_active, notes
) VALUES (
    'cabinet', 14, 25, 1.00, 'PEN',
    '2024-01-01'::DATE, NULL, true,
    'Ejemplo: Pago por alcanzar 25 viajes en ventana de 14 días para leads de cabinet'
) ON CONFLICT (origin_tag, window_days, milestone_trips, valid_from) DO NOTHING;

-- ============================================================================
-- REGLAS PARA SCOUTS (Yego→Scouts) - Cabinet
-- ============================================================================

-- Regla para cabinet, ventana 7 días, milestone 1 viaje
INSERT INTO ops.scout_payment_rules (
    origin_tag, window_days, milestone_trips, amount, currency, 
    valid_from, valid_to, is_active, notes
) VALUES (
    'cabinet', 7, 1, 1.00, 'PEN',
    '2024-01-01'::DATE, NULL, true,
    'Ejemplo: Pago a scout por primer viaje en ventana de 7 días para leads de cabinet'
) ON CONFLICT (origin_tag, window_days, milestone_trips, valid_from) DO NOTHING;

-- Regla para cabinet, ventana 7 días, milestone 5 viajes
INSERT INTO ops.scout_payment_rules (
    origin_tag, window_days, milestone_trips, amount, currency, 
    valid_from, valid_to, is_active, notes
) VALUES (
    'cabinet', 7, 5, 1.00, 'PEN',
    '2024-01-01'::DATE, NULL, true,
    'Ejemplo: Pago a scout por alcanzar 5 viajes en ventana de 7 días para leads de cabinet'
) ON CONFLICT (origin_tag, window_days, milestone_trips, valid_from) DO NOTHING;

-- Regla para cabinet, ventana 7 días, milestone 25 viajes
INSERT INTO ops.scout_payment_rules (
    origin_tag, window_days, milestone_trips, amount, currency, 
    valid_from, valid_to, is_active, notes
) VALUES (
    'cabinet', 7, 25, 1.00, 'PEN',
    '2024-01-01'::DATE, NULL, true,
    'Ejemplo: Pago a scout por alcanzar 25 viajes en ventana de 7 días para leads de cabinet'
) ON CONFLICT (origin_tag, window_days, milestone_trips, valid_from) DO NOTHING;

-- ============================================================================
-- REGLAS PARA SCOUTS (Yego→Scouts) - Fleet Migration
-- ============================================================================

-- Regla para fleet_migration, ventana 30 días, milestone 50 viajes
INSERT INTO ops.scout_payment_rules (
    origin_tag, window_days, milestone_trips, amount, currency, 
    valid_from, valid_to, is_active, notes
) VALUES (
    'fleet_migration', 30, 50, 1.00, 'PEN',
    '2024-01-01'::DATE, NULL, true,
    'Ejemplo: Pago a scout por alcanzar 50 viajes en ventana de 30 días para migraciones de fleet'
) ON CONFLICT (origin_tag, window_days, milestone_trips, valid_from) DO NOTHING;

-- ============================================================================
-- VERIFICACIÓN POST-INSERT
-- ============================================================================

-- Verificar que los inserts funcionaron correctamente
SELECT 
    'partner_payment_rules' as table_name,
    COUNT(*) as total_records,
    COUNT(DISTINCT origin_tag) as distinct_origins,
    COUNT(DISTINCT window_days) as distinct_windows,
    COUNT(DISTINCT milestone_trips) as distinct_milestones
FROM ops.partner_payment_rules
UNION ALL
SELECT 
    'scout_payment_rules' as table_name,
    COUNT(*) as total_records,
    COUNT(DISTINCT origin_tag) as distinct_origins,
    COUNT(DISTINCT window_days) as distinct_windows,
    COUNT(DISTINCT milestone_trips) as distinct_milestones
FROM ops.scout_payment_rules;







