-- ============================================================================
-- QUERY DE DEFENSA (DRILLDOWN): Evidencia para Defender el Cobro
-- ============================================================================
-- PROPÓSITO:
-- Dado un driver_id/person_key/milestone_value, mostrar evidencia suficiente
-- para defender el cobro usando las vistas existentes, sin crear nuevas reglas.
--
-- CASOS CUBIERTOS:
-- - PAID_MISAPPLIED: Claim original + pago encontrado en otro milestone
-- - UNPAID: Claim original + búsqueda de pagos en todos los milestones
-- - PAID: Claim original + pago encontrado correctamente
-- ============================================================================

-- ============================================================================
-- QUERY 4.1: Drilldown completo por driver_id y milestone_value
-- ============================================================================
-- Muestra evidencia completa: claim original, lead cabinet, pagos encontrados,
-- estado de reconciliación
-- ============================================================================

-- Ejemplo de uso: Reemplazar 'DRIVER_ID_AQUI' y MILESTONE_AQUI con valores reales
-- SELECT * FROM drilldown_claim('DRIVER_ID_AQUI', MILESTONE_AQUI);

-- Query parametrizable (usar con parámetros en aplicación)
WITH claim_info AS (
    SELECT 
        c.*
    FROM ops.mv_yango_cabinet_claims_for_collection c
    WHERE c.driver_id = :driver_id  -- Parámetro: driver_id
        AND c.milestone_value = :milestone_value  -- Parámetro: milestone_value
),
lead_cabinet_info AS (
    SELECT 
        il.person_key,
        il.source_table,
        il.source_pk,
        il.match_rule,
        il.match_score,
        il.confidence_level,
        il.linked_at
    FROM canon.identity_links il
    WHERE il.source_table = 'module_ct_cabinet_leads'
        AND il.person_key = (SELECT person_key FROM claim_info)
),
all_payments_for_driver AS (
    SELECT 
        p.*
    FROM ops.v_yango_payments_ledger_latest_enriched p
    WHERE p.driver_id_final = :driver_id  -- Parámetro: driver_id
        AND p.is_paid = true
),
reconciliation_status AS (
    SELECT 
        r.*
    FROM ops.v_yango_reconciliation_detail r
    WHERE r.driver_id = :driver_id  -- Parámetro: driver_id
        AND r.milestone_value = :milestone_value  -- Parámetro: milestone_value
)
SELECT 
    '=== QUERY 4.1: Drilldown Completo ===' AS seccion,
    -- Información del claim
    ci.driver_id AS "Driver ID",
    ci.person_key AS "Person Key",
    ci.milestone_value AS "Milestone Esperado",
    ci.expected_amount AS "Monto Esperado (S/)",
    ci.lead_date AS "Fecha Lead",
    ci.yango_due_date AS "Fecha Vencimiento",
    ci.days_overdue_yango AS "Días Vencidos",
    ci.yango_payment_status AS "Estado Pago",
    ci.reason_code AS "Razón",
    ci.identity_status AS "Estado Identidad",
    ci.match_rule AS "Regla Matching",
    ci.match_confidence AS "Confianza Matching",
    ci.is_reconcilable_enriched AS "Reconciliable",
    
    -- Información del lead cabinet
    lci.source_pk AS "Lead Cabinet ID",
    lci.match_rule AS "Lead Match Rule",
    lci.match_score AS "Lead Match Score",
    lci.confidence_level AS "Lead Confidence",
    lci.linked_at AS "Lead Linked At",
    
    -- Pagos encontrados para este driver (todos los milestones)
    (
        SELECT JSON_AGG(
            json_build_object(
                'payment_key', ap.payment_key,
                'milestone_value', ap.milestone_value,
                'pay_date', ap.pay_date,
                'is_paid', ap.is_paid,
                'identity_status', ap.identity_status,
                'match_rule', ap.match_rule,
                'match_confidence', ap.match_confidence
            )
        )
        FROM all_payments_for_driver ap
    ) AS "Todos los Pagos del Driver",
    
    -- Estado de reconciliación
    rs.reconciliation_status AS "Estado Reconciliación",
    rs.expected_amount AS "Reconciliation Expected Amount",
    rs.paid_payment_key AS "Reconciliation Payment Key",
    rs.paid_date AS "Reconciliation Paid Date"
    
