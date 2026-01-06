BEGIN;

-- 0) Seguridad: mostrar conteos actuales
SELECT 'before_scout_total' AS k, COUNT(*) AS v FROM ops.scout_payment_rules;
SELECT 'before_partner_total' AS k, COUNT(*) AS v FROM ops.partner_payment_rules;

-- 1) Insert baseline rules SOLO si las tablas están vacías (idempotente)
DO $$
DECLARE
  scout_cnt INT;
  partner_cnt INT;
BEGIN
  SELECT COUNT(*) INTO scout_cnt FROM ops.scout_payment_rules;
  SELECT COUNT(*) INTO partner_cnt FROM ops.partner_payment_rules;

  IF scout_cnt = 0 THEN
    -- SCOUT - CABINET (7 días) - hitos 1,5,25
    INSERT INTO ops.scout_payment_rules
      (origin_tag, milestone_trips, window_days, amount, currency, valid_from, valid_to, is_active)
    VALUES
      ('cabinet', 1,  7, 0, 'PEN', DATE '2025-11-03', NULL, TRUE),
      ('cabinet', 5,  7, 0, 'PEN', DATE '2025-11-03', NULL, TRUE),
      ('cabinet', 25, 7, 0, 'PEN', DATE '2025-11-03', NULL, TRUE),

      -- SCOUT - FLEET MIGRATION (30 días) - hito 50
      ('fleet_migration', 50, 30, 0, 'PEN', DATE '2025-11-03', NULL, TRUE);
  END IF;

  IF partner_cnt = 0 THEN
    -- PARTNER - (14 días) - hitos 1,5,25 para ambos orígenes
    INSERT INTO ops.partner_payment_rules
      (origin_tag, milestone_trips, window_days, amount, currency, valid_from, valid_to, is_active)
    VALUES
      ('cabinet',        1,  14, 0, 'PEN', DATE '2025-11-03', NULL, TRUE),
      ('cabinet',        5,  14, 0, 'PEN', DATE '2025-11-03', NULL, TRUE),
      ('cabinet',        25, 14, 0, 'PEN', DATE '2025-11-03', NULL, TRUE),
      ('fleet_migration',1,  14, 0, 'PEN', DATE '2025-11-03', NULL, TRUE),
      ('fleet_migration',5,  14, 0, 'PEN', DATE '2025-11-03', NULL, TRUE),
      ('fleet_migration',25, 14, 0, 'PEN', DATE '2025-11-03', NULL, TRUE);
  END IF;
END $$;

-- 2) Verificación: reglas activas
SELECT 'after_scout_active' AS k, COUNT(*) AS v
FROM ops.scout_payment_rules
WHERE is_active = TRUE;

SELECT 'after_partner_active' AS k, COUNT(*) AS v
FROM ops.partner_payment_rules
WHERE is_active = TRUE;

COMMIT;

-- 3) Verificación del desbloqueo: ops.v_payment_calculation debe tener filas
SELECT COUNT(*) AS payment_rows FROM ops.v_payment_calculation;

-- 4) Breakdown mínimo
SELECT rule_scope, origin_tag, COUNT(*) AS n
FROM ops.v_payment_calculation
GROUP BY 1,2
ORDER BY 1,2;

-- 5) Muestra 20 filas
SELECT person_key, origin_tag, rule_scope, rule_id, lead_date,
       window_days, milestone_trips, achieved_trips_in_window AS trips_in_window,
       milestone_achieved, achieved_date, is_payable, payable_date
FROM ops.v_payment_calculation
ORDER BY lead_date DESC
LIMIT 20;

























