-- Script para verificar qué vistas existen en la base de datos
-- Ejecuta esto en DBeaver para ver qué vistas faltan

-- Verificar vistas principales que necesita v_payments_driver_matrix_cabinet
SELECT 
    'v_claims_payment_status_cabinet' AS vista,
    EXISTS (
        SELECT 1 FROM information_schema.views 
        WHERE table_schema = 'ops' 
        AND table_name = 'v_claims_payment_status_cabinet'
    ) AS existe;

SELECT 
    'v_yango_cabinet_claims_for_collection' AS vista,
    EXISTS (
        SELECT 1 FROM information_schema.views 
        WHERE table_schema = 'ops' 
        AND table_name = 'v_yango_cabinet_claims_for_collection'
    ) AS existe;

SELECT 
    'v_yango_payments_claims_cabinet_14d' AS vista,
    EXISTS (
        SELECT 1 FROM information_schema.views 
        WHERE table_schema = 'ops' 
        AND table_name = 'v_yango_payments_claims_cabinet_14d'
    ) AS existe;

SELECT 
    'v_payment_calculation' AS vista,
    EXISTS (
        SELECT 1 FROM information_schema.views 
        WHERE table_schema = 'ops' 
        AND table_name = 'v_payment_calculation'
    ) AS existe;

SELECT 
    'v_payment_calculation_updated' AS vista,
    EXISTS (
        SELECT 1 FROM information_schema.views 
        WHERE table_schema = 'ops' 
        AND table_name = 'v_payment_calculation_updated'
    ) AS existe;

-- Ver todas las vistas en ops
SELECT 
    table_name AS vista,
    'EXISTS' AS estado
FROM information_schema.views 
WHERE table_schema = 'ops'
ORDER BY table_name;



