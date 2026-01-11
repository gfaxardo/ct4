-- ============================================================================
-- Vista: ops.v_claims_cabinet_driver_rollup
-- ============================================================================
-- PROPÓSITO DE NEGOCIO:
-- Vista agregada driver-level derivada de ops.v_yango_cabinet_claims_for_collection.
-- Agrupa claims por driver_id + período para mostrar una vista amigable por conductor.
-- Garantiza reconciliación: SUM(rollup) == SUM(claim-level).
-- ============================================================================
-- REGLAS DE NEGOCIO:
-- 1. Fuente: ops.v_yango_cabinet_claims_for_collection (claim-level, 1 fila por claim)
-- 2. Agrupa por driver_id (o person_key si driver_id es NULL) y período (lead_date_min/max)
-- 3. Calcula totales desde yango_payment_status: PAID, UNPAID, PAID_MISAPPLIED
-- 4. Mantiene milestones_hit (M1/M5/M25) y status (paid/partial/not_paid)
-- 5. Priority: P0 (unpaid con bucket >= 3_15_30), P1 (tiene PAID_MISAPPLIED), P2 (resto)
-- ============================================================================

CREATE OR REPLACE VIEW ops.v_claims_cabinet_driver_rollup AS
WITH driver_period AS (
    SELECT 
        COALESCE(driver_id, 'person_' || person_key::text) AS driver_key,
        driver_id,
        person_key,
        driver_name,
        MIN(lead_date) AS lead_date_min,
        MAX(lead_date) AS lead_date_max,
        
        -- Totales por status Yango
        SUM(expected_amount) AS expected_total_yango,
        SUM(CASE WHEN yango_payment_status = 'PAID' THEN expected_amount ELSE 0 END) AS paid_total_yango,
        SUM(CASE WHEN yango_payment_status = 'UNPAID' THEN expected_amount ELSE 0 END) AS unpaid_total_yango,
        SUM(CASE WHEN yango_payment_status = 'PAID_MISAPPLIED' THEN expected_amount ELSE 0 END) AS misapplied_total_yango,
        
        -- Counts
        COUNT(*) AS claims_total,
        SUM(CASE WHEN yango_payment_status = 'PAID' THEN 1 ELSE 0 END) AS claims_paid,
        SUM(CASE WHEN yango_payment_status = 'UNPAID' THEN 1 ELSE 0 END) AS claims_unpaid,
        SUM(CASE WHEN yango_payment_status = 'PAID_MISAPPLIED' THEN 1 ELSE 0 END) AS claims_misapplied,
        
        -- Milestones hit
        BOOL_OR(milestone_value = 1) AS milestone_1_hit,
        BOOL_OR(milestone_value = 5) AS milestone_5_hit,
        BOOL_OR(milestone_value = 25) AS milestone_25_hit,
        
        -- Milestones paid
        BOOL_OR(milestone_value = 1 AND yango_payment_status = 'PAID') AS milestone_1_paid,
        BOOL_OR(milestone_value = 5 AND yango_payment_status = 'PAID') AS milestone_5_paid,
        BOOL_OR(milestone_value = 25 AND yango_payment_status = 'PAID') AS milestone_25_paid,
        
        -- Priority flags
        BOOL_OR(yango_payment_status = 'UNPAID' AND overdue_bucket_yango IN ('3_15_30', '4_30_plus')) AS has_p0_priority,
        BOOL_OR(yango_payment_status = 'PAID_MISAPPLIED') AS has_p1_priority
        
    FROM ops.v_yango_cabinet_claims_for_collection
    GROUP BY driver_key, driver_id, person_key, driver_name
)
SELECT 
    driver_id,
    person_key,
    driver_name,
    lead_date_min,
    lead_date_max,
    expected_total_yango,
    paid_total_yango,
    unpaid_total_yango,
    misapplied_total_yango,
    claims_total,
    claims_paid,
    claims_unpaid,
    claims_misapplied,
    
    -- Milestones hit (M1/M5/M25)
    jsonb_build_object(
        'm1', milestone_1_hit,
        'm5', milestone_5_hit,
        'm25', milestone_25_hit
    ) AS milestones_hit,
    
    -- Milestones paid
    jsonb_build_object(
        'paid_m1', milestone_1_paid,
        'paid_m5', milestone_5_paid,
        'paid_m25', milestone_25_paid
    ) AS milestones_paid,
    
    -- Status: paid/partial/not_paid
    CASE 
        WHEN claims_unpaid = 0 AND claims_misapplied = 0 THEN 'paid'
        WHEN claims_paid > 0 OR claims_misapplied > 0 THEN 'partial'
        ELSE 'not_paid'
    END AS status,
    
    -- Priority: P0/P1/P2
    CASE 
        WHEN has_p0_priority THEN 'P0'
        WHEN has_p1_priority THEN 'P1'
        ELSE 'P2'
    END AS priority

