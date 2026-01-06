-- ============================================================================
-- Script de Aplicación: Fix M1 Claims Generation para Cabinet
-- ============================================================================
-- PROPÓSITO:
-- Aplicar el fix para que M1 genere claims correctamente cuando está achieved
-- dentro de la ventana de 14 días.
-- ============================================================================
-- CAMBIOS:
-- 1. v_claims_payment_status_cabinet: usar v_cabinet_milestones_achieved_from_payment_calc
--    en lugar de v_cabinet_milestones_achieved_from_trips
-- 2. Incluir M1, M5, M25 con expected_amount correcto (M1=25, M5=35, M25=100)
-- 3. Aplicar ventana de 14 días correctamente: achieved_date entre lead_date y lead_date+14d
-- ============================================================================
-- ORDEN DE EJECUCIÓN:
-- 1. Aplicar cambios en v_claims_payment_status_cabinet.sql
-- 2. Ejecutar verify_m1_claims_generation.sql para validar
-- ============================================================================

-- Aplicar la vista corregida
\i backend/sql/ops/v_claims_payment_status_cabinet.sql

-- Verificar que la vista se creó correctamente
SELECT 
    'Vista aplicada' AS status,
    COUNT(*) AS count_claims_m1,
    COUNT(*) FILTER (WHERE milestone_value = 1) AS count_m1,
    COUNT(*) FILTER (WHERE milestone_value = 5) AS count_m5,
    COUNT(*) FILTER (WHERE milestone_value = 25) AS count_m25
FROM ops.v_claims_payment_status_cabinet
WHERE milestone_value IN (1, 5, 25);

