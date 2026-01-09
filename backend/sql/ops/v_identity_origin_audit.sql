-- Vista de auditoría de origen canónico
-- Detecta violaciones del contrato canónico de origen
-- NO afecta claims ni pagos, solo auditoría C0/C1

CREATE OR REPLACE VIEW ops.v_identity_origin_audit AS
WITH person_links AS (
    -- Agrupar todos los links por person_key
    SELECT 
        il.person_key,
        il.source_table,
        il.source_pk,
        il.match_rule,
        il.match_score,
        il.confidence_level,
        il.linked_at,
        il.snapshot_date,
        il.evidence
    FROM canon.identity_links il
),
person_summary AS (
    -- Resumen de links por persona
    SELECT 
        pl.person_key,
        -- Driver info
        MAX(CASE WHEN pl.source_table = 'drivers' THEN pl.source_pk END) AS driver_id,
        MIN(CASE WHEN pl.source_table = 'drivers' THEN pl.linked_at END) AS driver_linked_at,
        -- Lead links
        BOOL_OR(pl.source_table IN ('module_ct_cabinet_leads', 'module_ct_scouting_daily', 'module_ct_migrations')) AS has_lead_links,
        MIN(CASE 
            WHEN pl.source_table IN ('module_ct_cabinet_leads', 'module_ct_scouting_daily', 'module_ct_migrations') 
            THEN pl.linked_at 
        END) AS first_lead_linked_at,
        -- First seen at (prioridad: driver_linked_at, first_activity_at, registry_created_at)
        LEAST(
            MIN(pl.linked_at),
            MIN(CASE WHEN pl.source_table = 'drivers' THEN pl.linked_at END),
            (SELECT created_at FROM canon.identity_registry ir WHERE ir.person_key = pl.person_key)
        ) AS first_seen_at,
        -- Links summary
        jsonb_agg(
            jsonb_build_object(
                'source_table', pl.source_table,
                'source_pk', pl.source_pk,
                'match_rule', pl.match_rule,
                'match_score', pl.match_score,
                'confidence_level', pl.confidence_level::text,
                'linked_at', pl.linked_at,
                'snapshot_date', pl.snapshot_date
            ) ORDER BY pl.linked_at
        ) AS links_summary
    FROM person_links pl
    GROUP BY pl.person_key
),
origin_info AS (
    -- Información de origen desde canon.identity_origin
    SELECT 
        io.person_key,
        io.origin_tag::text AS origin_tag,
        io.origin_source_id,
        io.origin_confidence,
        io.origin_created_at,
        io.ruleset_version,
        io.evidence AS origin_evidence,
        io.decided_by::text AS decided_by,
        io.decided_at,
        io.resolution_status::text AS resolution_status,
        io.notes
    FROM canon.identity_origin io
),
inferred_origin AS (
    -- Inferir origen desde links si no existe en identity_origin
    SELECT 
        ps.person_key,
        CASE 
            WHEN EXISTS (
                SELECT 1 FROM person_links pl 
                WHERE pl.person_key = ps.person_key 
                AND pl.source_table = 'module_ct_cabinet_leads'
            ) THEN 'cabinet_lead'
            WHEN EXISTS (
                SELECT 1 FROM person_links pl 
                WHERE pl.person_key = ps.person_key 
                AND pl.source_table = 'module_ct_scouting_daily'
            ) THEN 'scout_registration'
            WHEN EXISTS (
                SELECT 1 FROM person_links pl 
                WHERE pl.person_key = ps.person_key 
                AND pl.source_table = 'module_ct_migrations'
            ) THEN 'migration'
            WHEN ps.driver_id IS NOT NULL 
                AND ps.first_seen_at::date < CURRENT_DATE - INTERVAL '90 days'  -- Aproximación, usar LEAD_SYSTEM_START_DATE en aplicación
                AND NOT ps.has_lead_links
            THEN 'legacy_external'
            ELSE NULL
        END AS inferred_origin_tag,
        CASE 
            WHEN EXISTS (
                SELECT 1 FROM person_links pl 
                WHERE pl.person_key = ps.person_key 
                AND pl.source_table = 'module_ct_cabinet_leads'
            ) THEN (
                SELECT pl.source_pk FROM person_links pl 
                WHERE pl.person_key = ps.person_key 
                AND pl.source_table = 'module_ct_cabinet_leads'
                ORDER BY pl.linked_at LIMIT 1
            )
            WHEN EXISTS (
                SELECT 1 FROM person_links pl 
                WHERE pl.person_key = ps.person_key 
                AND pl.source_table = 'module_ct_scouting_daily'
            ) THEN (
                SELECT pl.source_pk FROM person_links pl 
                WHERE pl.person_key = ps.person_key 
                AND pl.source_table = 'module_ct_scouting_daily'
                ORDER BY pl.linked_at LIMIT 1
            )
            WHEN EXISTS (
                SELECT 1 FROM person_links pl 
                WHERE pl.person_key = ps.person_key 
                AND pl.source_table = 'module_ct_migrations'
            ) THEN (
                SELECT pl.source_pk FROM person_links pl 
                WHERE pl.person_key = ps.person_key 
                AND pl.source_table = 'module_ct_migrations'
                ORDER BY pl.linked_at LIMIT 1
            )
            WHEN ps.driver_id IS NOT NULL THEN ps.driver_id
            ELSE NULL
        END AS inferred_origin_source_id
    FROM person_summary ps
),
violation_detection AS (
    -- Detectar violaciones
    SELECT 
        ps.person_key,
        ps.driver_id,
        ps.has_lead_links,
        ps.first_seen_at,
        ps.driver_linked_at,
        ps.first_lead_linked_at,
        ps.links_summary,
        -- Origen (desde identity_origin o inferido)
        COALESCE(oi.origin_tag, inf.inferred_origin_tag) AS origin_tag,
        COALESCE(oi.origin_source_id, inf.inferred_origin_source_id) AS origin_source_id,
        COALESCE(oi.origin_confidence, 0.0) AS origin_confidence,
        COALESCE(oi.origin_created_at, ps.first_seen_at) AS origin_created_at,
        oi.ruleset_version,
        oi.origin_evidence,
        oi.decided_by,
        oi.decided_at,
        oi.resolution_status,
        oi.notes,
        -- Violation detection
        CASE 
            WHEN COALESCE(oi.origin_tag, inf.inferred_origin_tag) IS NULL THEN true
            ELSE false
        END AS violation_flag,
        CASE 
            WHEN COALESCE(oi.origin_tag, inf.inferred_origin_tag) IS NULL THEN 'missing_origin'
            WHEN (
                SELECT COUNT(DISTINCT CASE 
                    WHEN pl.source_table = 'module_ct_cabinet_leads' THEN 'cabinet_lead'
                    WHEN pl.source_table = 'module_ct_scouting_daily' THEN 'scout_registration'
                    WHEN pl.source_table = 'module_ct_migrations' THEN 'migration'
                END)
                FROM person_links pl
                WHERE pl.person_key = ps.person_key
                AND pl.source_table IN ('module_ct_cabinet_leads', 'module_ct_scouting_daily', 'module_ct_migrations')
            ) > 1 THEN 'multiple_origins'
            WHEN ps.driver_linked_at IS NOT NULL 
                AND ps.first_lead_linked_at IS NOT NULL
                AND ps.driver_linked_at < ps.first_lead_linked_at THEN 'late_origin_link'
            WHEN ps.has_lead_links 
                AND ps.driver_id IS NULL THEN 'orphan_lead'
            WHEN ps.driver_id IS NOT NULL 
                AND NOT ps.has_lead_links
                AND inf.inferred_origin_tag = 'legacy_external' THEN 'legacy_driver_unclassified'
            ELSE NULL
        END AS violation_reason,
        CASE 
            WHEN COALESCE(oi.origin_tag, inf.inferred_origin_tag) IS NULL THEN 'manual_review'
            WHEN (
                SELECT COUNT(DISTINCT CASE 
                    WHEN pl.source_table = 'module_ct_cabinet_leads' THEN 'cabinet_lead'
                    WHEN pl.source_table = 'module_ct_scouting_daily' THEN 'scout_registration'
                    WHEN pl.source_table = 'module_ct_migrations' THEN 'migration'
                END)
                FROM person_links pl
                WHERE pl.person_key = ps.person_key
                AND pl.source_table IN ('module_ct_cabinet_leads', 'module_ct_scouting_daily', 'module_ct_migrations')
            ) > 1 THEN 'manual_review'
            WHEN ps.driver_linked_at IS NOT NULL 
                AND ps.first_lead_linked_at IS NOT NULL
                AND ps.driver_linked_at < ps.first_lead_linked_at THEN 'auto_link'
            WHEN ps.has_lead_links 
                AND ps.driver_id IS NULL THEN 'auto_link'
            WHEN ps.driver_id IS NOT NULL 
                AND NOT ps.has_lead_links
                AND inf.inferred_origin_tag = 'legacy_external' THEN 'mark_legacy'
            ELSE 'auto_link'
        END AS recommended_action
    FROM person_summary ps
    LEFT JOIN origin_info oi ON oi.person_key = ps.person_key
    LEFT JOIN inferred_origin inf ON inf.person_key = ps.person_key
)
SELECT 
    vd.person_key,
    vd.driver_id,
    vd.origin_tag,
    vd.origin_source_id,
    vd.origin_confidence,
    vd.origin_created_at,
    vd.ruleset_version,
    vd.origin_evidence,
    vd.decided_by,
    vd.decided_at,
    vd.resolution_status,
    vd.notes,
    vd.first_seen_at,
    vd.driver_linked_at,
    vd.has_lead_links,
    vd.links_summary,
    vd.violation_flag,
    vd.violation_reason::text AS violation_reason,
    vd.recommended_action::text AS recommended_action
FROM violation_detection vd;

COMMENT ON VIEW ops.v_identity_origin_audit IS 
'Vista de auditoría de origen canónico. Detecta violaciones del contrato canónico de origen. '
'NO afecta claims ni pagos, solo auditoría C0/C1. '
'Campos clave: violation_flag, violation_reason, recommended_action, resolution_status.';