FROM driver_period;

-- ============================================================================
-- Comentarios de la Vista
-- ============================================================================
COMMENT ON VIEW ops.v_claims_cabinet_driver_rollup IS 
'Vista agregada driver-level derivada de ops.v_yango_cabinet_claims_for_collection. Agrupa claims por driver_id + período. Garantiza reconciliación: SUM(rollup) == SUM(claim-level).';

COMMENT ON COLUMN ops.v_claims_cabinet_driver_rollup.driver_id IS 
'ID del conductor (NULL si solo existe person_key).';

COMMENT ON COLUMN ops.v_claims_cabinet_driver_rollup.person_key IS 
'Person key del conductor (identidad canónica).';

COMMENT ON COLUMN ops.v_claims_cabinet_driver_rollup.driver_name IS 
'Nombre del conductor desde ops.v_yango_cabinet_claims_for_collection.';

COMMENT ON COLUMN ops.v_claims_cabinet_driver_rollup.expected_total_yango IS 
'Total esperado Yango (suma de expected_amount de todos los claims del driver).';

COMMENT ON COLUMN ops.v_claims_cabinet_driver_rollup.paid_total_yango IS 
'Total pagado Yango (suma de expected_amount donde yango_payment_status = PAID).';

COMMENT ON COLUMN ops.v_claims_cabinet_driver_rollup.unpaid_total_yango IS 
'Total no pagado Yango (suma de expected_amount donde yango_payment_status = UNPAID).';

COMMENT ON COLUMN ops.v_claims_cabinet_driver_rollup.misapplied_total_yango IS 
'Total pagado mal aplicado Yango (suma de expected_amount donde yango_payment_status = PAID_MISAPPLIED).';

COMMENT ON COLUMN ops.v_claims_cabinet_driver_rollup.status IS 
'Estado del driver: paid (todos pagados), partial (algunos pagados), not_paid (ninguno pagado).';

COMMENT ON COLUMN ops.v_claims_cabinet_driver_rollup.priority IS 
'Prioridad operativa: P0 (unpaid con bucket >= 3_15_30), P1 (tiene PAID_MISAPPLIED), P2 (resto).';

-- ============================================================================
-- QUERY DE RECONCILIACIÓN
-- ============================================================================
-- Para verificar que SUM(rollup) == SUM(claim-level):
-- SELECT 
--     (SELECT SUM(expected_total_yango) FROM ops.v_claims_cabinet_driver_rollup) AS rollup_total,
--     (SELECT SUM(expected_amount) FROM ops.v_yango_cabinet_claims_for_collection) AS claim_level_total,
--     (SELECT SUM(expected_total_yango) FROM ops.v_claims_cabinet_driver_rollup) - 
--     (SELECT SUM(expected_amount) FROM ops.v_yango_cabinet_claims_for_collection) AS difference;
-- Debe retornar difference = 0
-- ============================================================================





