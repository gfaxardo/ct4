-- Vista de alertas de origen (stateless)
-- LEFT JOIN a ops.identity_origin_alert_state para estado de resolución/mute

CREATE OR REPLACE VIEW ops.v_identity_origin_alerts AS
WITH audit_data AS (
    SELECT 
        person_key,
        driver_id,
        origin_tag,
        violation_flag,
        violation_reason,
        recommended_action,
        resolution_status,
        first_seen_at,
        origin_confidence
    FROM ops.v_identity_origin_audit
    WHERE violation_flag = true
),
alert_severity AS (
    -- Calcular severidad según impacto
    SELECT 
        ad.*,
        CASE 
            WHEN ad.violation_reason IN ('missing_origin', 'multiple_origins') 
                AND ad.resolution_status NOT IN ('resolved_auto', 'resolved_manual', 'discarded')
            THEN 'high'  -- Afecta export/collection
            WHEN ad.violation_reason IN ('late_origin_link', 'orphan_lead')
                AND ad.resolution_status NOT IN ('resolved_auto', 'resolved_manual', 'discarded')
            THEN 'medium'  -- Afecta reporting
            WHEN ad.violation_reason = 'legacy_driver_unclassified'
            THEN 'low'  -- Solo calidad de datos
            ELSE 'low'
        END AS severity,
        CASE 
            WHEN ad.violation_reason IN ('missing_origin', 'multiple_origins') THEN 'export'
            WHEN ad.violation_reason IN ('late_origin_link', 'orphan_lead') THEN 'reporting'
            WHEN ad.violation_reason = 'legacy_driver_unclassified' THEN 'none'
            ELSE 'none'
        END AS impact,
        CASE 
            WHEN ad.violation_reason = 'missing_origin' THEN 'missing_origin'
            WHEN ad.violation_reason = 'multiple_origins' THEN 'multiple_origins'
            WHEN ad.violation_reason = 'legacy_driver_unclassified' THEN 'legacy_unclassified'
            WHEN ad.violation_reason = 'orphan_lead' THEN 'orphan_lead'
            ELSE 'missing_origin'
        END AS alert_type
    FROM audit_data ad
)
SELECT 
    ROW_NUMBER() OVER (ORDER BY asv.person_key, asv.alert_type) AS alert_id,
    asv.person_key,
    asv.driver_id,
    asv.alert_type::text AS alert_type,
    asv.violation_reason,
    asv.recommended_action,
    asv.severity::text AS severity,
    asv.impact::text AS impact,
    asv.origin_tag,
    asv.origin_confidence,
    asv.first_seen_at,
    -- Estado desde alert_state
    aos.first_detected_at,
    aos.last_detected_at,
    aos.resolved_at,
    aos.resolved_by,
    aos.muted_until,
    aos.notes AS alert_notes,
    -- Flags derivados
    CASE 
        WHEN aos.resolved_at IS NOT NULL THEN true
        WHEN aos.muted_until IS NOT NULL AND aos.muted_until > NOW() THEN true
        ELSE false
    END AS is_resolved_or_muted,
    asv.resolution_status
FROM alert_severity asv
LEFT JOIN ops.identity_origin_alert_state aos ON (
    aos.person_key = asv.person_key 
    AND aos.alert_type::text = asv.alert_type
)
WHERE asv.resolution_status NOT IN ('resolved_auto', 'resolved_manual', 'discarded', 'marked_legacy')
    AND (aos.resolved_at IS NULL OR aos.resolved_at IS NOT NULL)  -- Incluir todos para auditoría
    AND (aos.muted_until IS NULL OR aos.muted_until <= NOW());  -- Solo si no está muteado

COMMENT ON VIEW ops.v_identity_origin_alerts IS 
'Vista de alertas de origen (stateless). LEFT JOIN a ops.identity_origin_alert_state para estado. '
'Filtra por resolution_status y muted_until. '
'Severidad: high=export/collection, medium=reporting, low=data_hygiene.';