FROM claim_info ci
LEFT JOIN lead_cabinet_info lci ON lci.person_key = ci.person_key
LEFT JOIN reconciliation_status rs ON rs.driver_id = ci.driver_id AND rs.milestone_value = ci.milestone_value;

-- ============================================================================
-- QUERY 4.2: Drilldown para PAID_MISAPPLIED
-- ============================================================================
-- Muestra: claim original (milestone esperado) + pago encontrado en otro milestone
-- + evidencia de identidad
-- ============================================================================

-- Ejemplo de uso: Reemplazar 'DRIVER_ID_AQUI' y MILESTONE_AQUI con valores reales
WITH claim_misapplied AS (
    SELECT 
        c.*
    FROM ops.mv_yango_cabinet_claims_for_collection c
    WHERE c.driver_id = :driver_id  -- Parámetro: driver_id
        AND c.milestone_value = :milestone_value  -- Parámetro: milestone_value
        AND c.yango_payment_status = 'PAID_MISAPPLIED'
        AND c.reason_code = 'payment_found_other_milestone'
),
payment_found_other_milestone AS (
    SELECT 
        p.*
    FROM ops.v_yango_payments_ledger_latest_enriched p
    WHERE p.payment_key = (SELECT payment_key FROM claim_misapplied)
        AND p.driver_id_final = (SELECT driver_id FROM claim_misapplied)
        AND p.is_paid = true
),
all_payments_driver AS (
    SELECT 
        p.milestone_value,
        p.payment_key,
        p.pay_date,
        p.is_paid,
        p.identity_status,
        p.match_rule,
        p.match_confidence
    FROM ops.v_yango_payments_ledger_latest_enriched p
    WHERE p.driver_id_final = (SELECT driver_id FROM claim_misapplied)
        AND p.is_paid = true
)
SELECT 
    '=== QUERY 4.2: Drilldown PAID_MISAPPLIED ===' AS seccion,
    -- Claim original
    cm.driver_id AS "Driver ID Claim",
    cm.milestone_value AS "Milestone Esperado",
    cm.expected_amount AS "Monto Esperado (S/)",
    cm.lead_date AS "Fecha Lead",
    cm.yango_due_date AS "Fecha Vencimiento",
    cm.days_overdue_yango AS "Días Vencidos",
    cm.payment_key AS "Payment Key Encontrado",
    cm.reason_code AS "Razón",
    
    -- Pago encontrado en otro milestone
    pfom.milestone_value AS "Milestone del Pago Encontrado",
    pfom.pay_date AS "Fecha del Pago",
    pfom.driver_id_final AS "Driver ID del Pago",
    pfom.person_key_final AS "Person Key del Pago",
    pfom.identity_status AS "Estado Identidad del Pago",
    pfom.match_rule AS "Regla Matching del Pago",
    pfom.match_confidence AS "Confianza Matching del Pago",
    pfom.raw_driver_name AS "Nombre Driver en Pago",
    
    -- Análisis de discrepancia
    CASE 
        WHEN cm.milestone_value != pfom.milestone_value THEN 'MILESTONE_MISMATCH'
        ELSE 'OK'
    END AS "Tipo Discrepancia",
    
    -- Evidencia de identidad
    CASE 
        WHEN cm.driver_id = pfom.driver_id_final THEN 'DRIVER_ID_MATCH'
        WHEN cm.person_key = pfom.person_key_final THEN 'PERSON_KEY_MATCH'
        ELSE 'NO_IDENTITY_MATCH'
    END AS "Tipo Match Identidad",
    
    -- Todos los pagos del driver (para contexto)
    (
        SELECT JSON_AGG(
            json_build_object(
                'milestone_value', apd.milestone_value,
                'payment_key', apd.payment_key,
                'pay_date', apd.pay_date,
                'identity_status', apd.identity_status,
                'match_rule', apd.match_rule
            )
        )
        FROM all_payments_driver apd
    ) AS "Todos los Pagos del Driver"
    
FROM claim_misapplied cm
LEFT JOIN payment_found_other_milestone pfom ON pfom.payment_key = cm.payment_key;

