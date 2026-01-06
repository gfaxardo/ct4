-- ============================================================================
-- Vista: Resumen Ejecutivo - Reclamo Formal a Yango
-- ============================================================================
-- PROPÓSITO:
-- Vista READ-ONLY que agrupa EXIGIMOS y REPORTAMOS para resumen ejecutivo.
-- Usada para presentar resumen consolidado del reclamo formal a Yango.
--
-- ESTRUCTURA:
-- - Agrupa EXIGIMOS por milestone_value: count, sum(expected_amount)
-- - Agrupa REPORTAMOS: count, sum(paid_amount)
-- - Todo en 1 vista usando UNION ALL con section='EXIGIMOS'/'REPORTAMOS'
-- ============================================================================

CREATE OR REPLACE VIEW ops.v_yango_cabinet_claims_exec_summary AS
WITH exigimos_by_milestone AS (
    SELECT 
        'EXIGIMOS' AS section,
        milestone_value::text AS category,
        COUNT(*) AS count_claims,
        SUM(expected_amount) AS amount
    FROM ops.v_yango_cabinet_claims_exigimos
    GROUP BY milestone_value
),
exigimos_total AS (
    SELECT 
        'EXIGIMOS' AS section,
        'TOTAL' AS category,
        COUNT(*) AS count_claims,
        SUM(expected_amount) AS amount
    FROM ops.v_yango_cabinet_claims_exigimos
),
reportamos_by_reason AS (
    SELECT 
        'REPORTAMOS' AS section,
        no_mapping_reason AS category,
        COUNT(*) AS count_claims,
        SUM(paid_amount) AS amount
    FROM ops.v_yango_cabinet_payments_reportamos
    GROUP BY no_mapping_reason
),
reportamos_total AS (
    SELECT 
        'REPORTAMOS' AS section,
        'TOTAL' AS category,
        COUNT(*) AS count_claims,
        SUM(paid_amount) AS amount
    FROM ops.v_yango_cabinet_payments_reportamos
)
SELECT 
    section,
    category,
    count_claims,
    amount
FROM exigimos_by_milestone

UNION ALL

SELECT 
    section,
    category,
    count_claims,
    amount
FROM exigimos_total

UNION ALL

SELECT 
    section,
    category,
    count_claims,
    amount
FROM reportamos_by_reason

UNION ALL

SELECT 
    section,
    category,
    count_claims,
    amount
FROM reportamos_total

ORDER BY section, category;

-- ============================================================================
-- Comentarios
-- ============================================================================
COMMENT ON VIEW ops.v_yango_cabinet_claims_exec_summary IS 
'Vista READ-ONLY de resumen ejecutivo para reclamo formal a Yango. Agrupa EXIGIMOS por milestone y REPORTAMOS por motivo de no mapeo. Incluye totales por sección.';

COMMENT ON COLUMN ops.v_yango_cabinet_claims_exec_summary.section IS 
'Sección: EXIGIMOS (claims no pagados) o REPORTAMOS (pagos recibidos sin mapeo).';

COMMENT ON COLUMN ops.v_yango_cabinet_claims_exec_summary.category IS 
'Categoría: Para EXIGIMOS es milestone_value (1, 5, 25, TOTAL). Para REPORTAMOS es no_mapping_reason (NO_IDENTITY, NOT_CABINET_DRIVER, NO_CLAIM_EXISTS, TOTAL).';

COMMENT ON COLUMN ops.v_yango_cabinet_claims_exec_summary.count_claims IS 
'Número de registros en la categoría.';

COMMENT ON COLUMN ops.v_yango_cabinet_claims_exec_summary.amount IS 
'Monto total en la categoría. Para EXIGIMOS es expected_amount, para REPORTAMOS es paid_amount.';










