-- ============================================================================
-- Script de Verificación: ops.v_cabinet_financial_14d
-- ============================================================================
-- PROPÓSITO:
-- Verificar la integridad de la vista canónica financiera cabinet_financial_14d
-- mediante checks que detectan inconsistencias entre viajes, milestones y claims.
-- ============================================================================
-- CHECKS:
-- 1. Drivers con viajes >= hito sin claim
-- 2. Drivers con claim sin cumplir viajes
-- 3. Total esperado vs total pagado
-- ============================================================================

-- ============================================================================
-- CHECK 1: Drivers con viajes >= hito sin claim
-- ============================================================================
-- Detecta drivers que alcanzaron milestones dentro de la ventana de 14 días
-- pero no tienen claim registrado en v_claims_payment_status_cabinet
-- ============================================================================

SELECT 
    'CHECK_1: Drivers con viajes >= hito sin claim' AS check_name,
    COUNT(*) AS drivers_affected,
    SUM(CASE WHEN reached_m1_14d = true AND claim_m1_exists = false THEN 1 ELSE 0 END) AS m1_without_claim,
    SUM(CASE WHEN reached_m5_14d = true AND claim_m5_exists = false THEN 1 ELSE 0 END) AS m5_without_claim,
    SUM(CASE WHEN reached_m25_14d = true AND claim_m25_exists = false THEN 1 ELSE 0 END) AS m25_without_claim,
    SUM(expected_total_yango) AS total_expected_missing_claims
FROM ops.v_cabinet_financial_14d
WHERE (reached_m1_14d = true AND claim_m1_exists = false)
    OR (reached_m5_14d = true AND claim_m5_exists = false)
    OR (reached_m25_14d = true AND claim_m25_exists = false);

-- Detalle de drivers con viajes >= hito sin claim
SELECT 
    'CHECK_1_DETAIL: Drivers con viajes >= hito sin claim' AS check_name,
    driver_id,
    lead_date,
    total_trips_14d,
    reached_m1_14d,
    reached_m5_14d,
    reached_m25_14d,
    expected_total_yango,
    claim_m1_exists,
    claim_m5_exists,
    claim_m25_exists,
    CASE 
        WHEN reached_m1_14d = true AND claim_m1_exists = false THEN 'M1 sin claim'
        WHEN reached_m5_14d = true AND claim_m5_exists = false THEN 'M5 sin claim'
        WHEN reached_m25_14d = true AND claim_m25_exists = false THEN 'M25 sin claim'
        ELSE 'OK'
    END AS issue_description
FROM ops.v_cabinet_financial_14d
WHERE (reached_m1_14d = true AND claim_m1_exists = false)
    OR (reached_m5_14d = true AND claim_m5_exists = false)
    OR (reached_m25_14d = true AND claim_m25_exists = false)
ORDER BY expected_total_yango DESC, driver_id
LIMIT 100;

-- ============================================================================
-- CHECK 2: Drivers con claim sin cumplir viajes
-- ============================================================================
-- Detecta drivers que tienen claim registrado pero no alcanzaron el milestone
-- dentro de la ventana de 14 días según summary_daily
-- ============================================================================

SELECT 
    'CHECK_2: Drivers con claim sin cumplir viajes' AS check_name,
    COUNT(*) AS drivers_affected,
    SUM(CASE WHEN claim_m1_exists = true AND reached_m1_14d = false THEN 1 ELSE 0 END) AS m1_claim_without_trips,
    SUM(CASE WHEN claim_m5_exists = true AND reached_m5_14d = false THEN 1 ELSE 0 END) AS m5_claim_without_trips,
    SUM(CASE WHEN claim_m25_exists = true AND reached_m25_14d = false THEN 1 ELSE 0 END) AS m25_claim_without_trips,
    SUM(CASE 
        WHEN claim_m1_exists = true AND reached_m1_14d = false THEN expected_amount_m1
        WHEN claim_m5_exists = true AND reached_m5_14d = false THEN expected_amount_m5
        WHEN claim_m25_exists = true AND reached_m25_14d = false THEN expected_amount_m25
        ELSE 0
    END) AS total_expected_claims_without_trips
FROM ops.v_cabinet_financial_14d
WHERE (claim_m1_exists = true AND reached_m1_14d = false)
    OR (claim_m5_exists = true AND reached_m5_14d = false)
    OR (claim_m25_exists = true AND reached_m25_14d = false);

