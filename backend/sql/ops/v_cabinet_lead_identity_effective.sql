-- ============================================================================
-- Vista: ops.v_cabinet_lead_identity_effective
-- ============================================================================
-- PROPÓSITO:
-- Vista auxiliar que define "identidad efectiva Cabinet" para cada lead.
-- Determina si un lead tiene identidad efectiva (person_key + origin correcto).
-- ============================================================================
-- GRANO:
-- 1 fila por lead_id
-- ============================================================================
-- DEFINICIÓN:
-- - person_key_effective existe si hay vínculo canónico lead_id -> person_key 
--   (en canon.identity_links con source_table='module_ct_cabinet_leads')
-- - identity_effective = person_key_effective IS NOT NULL
-- - identity_link_source indica si el link es existente o recuperado
-- ============================================================================

CREATE OR REPLACE VIEW ops.v_cabinet_lead_identity_effective AS
WITH cabinet_leads AS (
    -- Base: todos los leads cabinet
    SELECT 
        COALESCE(cl.external_id, cl.id::TEXT) AS lead_id,
        cl.id AS lead_id_raw,
        cl.lead_created_at::DATE AS lead_date
    FROM public.module_ct_cabinet_leads cl
),
identity_links AS (
    -- Obtener person_key desde identity_links
    SELECT DISTINCT ON (il.source_pk)
        il.source_pk AS lead_id,
        il.person_key,
        il.linked_at
    FROM canon.identity_links il
    WHERE il.source_table = 'module_ct_cabinet_leads'
    ORDER BY il.source_pk, il.linked_at DESC
)
SELECT 
    cl.lead_id,
    cl.lead_date,
    il.person_key AS person_key_effective,
    -- identity_link_source: indica si el link es existente o recuperado
    CASE 
        WHEN il.person_key IS NOT NULL THEN 'existing_link'
        ELSE 'none'
    END AS identity_link_source,
    -- identity_effective: TRUE si tiene person_key
    (il.person_key IS NOT NULL) AS identity_effective
FROM cabinet_leads cl
LEFT JOIN identity_links il ON il.lead_id = cl.lead_id;

-- ============================================================================
-- Comentarios de la Vista
-- ============================================================================
COMMENT ON VIEW ops.v_cabinet_lead_identity_effective IS 
'Vista auxiliar que define "identidad efectiva Cabinet" para cada lead. Determina si un lead tiene identidad efectiva (person_key). Grano: 1 fila por lead_id.';

COMMENT ON COLUMN ops.v_cabinet_lead_identity_effective.lead_id IS 
'ID del lead (external_id o id). Grano principal de la vista.';

COMMENT ON COLUMN ops.v_cabinet_lead_identity_effective.lead_date IS 
'Fecha de creación del lead (lead_created_at::DATE).';

COMMENT ON COLUMN ops.v_cabinet_lead_identity_effective.person_key_effective IS 
'Person key asignado al lead desde canon.identity_links. NULL si no tiene identidad.';

COMMENT ON COLUMN ops.v_cabinet_lead_identity_effective.identity_link_source IS 
'Origen del vínculo: existing_link (tiene person_key), none (no tiene person_key).';

COMMENT ON COLUMN ops.v_cabinet_lead_identity_effective.identity_effective IS 
'Flag indicando si el lead tiene identidad efectiva (person_key IS NOT NULL).';
