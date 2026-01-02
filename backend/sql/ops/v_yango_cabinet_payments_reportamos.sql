-- ============================================================================
-- Vista: Pagos Recibidos que NO Mapean a Nuestros Leads Cabinet
-- ============================================================================
-- PROPÓSITO:
-- Vista READ-ONLY que lista pagos recibidos (Yango->YEGO) que NO matchean 
-- a nuestros leads cabinet. Usada para reportar pagos recibidos que no 
-- corresponden a nuestros claims.
--
-- DEFINICIÓN:
-- - Universo: pagos del ledger (vista enriched) que NO matchean a nuestros leads cabinet.
-- - Criterio de NO mapeo:
--   - Payment tiene driver_id_final que NO existe en nuestro universo de drivers 
--     provenientes de cabinet_leads
--   - O payment NO tiene match de identidad contra person_key de nuestros leads
--
-- NOTA: Un pago se considera "mapeado" si existe un claim en 
-- ops.mv_yango_cabinet_claims_for_collection con el mismo driver_id y milestone_value
-- Y ese claim tiene un lead cabinet asociado (vía identity_links).
-- ============================================================================

CREATE OR REPLACE VIEW ops.v_yango_cabinet_payments_reportamos AS
WITH cabinet_claims AS (
    -- Claims existentes de nuestros leads cabinet
    -- Estos ya representan drivers que vienen de nuestros leads cabinet
    SELECT DISTINCT
        driver_id,
        person_key,
        milestone_value
    FROM ops.mv_yango_cabinet_claims_for_collection
    WHERE driver_id IS NOT NULL
),
cabinet_drivers AS (
    -- Drivers que provienen de nuestros leads cabinet
    -- Usar los drivers de nuestros claims + person_keys de leads cabinet
    SELECT DISTINCT
        cc.driver_id,
        cc.person_key AS cabinet_person_key
    FROM cabinet_claims cc
    WHERE cc.driver_id IS NOT NULL
    
    UNION
    
    -- También incluir person_keys de leads cabinet directamente
    SELECT DISTINCT
        NULL::text AS driver_id,
        il.person_key AS cabinet_person_key
    FROM canon.identity_links il
    WHERE il.source_table = 'module_ct_cabinet_leads'
        AND il.person_key IS NOT NULL
)
SELECT DISTINCT ON (p.payment_key)
    -- Identificación del pago
    p.payment_key,
    p.pay_date,
    p.milestone_value,
    
    -- Monto pagado (calcular según milestone)
    CASE 
        WHEN p.milestone_value = 1 THEN 25::numeric(12,2)
        WHEN p.milestone_value = 5 THEN 35::numeric(12,2)
        WHEN p.milestone_value = 25 THEN 100::numeric(12,2)
        ELSE 0::numeric(12,2)
    END AS paid_amount,
    
    -- Identidad del pago
    p.driver_id_final,
    p.person_key_final,
    p.raw_driver_name AS driver_name_norm,
    p.identity_status,
    p.match_rule,
    p.match_confidence,
    
    -- Verificación: ¿existe claim para este pago?
    c.driver_id AS claim_driver_id,
    c.person_key AS claim_person_key,
    
    -- Verificación: ¿existe lead cabinet para este driver/person_key?
    cd.driver_id AS cabinet_driver_id,
    cd.cabinet_person_key,
    
    -- Motivo de no mapeo
    CASE
        WHEN p.driver_id_final IS NULL AND p.person_key_final IS NULL THEN 'NO_IDENTITY'
        WHEN cd.driver_id IS NULL AND cd.cabinet_person_key IS NULL THEN 'NOT_CABINET_DRIVER'
        WHEN c.driver_id IS NULL THEN 'NO_CLAIM_EXISTS'
        ELSE 'OTHER'
    END AS no_mapping_reason
    
FROM ops.v_yango_payments_ledger_latest_enriched p
-- Verificar si existe claim para este pago (driver_id + milestone_value)
LEFT JOIN cabinet_claims c
    ON c.driver_id = p.driver_id_final
    AND c.milestone_value = p.milestone_value
-- Verificar si el driver/person_key viene de nuestros leads cabinet
LEFT JOIN cabinet_drivers cd
    ON (cd.driver_id = p.driver_id_final OR cd.cabinet_person_key = p.person_key_final)

WHERE 
    -- Solo pagos efectivamente pagados
    p.is_paid = true
    -- Solo milestones válidos
    AND p.milestone_value IN (1, 5, 25)
    -- Filtrar pagos que NO matchean:
    -- 1. No tienen identidad
    -- 2. O no son drivers de nuestros leads cabinet (ni por driver_id ni por person_key)
    -- 3. O no tienen claim correspondiente
    AND (
        (p.driver_id_final IS NULL AND p.person_key_final IS NULL)
        OR (cd.driver_id IS NULL AND cd.cabinet_person_key IS NULL)
        OR c.driver_id IS NULL
    )
-- Eliminar duplicados por payment_key (si un payment_key aparece múltiples veces, quedarse con el más reciente)
ORDER BY p.payment_key, p.pay_date DESC NULLS LAST, p.driver_id_final NULLS LAST;

-- ============================================================================
-- Comentarios
-- ============================================================================
COMMENT ON VIEW ops.v_yango_cabinet_payments_reportamos IS 
'Vista READ-ONLY de pagos recibidos (Yango->YEGO) que NO matchean a nuestros leads cabinet. Incluye pagos sin identidad, pagos de drivers no-cabinet, o pagos sin claim correspondiente. Usada para reportar pagos recibidos que no corresponden a nuestros claims.';

COMMENT ON COLUMN ops.v_yango_cabinet_payments_reportamos.payment_key IS 
'Identificador único del pago desde el ledger.';

COMMENT ON COLUMN ops.v_yango_cabinet_payments_reportamos.paid_amount IS 
'Monto pagado según milestone: 1=S/25, 5=S/35, 25=S/100. Calculado desde milestone_value.';

COMMENT ON COLUMN ops.v_yango_cabinet_payments_reportamos.no_mapping_reason IS 
'Motivo de no mapeo: NO_IDENTITY (sin identidad), NOT_CABINET_DRIVER (no es driver de nuestros leads), NO_CLAIM_EXISTS (no tiene claim), OTHER (otro motivo).';

