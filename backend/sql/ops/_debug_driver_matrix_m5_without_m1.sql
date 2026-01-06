-- ============================================================================
-- Script de diagnóstico: Driver Matrix - M5 sin M1
-- ============================================================================
-- PROPÓSITO:
-- Diagnosticar casos donde la vista ops.v_payments_driver_matrix_cabinet
-- muestra M5 con datos pero M1 vacío (NULL).
-- ============================================================================
-- USO:
-- Ejecutar en psql o herramienta SQL conectada a la base de datos.
-- Ajustar parámetros según necesidad (driver_id, origin_tag, etc.)
-- ============================================================================

-- ============================================================================
-- PARTE A: Conteo por origin_tag de inconsistencias
-- ============================================================================
-- Cuenta filas donde M5 tiene payment_status pero M1 no
SELECT 
    origin_tag,
    COUNT(*) AS casos_m5_sin_m1,
    COUNT(DISTINCT driver_id) AS drivers_unicos_afectados
FROM ops.v_payments_driver_matrix_cabinet
WHERE m5_yango_payment_status IS NOT NULL 
    AND m1_yango_payment_status IS NULL
GROUP BY origin_tag
ORDER BY casos_m5_sin_m1 DESC;

-- ============================================================================
-- PARTE B: Sample de 30 filas con columnas clave
-- ============================================================================
-- Muestra casos específicos con información relevante
SELECT 
    driver_id,
    person_key,
    driver_name,
    week_start,
    lead_date,
    origin_tag,
    -- M1 fields
    m1_achieved_flag,
    m1_achieved_date,
    m1_expected_amount_yango,
    m1_yango_payment_status,
    m1_window_status,
    m1_overdue_days,
    -- M5 fields
    m5_achieved_flag,
    m5_achieved_date,
    m5_expected_amount_yango,
    m5_yango_payment_status,
    m5_window_status,
    m5_overdue_days,
    -- M25 fields (para contexto)
    m25_achieved_flag,
    m25_yango_payment_status
FROM ops.v_payments_driver_matrix_cabinet
WHERE m5_yango_payment_status IS NOT NULL 
    AND m1_yango_payment_status IS NULL
ORDER BY m5_achieved_date DESC NULLS LAST, driver_name ASC
LIMIT 30;

-- ============================================================================
-- PARTE C: Queries parametrizables por driver_id
-- ============================================================================
-- Reemplazar :driver_id con el driver_id específico a investigar
-- Ejemplo: WHERE driver_id = '08e20910d81d42658d4334d3f6d10ac0'

-- C1: Revisar claims base (ops.v_claims_payment_status_cabinet)
-- Muestra todos los claims del driver por milestone
SELECT 
    driver_id,
    person_key,
    lead_date,
    milestone_value,
    expected_amount,
    paid_flag,
    paid_date,
    days_overdue,
    payment_status,
    reason_code
FROM ops.v_claims_payment_status_cabinet
WHERE driver_id = :driver_id  -- Reemplazar con driver_id específico
    AND milestone_value IN (1, 5, 25)
ORDER BY milestone_value, lead_date DESC;

-- C2: Revisar claims Yango (ops.v_yango_cabinet_claims_for_collection)
-- Muestra el estado de pago Yango por milestone
SELECT 
    driver_id,
    milestone_value,
    yango_payment_status,
    driver_name,
    lead_date,
    expected_amount_yango,
    paid_date_yango
FROM ops.v_yango_cabinet_claims_for_collection
WHERE driver_id = :driver_id  -- Reemplazar con driver_id específico
    AND milestone_value IN (1, 5, 25)
ORDER BY milestone_value, lead_date DESC;

-- C3: Verificar si hay claims M1 que no están llegando a la vista
-- Compara claims base vs lo que aparece en la vista final
WITH claims_base AS (
    SELECT 
        driver_id,
        milestone_value,
        lead_date,
        expected_amount,
        payment_status
    FROM ops.v_claims_payment_status_cabinet
    WHERE driver_id = :driver_id  -- Reemplazar con driver_id específico
        AND milestone_value = 1  -- Solo M1
),
yango_claims AS (
    SELECT 
        driver_id,
        milestone_value,
        lead_date,
        yango_payment_status
    FROM ops.v_yango_cabinet_claims_for_collection
    WHERE driver_id = :driver_id  -- Reemplazar con driver_id específico
        AND milestone_value = 1  -- Solo M1
),
matrix_view AS (
    SELECT 
        driver_id,
        m1_achieved_flag,
        m1_achieved_date,
        m1_yango_payment_status
    FROM ops.v_payments_driver_matrix_cabinet
    WHERE driver_id = :driver_id  -- Reemplazar con driver_id específico
)
SELECT 
    'Claims Base M1' AS fuente,
    COUNT(*) AS total_registros
