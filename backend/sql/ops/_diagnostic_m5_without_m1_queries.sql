
-- ============================================================================
-- QUERIES DIAGNOSTICAS: Causa raiz M5 sin M1
-- ============================================================================

-- Q1: Verificar distribución de milestones en claims base
SELECT 
    milestone_value,
    COUNT(*) as total_claims,
    COUNT(DISTINCT driver_id) as unique_drivers
FROM ops.v_claims_payment_status_cabinet
WHERE milestone_value IN (1, 5, 25)
GROUP BY milestone_value
ORDER BY milestone_value;

-- Q2: Drivers con M5 pero sin M1 en claims base
SELECT 
    COUNT(DISTINCT driver_id) as drivers_m5_sin_m1
FROM (
    SELECT 
        driver_id,
        COUNT(*) FILTER (WHERE milestone_value = 1) as m1_count,
        COUNT(*) FILTER (WHERE milestone_value = 5) as m5_count
    FROM ops.v_claims_payment_status_cabinet
    GROUP BY driver_id
    HAVING COUNT(*) FILTER (WHERE milestone_value = 1) = 0
    AND COUNT(*) FILTER (WHERE milestone_value = 5) > 0
) subq;

-- Q3: Verificar si hay filtros por milestone_value en la vista
-- (Revisar manualmente la definición de v_claims_payment_status_cabinet)

-- Q4: Verificar reglas de negocio que generan claims
-- (Revisar ops.payment_rules o similar)

-- Q5: Verificar condiciones temporales/ventanas
SELECT 
    driver_id,
    milestone_value,
    lead_date,
    expected_amount,
    payment_status
FROM ops.v_claims_payment_status_cabinet
WHERE driver_id IN (
    SELECT driver_id 
    FROM ops.v_payments_driver_matrix_cabinet 
    WHERE m5_without_m1_flag = true 
    LIMIT 5
)
ORDER BY driver_id, milestone_value, lead_date;
