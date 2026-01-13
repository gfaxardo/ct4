-- ============================================================================
-- Vista: ops.v_driver_orphans
-- ============================================================================
-- PROPÓSITO:
-- Vista para mostrar drivers huérfanos en la UI con información detallada.
-- Incluye filtros por reason, status, y permite link a detalle del driver/persona.
-- ============================================================================

CREATE OR REPLACE VIEW ops.v_driver_orphans AS
SELECT 
    q.driver_id,
    q.person_key,
    q.detected_at,
    q.detected_reason,
    q.creation_rule,
    q.evidence_json,
    q.status,
    q.resolved_at,
    q.resolution_notes,
    -- Información adicional del driver/persona
    ir.primary_phone,
    ir.primary_license,
    ir.primary_full_name,
    ir.confidence_level,
    -- Información de links existentes
    (SELECT COUNT(*) 
     FROM canon.identity_links il 
     WHERE il.source_table = 'drivers' 
     AND il.source_pk = q.driver_id) AS driver_links_count,
    -- Lead events count
    (SELECT COUNT(*) 
     FROM observational.lead_events le 
     WHERE (le.payload_json->>'driver_id')::text = q.driver_id) AS lead_events_count,
    -- Última actualización
    q.detected_at AS last_updated_at
FROM canon.driver_orphan_quarantine q
LEFT JOIN canon.identity_registry ir ON ir.person_key = q.person_key
ORDER BY q.detected_at DESC;

-- ============================================================================
-- Comentarios de la Vista
-- ============================================================================
COMMENT ON VIEW ops.v_driver_orphans IS 
'Vista para mostrar drivers huérfanos en la UI con información detallada. Incluye filtros por reason, status, y permite link a detalle del driver/persona.';

COMMENT ON COLUMN ops.v_driver_orphans.driver_id IS 
'ID del conductor huérfano (PK)';

COMMENT ON COLUMN ops.v_driver_orphans.person_key IS 
'Person key asociado (si existe)';

COMMENT ON COLUMN ops.v_driver_orphans.detected_reason IS 
'Razón de detección: no_lead_no_events, no_lead_has_events_repair_failed, legacy_driver_without_origin, manual_detection';

COMMENT ON COLUMN ops.v_driver_orphans.status IS 
'Estado: quarantined, resolved_relinked, resolved_created_lead, purged';

COMMENT ON COLUMN ops.v_driver_orphans.lead_events_count IS 
'Número de lead_events asociados al driver';



