-- ============================================================================
-- Crear vista materializada de v_yango_cabinet_claims_for_collection
-- ============================================================================
-- Esta vista es la que realmente se consulta desde el frontend y contiene
-- las columnas yango_payment_status e is_reconcilable_enriched
-- ============================================================================

DROP MATERIALIZED VIEW IF EXISTS ops.mv_yango_cabinet_claims_for_collection CASCADE;

CREATE MATERIALIZED VIEW ops.mv_yango_cabinet_claims_for_collection AS
SELECT 
    -- Campos de identificación
    c.driver_id,
    c.person_key,
    d.full_name AS driver_name,
    c.milestone_value,
    c.lead_date,
    
    -- Campo de monto (no recalcular, usar de vista base)
    c.expected_amount,
    
    -- Campos derivados Yango
    c.lead_date + INTERVAL '14 days' AS yango_due_date,
    GREATEST(0, CURRENT_DATE - (c.lead_date + INTERVAL '14 days')::date) AS days_overdue_yango,
    CASE 
        WHEN (c.lead_date + INTERVAL '14 days')::date >= CURRENT_DATE THEN '0_not_due'
        WHEN (CURRENT_DATE - (c.lead_date + INTERVAL '14 days')::date) BETWEEN 1 AND 7 THEN '1_1_7'
        WHEN (CURRENT_DATE - (c.lead_date + INTERVAL '14 days')::date) BETWEEN 8 AND 14 THEN '2_8_14'
        WHEN (CURRENT_DATE - (c.lead_date + INTERVAL '14 days')::date) BETWEEN 15 AND 30 THEN '3_15_30'
        ELSE '4_30_plus'
    END AS overdue_bucket_yango,
    
    -- Campo canónico de estado
    CASE
        WHEN c.paid_flag = true THEN 'PAID'
        WHEN c.reason_code = 'payment_found_other_milestone' THEN 'PAID_MISAPPLIED'
        ELSE 'UNPAID'
    END AS yango_payment_status,
    
    -- Campos de evidencia
    c.payment_key,
    c.paid_date AS pay_date,
    c.reason_code,
    c.payment_match_rule AS match_rule,
    c.payment_match_confidence AS match_confidence,
    
    -- Campos de identidad enriquecida (Opción B: diagnóstico de misapplied)
    c.payment_identity_status AS identity_status,
    
    -- suggested_driver_id: driver_id sugerido desde ledger enriched cuando hay misapplied
    COALESCE(
        p_other_milestone.driver_id_final,
        p_person_key.driver_id_final
    ) AS suggested_driver_id,
    
    -- is_reconcilable_enriched: flag para identificar claims reconciliables
    -- LÓGICA ROBUSTA:
    -- 1. identity_status debe ser 'confirmed' o 'enriched'
    -- 2. match_confidence puede ser string ('high'/'medium'/'low') o numérico
    -- 3. Si es 'high' -> siempre reconciliable
    -- 4. Si es 'medium' -> reconciliable si match_rule es 'name_unique' o 'source_upstream'
    -- 5. Si es numérico -> reconciliable si >= 0.85
    CASE
        -- Requisito base: identity_status debe ser confirmed o enriched
        WHEN c.payment_identity_status NOT IN ('confirmed', 'enriched') THEN false
        
        -- match_confidence = 'high' -> siempre reconciliable
        WHEN c.payment_match_confidence = 'high' THEN true
        
        -- match_confidence = 'medium' -> reconciliable solo si match_rule es único
        WHEN c.payment_match_confidence = 'medium' 
            AND c.payment_match_rule IN ('name_unique', 'source_upstream') 
        THEN true
        
        -- match_confidence numérico -> reconciliable si >= 0.85
        WHEN c.payment_match_confidence::text ~ '^[0-9]+\.?[0-9]*$' 
            AND (c.payment_match_confidence::numeric >= 0.85)
        THEN true
        
        -- Cualquier otro caso -> no reconciliable
        ELSE false
    END AS is_reconcilable_enriched

FROM ops.mv_claims_payment_status_cabinet c
LEFT JOIN public.drivers d ON d.driver_id = c.driver_id
-- Usar vistas materializadas en los JOINs LATERAL
LEFT JOIN LATERAL (
    SELECT driver_id_final
    FROM ops.mv_yango_payments_ledger_latest_enriched p
    WHERE p.driver_id_final = c.driver_id
        AND p.milestone_value != c.milestone_value
        AND p.is_paid = true
    ORDER BY p.pay_date DESC
    LIMIT 1
) p_other_milestone ON c.reason_code = 'payment_found_other_milestone'
LEFT JOIN LATERAL (
    SELECT driver_id_final
    FROM ops.mv_yango_payments_ledger_latest_enriched p
    WHERE p.person_key_final = c.person_key
        AND p.milestone_value = c.milestone_value
        AND p.is_paid = true
        AND p.driver_id_final IS NOT NULL
    ORDER BY p.pay_date DESC
    LIMIT 1
) p_person_key ON c.reason_code = 'payment_found_person_key_only' 
    AND c.person_key IS NOT NULL;

COMMENT ON MATERIALIZED VIEW ops.mv_yango_cabinet_claims_for_collection IS 
'Vista materializada de claims para cobranza Yango. Contiene yango_payment_status e is_reconcilable_enriched. Refrescar cada hora o cuando hay nuevos claims.';

-- ============================================================================
-- Crear índices optimizados
-- ============================================================================

-- Índice parcial para filtros PAID_MISAPPLIED + is_reconcilable_enriched
CREATE INDEX IF NOT EXISTS idx_mv_yango_cabinet_claims_misapplied_reconcilable 
    ON ops.mv_yango_cabinet_claims_for_collection(yango_payment_status, is_reconcilable_enriched) 
    WHERE yango_payment_status = 'PAID_MISAPPLIED';

-- Índices adicionales para otras consultas comunes
CREATE INDEX IF NOT EXISTS idx_mv_yango_cabinet_claims_payment_status 
    ON ops.mv_yango_cabinet_claims_for_collection(yango_payment_status);
    
CREATE INDEX IF NOT EXISTS idx_mv_yango_cabinet_claims_reconcilable 
    ON ops.mv_yango_cabinet_claims_for_collection(is_reconcilable_enriched) 
    WHERE is_reconcilable_enriched = true;

CREATE INDEX IF NOT EXISTS idx_mv_yango_cabinet_claims_driver_milestone 
    ON ops.mv_yango_cabinet_claims_for_collection(driver_id, milestone_value) 
    WHERE driver_id IS NOT NULL;

CREATE INDEX IF NOT EXISTS idx_mv_yango_cabinet_claims_expected_amount 
    ON ops.mv_yango_cabinet_claims_for_collection(expected_amount DESC);

