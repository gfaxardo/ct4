-- ============================================================================
-- Script de Spot-Check: Driver Matrix Operativo
-- ============================================================================
-- PROPÓSITO:
-- Auditoría humana de 20 drivers mostrando información operativa y de claims.
-- Usado para validar visualmente coherencia entre operación real y claims.
-- ============================================================================

SET statement_timeout = '120s';

SELECT 
    'SPOT-CHECK: Driver Matrix Operativo' AS check_name,
    driver_id,
    driver_name,
    lead_date,
    connection_within_14d_flag,
    connection_date_within_14d,
    trips_completed_14d_from_lead,
    first_trip_date_within_14d,
    -- Achieved flags
    m1_achieved_flag,
    m5_achieved_flag,
    m25_achieved_flag,
    -- Claim status
    m1_yango_payment_status,
    m5_yango_payment_status,
    m25_yango_payment_status,
    -- Expected amounts
    m1_expected_amount_yango,
    m5_expected_amount_yango,
    m25_expected_amount_yango
FROM ops.v_payments_driver_matrix_cabinet
WHERE origin_tag = 'cabinet'
    AND (
        m1_achieved_flag = true
        OR m5_achieved_flag = true
        OR m25_achieved_flag = true
    )
ORDER BY lead_date DESC, driver_id
LIMIT 20;