-- ============================================================================
-- QUERY 4.3: Drilldown para UNPAID
-- ============================================================================
-- Muestra: claim original + búsqueda de pagos en todos los milestones para
-- el mismo driver_id + razón de no pago
-- ============================================================================

-- Ejemplo de uso: Reemplazar 'DRIVER_ID_AQUI' y MILESTONE_AQUI con valores reales
WITH claim_unpaid AS (
    SELECT 
        c.*
    FROM ops.mv_yango_cabinet_claims_for_collection c
    WHERE c.driver_id = :driver_id  -- Parámetro: driver_id
        AND c.milestone_value = :milestone_value  -- Parámetro: milestone_value
        AND c.yango_payment_status = 'UNPAID'
),
all_payments_driver AS (
    SELECT 
        p.milestone_value,
        p.payment_key,
        p.pay_date,
        p.is_paid,
        p.identity_status,
        p.match_rule,
        p.match_confidence,
        p.driver_id_final,
        p.person_key_final
    FROM ops.v_yango_payments_ledger_latest_enriched p
    WHERE p.driver_id_final = (SELECT driver_id FROM claim_unpaid)
        AND p.is_paid = true
),
payments_by_milestone AS (
    SELECT 
        milestone_value,
        COUNT(*) AS count_payments,
        MAX(pay_date) AS last_pay_date,
        STRING_AGG(DISTINCT payment_key, ', ') AS payment_keys
    FROM all_payments_driver
    GROUP BY milestone_value
)
SELECT 
    '=== QUERY 4.3: Drilldown UNPAID ===' AS seccion,
    -- Claim original
    cu.driver_id AS "Driver ID",
    cu.milestone_value AS "Milestone Esperado",
    cu.expected_amount AS "Monto Esperado (S/)",
    cu.lead_date AS "Fecha Lead",
    cu.yango_due_date AS "Fecha Vencimiento",
    cu.days_overdue_yango AS "Días Vencidos",
    cu.reason_code AS "Razón No Pago",
    cu.identity_status AS "Estado Identidad",
    cu.match_rule AS "Regla Matching",
    cu.match_confidence AS "Confianza Matching",
    cu.is_reconcilable_enriched AS "Reconciliable",
    
    -- Búsqueda de pagos en todos los milestones
    (
        SELECT JSON_AGG(
            json_build_object(
                'milestone_value', pbm.milestone_value,
                'count_payments', pbm.count_payments,
                'last_pay_date', pbm.last_pay_date,
                'payment_keys', pbm.payment_keys
            )
        )
        FROM payments_by_milestone pbm
    ) AS "Pagos por Milestone",
    
    -- Total de pagos encontrados para este driver
    (SELECT COUNT(*) FROM all_payments_driver) AS "Total Pagos Driver",
    
    -- ¿Hay pago en otro milestone?
    CASE 
        WHEN EXISTS (
            SELECT 1 FROM all_payments_driver 
            WHERE milestone_value != (SELECT milestone_value FROM claim_unpaid)
        ) THEN 'SI: Hay pago en otro milestone'
        ELSE 'NO: No hay pagos en ningún milestone'
    END AS "Pago en Otro Milestone",
    
    -- Detalle de pagos encontrados
    (
        SELECT JSON_AGG(
            json_build_object(
                'milestone_value', apd.milestone_value,
                'payment_key', apd.payment_key,
                'pay_date', apd.pay_date,
                'identity_status', apd.identity_status,
                'match_rule', apd.match_rule,
                'match_confidence', apd.match_confidence
            )
        )
        FROM all_payments_driver apd
    ) AS "Detalle Pagos Encontrados"
    
FROM claim_unpaid cu;

-- ============================================================================
-- QUERY 4.4: Drilldown genérico (funciona para cualquier estado)
-- ============================================================================
-- Query genérica que funciona para PAID, UNPAID, o PAID_MISAPPLIED
-- ============================================================================