-- Detalle de drivers con claim sin cumplir viajes
SELECT 
    'CHECK_2_DETAIL: Drivers con claim sin cumplir viajes' AS check_name,
    driver_id,
    lead_date,
    total_trips_14d,
    reached_m1_14d,
    reached_m5_14d,
    reached_m25_14d,
    claim_m1_exists,
    claim_m5_exists,
    claim_m25_exists,
    expected_total_yango,
    CASE 
        WHEN claim_m1_exists = true AND reached_m1_14d = false THEN 'M1 claim sin viajes'
        WHEN claim_m5_exists = true AND reached_m5_14d = false THEN 'M5 claim sin viajes'
        WHEN claim_m25_exists = true AND reached_m25_14d = false THEN 'M25 claim sin viajes'
        ELSE 'OK'
    END AS issue_description
FROM ops.v_cabinet_financial_14d
WHERE (claim_m1_exists = true AND reached_m1_14d = false)
    OR (claim_m5_exists = true AND reached_m5_14d = false)
    OR (claim_m25_exists = true AND reached_m25_14d = false)
ORDER BY expected_total_yango DESC, driver_id
LIMIT 100;

-- ============================================================================
-- CHECK 3: Total esperado vs total pagado
-- ============================================================================
-- Compara el total esperado (basado en viajes) vs el total pagado (basado en claims)
-- para detectar discrepancias financieras
-- ============================================================================

SELECT 
    'CHECK_3: Total esperado vs total pagado' AS check_name,
    COUNT(*) AS total_drivers,
    COUNT(CASE WHEN expected_total_yango > 0 THEN 1 END) AS drivers_with_expected,
    COUNT(CASE WHEN total_paid_yango > 0 THEN 1 END) AS drivers_with_paid,
    COUNT(CASE WHEN amount_due_yango > 0 THEN 1 END) AS drivers_with_debt,
    SUM(expected_total_yango) AS total_expected_all_drivers,
    SUM(total_paid_yango) AS total_paid_all_drivers,
    SUM(amount_due_yango) AS total_due_yango,
    -- Discrepancia: diferencia entre esperado y pagado
    SUM(expected_total_yango - total_paid_yango) AS total_discrepancy
FROM ops.v_cabinet_financial_14d;

-- Resumen por milestone
SELECT 
    'CHECK_3_BY_MILESTONE: Total esperado vs total pagado por milestone' AS check_name,
    'M1' AS milestone,
    COUNT(CASE WHEN reached_m1_14d = true THEN 1 END) AS drivers_reached,
    COUNT(CASE WHEN claim_m1_exists = true THEN 1 END) AS drivers_with_claim,
    COUNT(CASE WHEN claim_m1_paid = true THEN 1 END) AS drivers_paid,
    SUM(expected_amount_m1) AS total_expected_m1,
    SUM(paid_amount_m1) AS total_paid_m1,
    SUM(expected_amount_m1 - paid_amount_m1) AS total_due_m1
FROM ops.v_cabinet_financial_14d
WHERE reached_m1_14d = true

UNION ALL

SELECT 
    'CHECK_3_BY_MILESTONE: Total esperado vs total pagado por milestone' AS check_name,
    'M5' AS milestone,
    COUNT(CASE WHEN reached_m5_14d = true THEN 1 END) AS drivers_reached,
    COUNT(CASE WHEN claim_m5_exists = true THEN 1 END) AS drivers_with_claim,
    COUNT(CASE WHEN claim_m5_paid = true THEN 1 END) AS drivers_paid,
    SUM(expected_amount_m5) AS total_expected_m5,
    SUM(paid_amount_m5) AS total_paid_m5,
    SUM(expected_amount_m5 - paid_amount_m5) AS total_due_m5
FROM ops.v_cabinet_financial_14d
WHERE reached_m5_14d = true

UNION ALL

SELECT 
    'CHECK_3_BY_MILESTONE: Total esperado vs total pagado por milestone' AS check_name,
    'M25' AS milestone,
    COUNT(CASE WHEN reached_m25_14d = true THEN 1 END) AS drivers_reached,
    COUNT(CASE WHEN claim_m25_exists = true THEN 1 END) AS drivers_with_claim,
    COUNT(CASE WHEN claim_m25_paid = true THEN 1 END) AS drivers_paid,
    SUM(expected_amount_m25) AS total_expected_m25,
    SUM(paid_amount_m25) AS total_paid_m25,
    SUM(expected_amount_m25 - paid_amount_m25) AS total_due_m25
FROM ops.v_cabinet_financial_14d
WHERE reached_m25_14d = true;

