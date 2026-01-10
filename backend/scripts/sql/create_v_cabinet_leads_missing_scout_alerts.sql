-- ============================================================================
-- VISTA: ops.v_cabinet_leads_missing_scout_alerts
-- ============================================================================
-- Propósito: Alertas para cabinet_leads sin scout_id mapeado
-- Ejecución: Idempotente (DROP + CREATE)
-- ============================================================================

DROP VIEW IF EXISTS ops.v_cabinet_leads_missing_scout_alerts CASCADE;

CREATE VIEW ops.v_cabinet_leads_missing_scout_alerts AS
SELECT 
    cl.id AS cabinet_lead_id,
    cl.external_id,
    cl.lead_created_at,
    il.person_key,
    NULL::INTEGER AS potential_scout_id,
    -- Verificar si hay eventos con scout para este person_key
    EXISTS (
        SELECT 1 FROM observational.lead_events le
        WHERE le.person_key = il.person_key
            AND (le.scout_id IS NOT NULL OR (le.payload_json IS NOT NULL AND le.payload_json->>'scout_id' IS NOT NULL))
    ) AS has_scout_in_events
FROM public.module_ct_cabinet_leads cl
INNER JOIN canon.identity_links il ON il.source_table = 'module_ct_cabinet_leads'
    AND il.source_pk = COALESCE(cl.external_id, cl.id::TEXT)
WHERE NOT EXISTS (
    -- Excluir si ya tiene scout satisfactorio
    SELECT 1 FROM observational.lead_ledger ll
    WHERE ll.person_key = il.person_key
        AND ll.attributed_scout_id IS NOT NULL
)
AND NOT EXISTS (
    -- Excluir si ya tiene scout en eventos
    SELECT 1 FROM observational.lead_events le
    WHERE le.person_key = il.person_key
        AND (le.scout_id IS NOT NULL OR (le.payload_json IS NOT NULL AND le.payload_json->>'scout_id' IS NOT NULL))
);

COMMENT ON VIEW ops.v_cabinet_leads_missing_scout_alerts IS 
'Cabinet leads sin scout_id mapeado. Requiere investigación de referral_link_id, recruiter_id, utm o payload_json para encontrar scout.';