-- Ejemplo de uso: Reemplazar 'DRIVER_ID_AQUI' y MILESTONE_AQUI con valores reales
WITH claim_base AS (
    SELECT 
        c.*
    FROM ops.mv_yango_cabinet_claims_for_collection c
    WHERE c.driver_id = :driver_id  -- Parámetro: driver_id
        AND c.milestone_value = :milestone_value  -- Parámetro: milestone_value
),
lead_cabinet AS (
    SELECT 
        il.source_pk,
        il.match_rule,
        il.match_score,
        il.confidence_level,
        il.linked_at
    FROM canon.identity_links il
    WHERE il.source_table = 'module_ct_cabinet_leads'
        AND il.person_key = (SELECT person_key FROM claim_base)
),
payment_exact AS (
    SELECT 
        p.*
    FROM ops.v_yango_payments_ledger_latest_enriched p
    WHERE p.driver_id_final = (SELECT driver_id FROM claim_base)
        AND p.milestone_value = (SELECT milestone_value FROM claim_base)
        AND p.is_paid = true
    ORDER BY p.pay_date DESC
    LIMIT 1
),
payments_other_milestones AS (
    SELECT 
        p.*
    FROM ops.v_yango_payments_ledger_latest_enriched p
    WHERE p.driver_id_final = (SELECT driver_id FROM claim_base)
        AND p.milestone_value != (SELECT milestone_value FROM claim_base)
        AND p.is_paid = true
),
reconciliation AS (
    SELECT 
        r.*
    FROM ops.v_yango_reconciliation_detail r
    WHERE r.driver_id = (SELECT driver_id FROM claim_base)
        AND r.milestone_value = (SELECT milestone_value FROM claim_base)
)
SELECT 
    '=== QUERY 4.4: Drilldown Genérico ===' AS seccion,
    -- Información del claim
    cb.driver_id AS "Driver ID",
    cb.person_key AS "Person Key",
    cb.milestone_value AS "Milestone",
    cb.expected_amount AS "Monto Esperado (S/)",
    cb.lead_date AS "Fecha Lead",
    cb.yango_due_date AS "Fecha Vencimiento",
    cb.days_overdue_yango AS "Días Vencidos",
    cb.yango_payment_status AS "Estado Pago",
    cb.reason_code AS "Razón",
    cb.identity_status AS "Estado Identidad",
    cb.match_rule AS "Regla Matching",
    cb.match_confidence AS "Confianza Matching",
    cb.is_reconcilable_enriched AS "Reconciliable",
    
    -- Información del lead cabinet
    lc.source_pk AS "Lead Cabinet ID",
    lc.match_rule AS "Lead Match Rule",
    lc.match_score AS "Lead Match Score",
    lc.confidence_level AS "Lead Confidence",
    lc.linked_at AS "Lead Linked At",
    
    -- Pago exacto (si existe)
    pe.payment_key AS "Payment Key Exacto",
    pe.pay_date AS "Fecha Pago Exacto",
    pe.milestone_value AS "Milestone Pago Exacto",
    pe.identity_status AS "Estado Identidad Pago Exacto",
    pe.match_rule AS "Regla Matching Pago Exacto",
    
    -- Pagos en otros milestones (si existen)
    (
        SELECT JSON_AGG(
            json_build_object(
                'milestone_value', pom.milestone_value,
                'payment_key', pom.payment_key,
                'pay_date', pom.pay_date,
                'identity_status', pom.identity_status,
                'match_rule', pom.match_rule
            )
        )
        FROM payments_other_milestones pom
    ) AS "Pagos Otros Milestones",
    
    -- Estado de reconciliación
    rec.reconciliation_status AS "Estado Reconciliación",
    rec.expected_amount AS "Reconciliation Expected Amount",
    rec.paid_payment_key AS "Reconciliation Payment Key",
    rec.paid_date AS "Reconciliation Paid Date",
    rec.match_method AS "Reconciliation Match Method"
    
FROM claim_base cb
LEFT JOIN lead_cabinet lc ON lc.source_pk IS NOT NULL
LEFT JOIN payment_exact pe ON pe.payment_key IS NOT NULL
LEFT JOIN reconciliation rec ON rec.driver_id = cb.driver_id AND rec.milestone_value = cb.milestone_value;

-- ============================================================================
-- QUERY 4.5: Evidencia completa para auditoría
-- ============================================================================
-- Query que muestra TODA la evidencia disponible para un claim específico,
-- incluyendo trazabilidad completa desde el lead hasta el pago
-- ============================================================================

