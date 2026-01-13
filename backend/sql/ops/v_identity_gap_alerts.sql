-- Vista de alertas de brechas de identidad (CORREGIDA)
-- Genera alertas para leads con problemas críticos de identidad
-- Actualizada para ser consistente con v_identity_gap_analysis corregida

CREATE OR REPLACE VIEW ops.v_identity_gap_alerts AS
SELECT 
    gap.lead_id,
    CASE 
        WHEN gap.gap_reason = 'no_identity' AND gap.gap_age_days >= 1 THEN 'over_24h_no_identity'
        WHEN gap.gap_reason IN ('no_identity', 'no_origin') AND gap.gap_age_days >= 7 THEN 'over_7d_unresolved'
        WHEN gap.gap_reason = 'inconsistent_origin' THEN 'inconsistent_origin'
        ELSE NULL
    END AS alert_type,
    gap.risk_level AS severity,
    gap.gap_age_days AS days_open,
    CASE 
        WHEN gap.gap_reason = 'no_identity' AND gap.gap_age_days >= 1 THEN 
            'Lead sin identidad por más de 24 horas. Reintentar matching automático.'
        WHEN gap.gap_reason IN ('no_identity', 'no_origin') AND gap.gap_age_days >= 7 THEN 
            'Lead sin resolver por más de 7 días. Revisión manual requerida.'
        WHEN gap.gap_reason = 'inconsistent_origin' THEN 
            'Lead tiene origin pero origin_source_id no coincide con lead_id. Revisión manual requerida.'
        ELSE NULL
    END AS suggested_action
FROM ops.v_identity_gap_analysis gap
WHERE gap.gap_reason != 'resolved'
    AND (
        (gap.gap_reason = 'no_identity' AND gap.gap_age_days >= 1) OR
        (gap.gap_reason IN ('no_identity', 'no_origin') AND gap.gap_age_days >= 7) OR
        (gap.gap_reason = 'inconsistent_origin')
    );

COMMENT ON VIEW ops.v_identity_gap_alerts IS 
'Alertas activas de brechas de identidad. Filtra leads con problemas críticos que requieren atención.';

COMMENT ON COLUMN ops.v_identity_gap_alerts.lead_id IS 
'ID del lead con problema';

COMMENT ON COLUMN ops.v_identity_gap_alerts.alert_type IS 
'Tipo de alerta: over_24h_no_identity, over_7d_unresolved, inconsistent_origin';

COMMENT ON COLUMN ops.v_identity_gap_alerts.severity IS 
'Nivel de severidad: high, medium, low';

COMMENT ON COLUMN ops.v_identity_gap_alerts.days_open IS 
'Días desde lead_date hasta hoy';

COMMENT ON COLUMN ops.v_identity_gap_alerts.suggested_action IS 
'Acción sugerida para resolver la alerta';
