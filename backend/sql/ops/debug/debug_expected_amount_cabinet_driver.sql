-- ============================================================================
-- DEBUG: expected_total incorrecto en /pagos/claims (Drivers)
-- ============================================================================
-- OBJETIVO: Encontrar por qué un driver muestra expected_total = S/195
-- cuando debería ser máximo S/160 (reglas: milestone 1=25, 5=35, 25=100)
-- ============================================================================
-- INSTRUCCIONES:
-- 1. Reemplazar '<DRIVER_ID_AQUI>' con el driver_id problemático (ej: b264635aea6c41c7b14b481b02d8cb09)
-- 2. Ejecutar queries en orden (A, B, C, D, E)
-- 3. Analizar resultados para identificar causa raíz
-- ============================================================================

-- ============================================================================
-- A) Ver filas base de claims para ese driver (SIN agregación)
-- ============================================================================
-- Objetivo: Ver todas las filas que tiene el driver en la vista base
-- Si hay más de 3 filas (una por milestone 1, 5, 25), hay duplicados
-- ============================================================================
SELECT
  driver_id,
  person_key,
  milestone_value,
  lead_date,
  expected_amount,
  currency,
  lead_date + INTERVAL '14 days' AS due_date,
  payment_status,
  reason_code
FROM ops.v_claims_payment_status_cabinet
WHERE driver_id = '<DRIVER_ID_AQUI>'
ORDER BY lead_date, milestone_value;

-- ============================================================================
-- B) Contar duplicados por claim canónico (driver_id + milestone_value)
-- ============================================================================
-- Objetivo: Identificar si hay múltiples filas para el mismo milestone
-- Si n_rows > 1 para algún milestone, hay duplicados
-- ============================================================================
SELECT
  driver_id,
  milestone_value,
  COUNT(*) AS n_rows,
  SUM(expected_amount) AS sum_amount,
  ARRAY_AGG(DISTINCT lead_date ORDER BY lead_date) AS distinct_lead_dates
FROM ops.v_claims_payment_status_cabinet
WHERE driver_id = '<DRIVER_ID_AQUI>'
GROUP BY driver_id, milestone_value
ORDER BY milestone_value;

-- ============================================================================
-- C) Ver si el monto esperado por milestone coincide con regla (25/35/100)
-- ============================================================================
-- Objetivo: Verificar que expected_amount sea exactamente 25, 35 o 100
-- según milestone_value (1, 5, 25 respectivamente)
-- ============================================================================
SELECT
  milestone_value,
  COUNT(*) AS n_rows,
  MIN(expected_amount) AS min_amt,
  MAX(expected_amount) AS max_amt,
  ARRAY_AGG(DISTINCT expected_amount ORDER BY expected_amount) AS distinct_amts,
  CASE 
    WHEN milestone_value = 1 THEN 25
    WHEN milestone_value = 5 THEN 35
    WHEN milestone_value = 25 THEN 100
    ELSE NULL
  END AS expected_rule_amt
FROM ops.v_claims_payment_status_cabinet
WHERE driver_id = '<DRIVER_ID_AQUI>'
GROUP BY milestone_value
ORDER BY milestone_value;

-- ============================================================================
-- D) Trazar upstream: filas en ops.v_yango_receivable_payable_detail para ese driver
-- ============================================================================
-- Objetivo: Ver los datos upstream antes de llegar a v_claims_payment_status_cabinet
-- Identificar si el problema viene de los datos fuente
-- ============================================================================
SELECT
  driver_id,
  person_key,
  milestone_value,
  lead_origin,
  lead_date,
  amount AS expected_amount,
  currency,
  pay_week_start_monday
FROM ops.v_yango_receivable_payable_detail
WHERE lead_origin = 'cabinet'
  AND milestone_value IN (1, 5, 25)
  AND driver_id = '<DRIVER_ID_AQUI>'
ORDER BY lead_date, milestone_value;

-- ============================================================================
-- E) Si hay duplicados, identificar por qué (mismo driver+milestone con distintas lead_date/pay_week)
-- ============================================================================
-- Objetivo: Analizar patrones de duplicación (mismo milestone, diferentes fechas)
-- ============================================================================
SELECT
  driver_id,
  milestone_value,
  lead_date,
  pay_week_start_monday,
  expected_amount,
  COUNT(*) OVER (PARTITION BY driver_id, milestone_value) AS dup_count,
  ROW_NUMBER() OVER (PARTITION BY driver_id, milestone_value ORDER BY lead_date DESC) AS rn_by_lead_date
FROM ops.v_claims_payment_status_cabinet
WHERE driver_id = '<DRIVER_ID_AQUI>'
ORDER BY milestone_value, lead_date;

-- ============================================================================
-- VALIDACIÓN FINAL: expected_total debe ser <= 160
-- ============================================================================
-- Objetivo: Verificar el total agregado después del fix
-- ============================================================================
SELECT
  SUM(expected_amount) AS expected_total,
  SUM(CASE WHEN milestone_value = 1 THEN expected_amount ELSE 0 END) AS m1_total,
  SUM(CASE WHEN milestone_value = 5 THEN expected_amount ELSE 0 END) AS m5_total,
  SUM(CASE WHEN milestone_value = 25 THEN expected_amount ELSE 0 END) AS m25_total,
  COUNT(DISTINCT milestone_value) AS distinct_milestones,
  COUNT(*) AS total_rows
FROM ops.v_claims_payment_status_cabinet
WHERE driver_id = '<DRIVER_ID_AQUI>';

-- ============================================================================
-- CASOS DE ESTUDIO (driver_ids proporcionados):
-- ============================================================================
-- Oscar Sanabria: b264635aea6c41c7b14b481b02d8cb09
-- Alexander Anaya: 88881990913f4b8181ff342c99635452
-- Prado Wilfredo: 3d809fc2cca64071a46dabe3223e314c
-- ============================================================================



