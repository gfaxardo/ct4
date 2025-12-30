-- ============================================================================
-- FIX: Corregir vista ops.v_claims_payment_status_cabinet
-- ============================================================================
-- Este script aplica el fix para eliminar duplicados y corregir expected_amount
-- Ejecutar desde psql o cualquier cliente PostgreSQL
-- ============================================================================

-- Leer y ejecutar el contenido completo del archivo v_claims_payment_status_cabinet.sql
\i backend/sql/ops/v_claims_payment_status_cabinet.sql

-- O mejor aún, ejecutar directamente el contenido (copiar y pegar en psql):