FROM claims_base
UNION ALL
SELECT 
    'Yango Claims M1' AS fuente,
    COUNT(*) AS total_registros
FROM yango_claims
UNION ALL
SELECT 
    'Matrix View M1' AS fuente,
    CASE WHEN m1_achieved_flag THEN 1 ELSE 0 END AS total_registros
FROM matrix_view;

-- C4: Verificar múltiples ciclos/semanas por driver
-- Detecta si el mismo driver tiene múltiples filas (por week_start diferente)
SELECT 
    driver_id,
    person_key,
    COUNT(*) AS num_filas,
    COUNT(DISTINCT week_start) AS semanas_distintas,
    COUNT(DISTINCT lead_date) AS lead_dates_distintas,
    ARRAY_AGG(DISTINCT week_start ORDER BY week_start) AS semanas,
    ARRAY_AGG(DISTINCT lead_date ORDER BY lead_date) AS lead_dates
FROM ops.v_payments_driver_matrix_cabinet
WHERE driver_id = :driver_id  -- Reemplazar con driver_id específico
GROUP BY driver_id, person_key
HAVING COUNT(*) > 1;

-- C5: Verificar joins/identidad
-- Compara person_key entre diferentes fuentes
SELECT 
    'v_claims_payment_status_cabinet' AS fuente,
    driver_id,
    person_key,
    milestone_value,
    lead_date
FROM ops.v_claims_payment_status_cabinet
WHERE driver_id = :driver_id  -- Reemplazar con driver_id específico
    AND milestone_value IN (1, 5)
UNION ALL
SELECT 
    'v_yango_cabinet_claims_for_collection' AS fuente,
    driver_id,
    NULL::uuid AS person_key,  -- Esta vista puede no tener person_key
    milestone_value,
    lead_date
FROM ops.v_yango_cabinet_claims_for_collection
WHERE driver_id = :driver_id  -- Reemplazar con driver_id específico
    AND milestone_value IN (1, 5)
ORDER BY milestone_value, lead_date DESC;

-- ============================================================================
-- PARTE D: Análisis de causas probables
-- ============================================================================

-- D1: Missing claim M1 - Verificar si hay drivers con M5 pero sin M1 en claims base
SELECT 
    'Missing M1 in base claims' AS causa,
    COUNT(DISTINCT driver_id) AS drivers_afectados
FROM (
    SELECT DISTINCT driver_id
    FROM ops.v_claims_payment_status_cabinet
    WHERE milestone_value = 5
) m5_drivers
WHERE NOT EXISTS (
    SELECT 1
    FROM ops.v_claims_payment_status_cabinet c
    WHERE c.driver_id = m5_drivers.driver_id
        AND c.milestone_value = 1
);

-- D2: Mismatch identidad/join - Drivers con M1 en claims pero sin match en Yango
SELECT 
    'M1 in claims but not in Yango' AS causa,
    COUNT(DISTINCT c.driver_id) AS drivers_afectados
FROM ops.v_claims_payment_status_cabinet c
WHERE c.milestone_value = 1
    AND NOT EXISTS (
        SELECT 1
        FROM ops.v_yango_cabinet_claims_for_collection y
        WHERE y.driver_id = c.driver_id
            AND y.milestone_value = 1
            AND y.lead_date = c.lead_date  -- Match por lead_date también
    );

-- D3: Split de semanas - Drivers con múltiples week_start
SELECT 
    'Multiple week_start per driver' AS causa,
    COUNT(*) AS casos
FROM (
    SELECT 
        driver_id,
        COUNT(DISTINCT week_start) AS num_semanas
    FROM ops.v_payments_driver_matrix_cabinet
    WHERE m5_yango_payment_status IS NOT NULL 
        AND m1_yango_payment_status IS NULL
    GROUP BY driver_id
    HAVING COUNT(DISTINCT week_start) > 1
) multi_week;

-- D4: Múltiples ciclos por driver - Verificar GROUP BY
-- Esta query muestra si el GROUP BY bc.driver_id está agrupando múltiples claims
SELECT 
    'Multiple claims per driver in GROUP BY' AS causa,
    COUNT(*) AS drivers_con_multiple_claims
FROM (
    SELECT 
        bc.driver_id,
        COUNT(*) AS num_claims
    FROM ops.v_claims_payment_status_cabinet bc
    WHERE bc.milestone_value IN (1, 5)
    GROUP BY bc.driver_id
    HAVING COUNT(*) > 2  -- Más de 2 claims (al menos M1 y M5, pero puede haber más)
) multi_claims;





