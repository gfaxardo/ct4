-- ============================================================================
-- Vista de Auditoría: Claims No Reconciliables
-- ============================================================================
-- PROPÓSITO:
-- Vista READ-ONLY que explica el motivo determinístico de no reconciliación
-- para cada claim donde is_reconcilable_enriched = false.
--
-- GRANO: 1 fila por claim (mismo grano que ops.mv_yango_cabinet_claims_for_collection)
-- Cada fila cae en UN SOLO audit_reason_code (ordenado por prioridad estricta)
--
-- EXPLORACIÓN REALIZADA:
-- - No existe claim_id/claim_key/row_key/record_id en la MV
-- - payment_key existe pero es NULL en todos los no reconciliables
-- - (driver_id, milestone_value, lead_date) es único -> usar para audit_row_key
-- - match_confidence es tipo text, valores: NULL (256), 'medium' (160)
-- - reason_code existe en MV con valor 'no_payment_found' en no reconciliables
-- - driver_id es el nombre real del campo (no driver_id_final)
-- ============================================================================

CREATE OR REPLACE VIEW ops.v_yango_cabinet_audit_non_reconcilable AS
WITH claims_non_reconcilable AS (
    SELECT 
        -- Identificador único: MD5 de (driver_id, milestone_value, lead_date)
        -- Esta combinación es única según exploración (query 10)
        MD5(
            COALESCE(driver_id::text, 'NULL') || '|' ||
            milestone_value::text || '|' ||
            COALESCE(lead_date::text, 'NULL')
        ) AS audit_row_key,
        
        -- Campos de identificación
        driver_id,
        person_key,
        driver_name,
        milestone_value,
        lead_date,
        
        -- Campos de monto y fechas
        expected_amount,
        yango_due_date,
        days_overdue_yango,
        overdue_bucket_yango,
        
        -- Campos de estado
        yango_payment_status,
        is_reconcilable_enriched,
        
        -- Campos de identidad y matching
        identity_status,
        match_rule,
        match_confidence,
        
        -- Campos adicionales para diagnóstico
        payment_key,
        pay_date,
        reason_code AS mv_reason_code,
        suggested_driver_id
    FROM ops.mv_yango_cabinet_claims_for_collection
    WHERE is_reconcilable_enriched = false
),
-- Helper: determinar si match_confidence es bajo según tipo text
confidence_helper AS (
    SELECT 
        *,
        -- match_confidence es tipo text
        -- Valores bajos: 'low' o 'medium' (text)
        -- NULL no se considera bajo (ya está cubierto por NO_IDENTITY_MATCH)
        CASE
            WHEN match_confidence::text IN ('low', 'medium') THEN true
            ELSE false
        END AS is_low_confidence
    FROM claims_non_reconcilable
)
SELECT 
    audit_row_key,
    driver_id,
    person_key,
    driver_name,
    milestone_value,
    lead_date,
    expected_amount,
    yango_due_date,
    days_overdue_yango,
    overdue_bucket_yango,
    yango_payment_status,
    identity_status,
    match_rule,
    match_confidence,
    payment_key,
    pay_date,
    mv_reason_code,
    suggested_driver_id,
    
    -- Audit reason code con prioridad estricta
    -- IMPORTANTE: El orden de los CASE es crítico - primera coincidencia gana
    CASE
        -- 1. NO_IDENTITY_MATCH: Sin identidad o identidad ambigua
        WHEN driver_id IS NULL 
            OR identity_status IN ('no_match', 'ambiguous')
            OR identity_status IS NULL
        THEN 'NO_IDENTITY_MATCH'
        
        -- 2. LOW_MATCH_CONFIDENCE: Identidad OK pero confianza baja
        -- match_confidence es tipo text: 'low' o 'medium' son bajos
        WHEN driver_id IS NOT NULL
            AND identity_status IN ('confirmed', 'enriched')
            AND is_low_confidence = true
        THEN 'LOW_MATCH_CONFIDENCE'
        
        -- 3. DATA_INCONSISTENCY: Datos inconsistentes
        WHEN expected_amount IS NULL 
            OR expected_amount <= 0
            OR lead_date IS NULL
            OR yango_due_date IS NULL
        THEN 'DATA_INCONSISTENCY'
        
        -- 4. OTHER_CLOSED: Fallback para casos no cubiertos
        ELSE 'OTHER_CLOSED'
    END AS audit_reason_code
    
FROM confidence_helper;

-- ============================================================================
-- Comentarios de la Vista
-- ============================================================================
COMMENT ON VIEW ops.v_yango_cabinet_audit_non_reconcilable IS 
'Vista READ-ONLY de auditoría para claims no reconciliables (is_reconcilable_enriched=false). Explica motivo determinístico con audit_reason_code. Prioridad estricta: NO_IDENTITY_MATCH > LOW_MATCH_CONFIDENCE > DATA_INCONSISTENCY > OTHER_CLOSED. Mismo grano que ops.mv_yango_cabinet_claims_for_collection.';

COMMENT ON COLUMN ops.v_yango_cabinet_audit_non_reconcilable.audit_row_key IS 
'Identificador único del claim generado como MD5(driver_id|milestone_value|lead_date). Esta combinación es única según exploración.';

COMMENT ON COLUMN ops.v_yango_cabinet_audit_non_reconcilable.mv_reason_code IS 
'Reason code original de la MV (ops.mv_yango_cabinet_claims_for_collection.reason_code). No modificado.';

COMMENT ON COLUMN ops.v_yango_cabinet_audit_non_reconcilable.audit_reason_code IS 
'Código calculado por auditoría. NO_IDENTITY_MATCH: sin identidad o ambigua. LOW_MATCH_CONFIDENCE: confianza baja (text: low/medium). DATA_INCONSISTENCY: datos inválidos. OTHER_CLOSED: fallback. Orden de prioridad: primera coincidencia gana.';