-- Top 50 drivers con mayor deuda pendiente
SELECT 
    'CHECK_3_TOP_DEBT: Top 50 drivers con mayor deuda pendiente' AS check_name,
    driver_id,
    lead_date,
    total_trips_14d,
    reached_m1_14d,
    reached_m5_14d,
    reached_m25_14d,
    expected_total_yango,
    total_paid_yango,
    amount_due_yango,
    claim_m1_exists,
    claim_m1_paid,
    claim_m5_exists,
    claim_m5_paid,
    claim_m25_exists,
    claim_m25_paid
FROM ops.v_cabinet_financial_14d
WHERE amount_due_yango > 0
ORDER BY amount_due_yango DESC, driver_id
LIMIT 50;

-- ============================================================================
-- CHECK 4: Validación de coherencia de milestones acumulativos
-- ============================================================================
-- Verifica que si M5 está alcanzado, M1 también lo esté
-- Verifica que si M25 está alcanzado, M5 y M1 también lo estén
-- ============================================================================

SELECT 
    'CHECK_4: Coherencia de milestones acumulativos' AS check_name,
    COUNT(CASE WHEN reached_m5_14d = true AND reached_m1_14d = false THEN 1 END) AS m5_without_m1,
    COUNT(CASE WHEN reached_m25_14d = true AND reached_m5_14d = false THEN 1 END) AS m25_without_m5,
    COUNT(CASE WHEN reached_m25_14d = true AND reached_m1_14d = false THEN 1 END) AS m25_without_m1
FROM ops.v_cabinet_financial_14d;

-- Detalle de drivers con milestones inconsistentes
SELECT 
    'CHECK_4_DETAIL: Drivers con milestones inconsistentes' AS check_name,
    driver_id,
    lead_date,
    total_trips_14d,
    reached_m1_14d,
    reached_m5_14d,
    reached_m25_14d,
    CASE 
        WHEN reached_m5_14d = true AND reached_m1_14d = false THEN 'M5 sin M1'
        WHEN reached_m25_14d = true AND reached_m5_14d = false THEN 'M25 sin M5'
        WHEN reached_m25_14d = true AND reached_m1_14d = false THEN 'M25 sin M1'
        ELSE 'OK'
    END AS issue_description
FROM ops.v_cabinet_financial_14d
WHERE (reached_m5_14d = true AND reached_m1_14d = false)
    OR (reached_m25_14d = true AND reached_m5_14d = false)
    OR (reached_m25_14d = true AND reached_m1_14d = false)
ORDER BY driver_id;

-- ============================================================================
-- RESUMEN EJECUTIVO
-- ============================================================================
-- Vista consolidada de todos los checks para reporte ejecutivo
-- ============================================================================

SELECT 
    'RESUMEN_EJECUTIVO' AS report_type,
    COUNT(*) AS total_drivers_cabinet,
    COUNT(CASE WHEN expected_total_yango > 0 THEN 1 END) AS drivers_con_deuda_esperada,
    COUNT(CASE WHEN amount_due_yango > 0 THEN 1 END) AS drivers_con_deuda_pendiente,
    SUM(expected_total_yango) AS total_esperado_yango,
    SUM(total_paid_yango) AS total_pagado_yango,
    SUM(amount_due_yango) AS total_deuda_yango,
    -- Porcentaje de cobranza
    CASE 
        WHEN SUM(expected_total_yango) > 0 
        THEN ROUND((SUM(total_paid_yango) / SUM(expected_total_yango)) * 100, 2)
        ELSE 0
    END AS porcentaje_cobranza,
    -- Drivers con milestones alcanzados
    COUNT(CASE WHEN reached_m1_14d = true THEN 1 END) AS drivers_m1,
    COUNT(CASE WHEN reached_m5_14d = true THEN 1 END) AS drivers_m5,
    COUNT(CASE WHEN reached_m25_14d = true THEN 1 END) AS drivers_m25,
    -- Drivers con claims
    COUNT(CASE WHEN claim_m1_exists = true THEN 1 END) AS drivers_claim_m1,
    COUNT(CASE WHEN claim_m5_exists = true THEN 1 END) AS drivers_claim_m5,
    COUNT(CASE WHEN claim_m25_exists = true THEN 1 END) AS drivers_claim_m25,
    -- Drivers con pagos
    COUNT(CASE WHEN claim_m1_paid = true THEN 1 END) AS drivers_paid_m1,
    COUNT(CASE WHEN claim_m5_paid = true THEN 1 END) AS drivers_paid_m5,
    COUNT(CASE WHEN claim_m25_paid = true THEN 1 END) AS drivers_paid_m25
FROM ops.v_cabinet_financial_14d;




