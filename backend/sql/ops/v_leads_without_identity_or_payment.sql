-- ============================================================================
-- Vista: ops.v_leads_without_identity_or_payment
-- ============================================================================
-- PROPÓSITO:
-- Identifica leads de cabinet que NO tienen identidad canónica ni claims generados.
-- Esta es la métrica del "primer gap del embudo": leads que se registraron pero
-- no lograron tener identidad ni generar pago.
-- 
-- Esta vista responde: "¿Cuántos leads se perdieron en el primer paso del embudo?"
-- ============================================================================
-- GRANO:
-- 1 fila por lead (external_id o id) que no tiene identidad ni claims
-- ============================================================================
-- FUENTES:
-- - public.module_ct_cabinet_leads (leads registrados)
-- - canon.identity_links (vínculos de identidad)
-- - ops.v_claims_payment_status_cabinet (claims generados)
-- ============================================================================

DROP VIEW IF EXISTS ops.v_leads_without_identity_or_payment CASCADE;

CREATE VIEW ops.v_leads_without_identity_or_payment AS
WITH leads_with_identity AS (
    -- Leads que tienen identidad canónica
    SELECT DISTINCT
        COALESCE(mcl.external_id::text, mcl.id::text) AS lead_source_pk,
        il.person_key,
        il.match_rule,
        il.match_score,
        il.confidence_level
    FROM public.module_ct_cabinet_leads mcl
    INNER JOIN canon.identity_links il
        ON il.source_table = 'module_ct_cabinet_leads'
        AND il.source_pk = COALESCE(mcl.external_id::text, mcl.id::text)
),
leads_with_claims AS (
    -- Leads que tienen claims generados (a través de su identidad)
    SELECT DISTINCT
        COALESCE(mcl.external_id::text, mcl.id::text) AS lead_source_pk
    FROM public.module_ct_cabinet_leads mcl
    INNER JOIN canon.identity_links il
        ON il.source_table = 'module_ct_cabinet_leads'
        AND il.source_pk = COALESCE(mcl.external_id::text, mcl.id::text)
    INNER JOIN ops.v_claims_payment_status_cabinet c
        ON c.person_key = il.person_key
        AND c.driver_id IS NOT NULL
)
SELECT 
    mcl.id,
    mcl.external_id,
    mcl.first_name,
    mcl.middle_name,
    mcl.last_name,
    CONCAT(
        COALESCE(mcl.first_name, ''),
        CASE WHEN mcl.middle_name IS NOT NULL THEN ' ' || mcl.middle_name ELSE '' END,
        CASE WHEN mcl.last_name IS NOT NULL THEN ' ' || mcl.last_name ELSE '' END
    ) AS full_name,
    mcl.park_phone,
    mcl.asset_plate_number,
    mcl.asset_model,
    mcl.asset_color,
    mcl.lead_created_at,
    mcl.status,
    mcl.activation_city,
    mcl.target_city,
    -- Flags de estado
    CASE 
        WHEN li.person_key IS NOT NULL THEN true 
        ELSE false 
    END AS has_identity,
    CASE 
        WHEN lc.lead_source_pk IS NOT NULL THEN true 
        ELSE false 
    END AS has_claims,
    -- Información de identidad (si existe)
    li.person_key,
    li.match_rule,
    li.match_score,
    li.confidence_level,
    -- Razón del gap
    CASE 
        WHEN li.person_key IS NULL AND lc.lead_source_pk IS NULL THEN 'Sin identidad ni claims'
        WHEN li.person_key IS NULL THEN 'Sin identidad (pero tiene claims - anomalía)'
        WHEN lc.lead_source_pk IS NULL THEN 'Con identidad pero sin claims'
        ELSE 'Con identidad y claims'
    END AS gap_reason
FROM public.module_ct_cabinet_leads mcl
LEFT JOIN leads_with_identity li
    ON li.lead_source_pk = COALESCE(mcl.external_id::text, mcl.id::text)
LEFT JOIN leads_with_claims lc
    ON lc.lead_source_pk = COALESCE(mcl.external_id::text, mcl.id::text)
WHERE 
    -- Solo leads que NO tienen identidad O NO tienen claims
    -- Esto incluye el GAP 1 (sin identidad) y otros gaps (con identidad pero sin claims)
    (li.person_key IS NULL OR lc.lead_source_pk IS NULL)
ORDER BY mcl.lead_created_at DESC;

-- NOTA IMPORTANTE:
-- Esta vista muestra TODOS los leads que tienen algún gap.
-- Para ver SOLO el GAP 1 (sin identidad), filtrar: WHERE li.person_key IS NULL
-- Para ver SOLO el GAP crítico (sin identidad ni claims), filtrar: WHERE li.person_key IS NULL AND lc.lead_source_pk IS NULL

COMMENT ON VIEW ops.v_leads_without_identity_or_payment IS 
'Vista que identifica leads de cabinet que NO tienen identidad canónica ni claims generados. 
Representa el "primer gap del embudo": leads que se registraron pero no lograron tener identidad ni generar pago.
Útil para identificar problemas en el proceso de matching o datos incompletos.';

COMMENT ON COLUMN ops.v_leads_without_identity_or_payment.has_identity IS 
'Indica si el lead tiene identidad canónica (person_key).';

COMMENT ON COLUMN ops.v_leads_without_identity_or_payment.has_claims IS 
'Indica si el lead tiene claims generados (a través de su identidad).';

COMMENT ON COLUMN ops.v_leads_without_identity_or_payment.gap_reason IS 
'Razón del gap: "Sin identidad ni claims" (primer gap), "Sin identidad" (anomalía), "Con identidad pero sin claims" (gap posterior).';