-- Ejemplo de uso: Reemplazar 'DRIVER_ID_AQUI' y MILESTONE_AQUI con valores reales
WITH claim_full AS (
    SELECT 
        c.*
    FROM ops.mv_yango_cabinet_claims_for_collection c
    WHERE c.driver_id = :driver_id  -- Parámetro: driver_id
        AND c.milestone_value = :milestone_value  -- Parámetro: milestone_value
),
lead_trace AS (
    SELECT 
        cl.id AS lead_id,
        cl.external_id AS lead_external_id,
        cl.lead_created_at AS lead_created_at,
        cl.park_phone AS lead_phone,
        cl.first_name || ' ' || COALESCE(cl.middle_name || ' ', '') || cl.last_name AS lead_name
    FROM public.module_ct_cabinet_leads cl
    WHERE cl.id IN (
        SELECT CAST(il.source_pk AS INTEGER)
        FROM canon.identity_links il
        WHERE il.source_table = 'module_ct_cabinet_leads'
            AND il.person_key = (SELECT person_key FROM claim_full)
    )
    LIMIT 1
),
identity_trace AS (
    SELECT 
        ir.person_key,
        ir.primary_phone,
        ir.primary_document,
        ir.primary_license,
        ir.primary_full_name,
        ir.confidence_level
    FROM canon.identity_registry ir
    WHERE ir.person_key = (SELECT person_key FROM claim_full)
),
payments_trace AS (
    SELECT 
        p.*
    FROM ops.v_yango_payments_ledger_latest_enriched p
    WHERE p.driver_id_final = (SELECT driver_id FROM claim_full)
        AND p.is_paid = true
)
SELECT 
    '=== QUERY 4.5: Evidencia Completa para Auditoría ===' AS seccion,
    -- Claim
    cf.driver_id AS "Driver ID",
    cf.milestone_value AS "Milestone",
    cf.expected_amount AS "Monto Esperado (S/)",
    cf.yango_payment_status AS "Estado Pago",
    cf.reason_code AS "Razón",
    
    -- Lead original
    lt.lead_id AS "Lead ID",
    lt.lead_external_id AS "Lead External ID",
    lt.lead_created_at AS "Lead Created At",
    lt.lead_phone AS "Lead Phone",
    lt.lead_name AS "Lead Name",
    
    -- Identidad canónica
    it.person_key AS "Person Key",
    it.primary_phone AS "Primary Phone",
    it.primary_document AS "Primary Document",
    it.primary_license AS "Primary License",
    it.primary_full_name AS "Primary Full Name",
    it.confidence_level AS "Confidence Level",
    
    -- Pagos encontrados
    (
        SELECT JSON_AGG(
            json_build_object(
                'payment_key', pt.payment_key,
                'milestone_value', pt.milestone_value,
                'pay_date', pt.pay_date,
                'is_paid', pt.is_paid,
                'driver_id_final', pt.driver_id_final,
                'person_key_final', pt.person_key_final,
                'identity_status', pt.identity_status,
                'match_rule', pt.match_rule,
                'match_confidence', pt.match_confidence,
                'raw_driver_name', pt.raw_driver_name
            )
        )
        FROM payments_trace pt
    ) AS "Pagos Encontrados"
    
FROM claim_full cf
LEFT JOIN lead_trace lt ON lt.lead_id IS NOT NULL
LEFT JOIN identity_trace it ON it.person_key = cf.person_key;

-- ============================================================================
-- NOTAS DE USO
-- ============================================================================
-- 1. Todas las queries usan parámetros :driver_id y :milestone_value
-- 2. En una aplicación, estos parámetros deben ser reemplazados por valores reales
-- 3. QUERY 4.1: Drilldown completo para cualquier estado
-- 4. QUERY 4.2: Específica para PAID_MISAPPLIED
-- 5. QUERY 4.3: Específica para UNPAID
-- 6. QUERY 4.4: Genérica que funciona para cualquier estado
-- 7. QUERY 4.5: Evidencia completa para auditoría (trazabilidad completa)
-- ============================================================================









