-- ============================================================================
-- BACKFILL: Scout ID desde cabinet_leads a lead_events (CATEGORÍA A)
-- ============================================================================
-- OBJETIVO: Para eventos sin scout_id, intentar backfill desde cabinet_leads
-- REGLA: Solo si hay mapping 1:1 confiable (ej referral_link_id → scouts_list)
-- EJECUCIÓN: Idempotente (solo actualiza si scout_id es NULL)
-- ============================================================================

-- ============================================================================
-- PASO 1: Verificar si existe tabla scouts_list con mapping confiable
-- ============================================================================

-- Por ahora, NO hacemos backfill automático desde cabinet_leads
-- porque no hay mapping 1:1 confiable verificable.
-- En su lugar, se crea una vista de alertas para revisión manual.

-- Este script está preparado para cuando exista un mapping confiable.
-- Ejemplo de implementación futura:

/*
CREATE OR REPLACE TEMP VIEW v_cabinet_leads_with_scout_mapping AS
SELECT 
    cl.id AS cabinet_lead_id,
    cl.external_id,
    il.person_key,
    le.id AS lead_event_id,
    sl.id AS scout_id,
    'referral_link_id' AS mapping_method
FROM public.module_ct_cabinet_leads cl
INNER JOIN canon.identity_links il 
    ON il.source_table = 'module_ct_cabinet_leads'
    AND il.source_pk = COALESCE(cl.external_id, cl.id::TEXT)
INNER JOIN observational.lead_events le 
    ON le.person_key = il.person_key
    AND le.source_table = 'module_ct_cabinet_leads'
    AND le.source_pk = COALESCE(cl.external_id, cl.id::TEXT)
INNER JOIN public.module_ct_scouts_list sl 
    ON sl.referral_link_id = cl.referral_link_id  -- Ejemplo de mapping
WHERE le.scout_id IS NULL
    AND (le.payload_json IS NULL OR le.payload_json->>'scout_id' IS NULL)
    AND cl.referral_link_id IS NOT NULL
    -- Verificar que sea mapping 1:1 (exactamente 1 scout por referral_link_id)
    AND (
        SELECT COUNT(DISTINCT s2.id)
        FROM public.module_ct_scouts_list s2
        WHERE s2.referral_link_id = cl.referral_link_id
    ) = 1;

-- Actualizar lead_events con scout_id encontrado
DO $$
DECLARE
    updated_count INTEGER := 0;
    audit_count INTEGER := 0;
    rec RECORD;
BEGIN
    FOR rec IN SELECT * FROM v_cabinet_leads_with_scout_mapping
    LOOP
        UPDATE observational.lead_events
        SET 
            scout_id = rec.scout_id,
            payload_json = COALESCE(payload_json, '{}'::JSONB) || jsonb_build_object(
                'backfill_method', 'BACKFILL_FROM_CABINET_LEADS',
                'backfill_timestamp', NOW(),
                'mapping_method', rec.mapping_method
            ),
            updated_at = NOW()
        WHERE id = rec.lead_event_id
            AND scout_id IS NULL;
        
        IF FOUND THEN
            updated_count := updated_count + 1;
            
            INSERT INTO ops.lead_events_scout_backfill_audit (
                source_table,
                source_pk,
                person_key,
                old_scout_id,
                new_scout_id,
                mapping_method,
                mapping_confidence,
                action_type,
                evidence_json,
                notes
            )
            VALUES (
                'module_ct_cabinet_leads',
                rec.cabinet_lead_id::TEXT,
                rec.person_key,
                NULL,
                rec.scout_id,
                rec.mapping_method,
                'high',
                'UPDATED',
                jsonb_build_object(
                    'cabinet_lead_id', rec.cabinet_lead_id,
                    'external_id', rec.external_id,
                    'mapping_method', rec.mapping_method
                ),
                format('Backfill desde cabinet_leads: referral_link_id → scout_id=%%s', rec.scout_id)
            );
            
            audit_count := audit_count + 1;
        END IF;
    END LOOP;
    
    RAISE NOTICE 'Actualizados %% registros en lead_events', updated_count;
    RAISE NOTICE 'Registrados %% registros en auditoría', audit_count;
END $$;
*/

-- ============================================================================
-- POR AHORA: Solo crear alertas (ya existe vista en create_v_cabinet_leads_missing_scout_alerts.sql)
-- ============================================================================

SELECT 
    'INFO: Backfill desde cabinet_leads NO IMPLEMENTADO' AS status,
    'Requiere mapping 1:1 confiable (ej: referral_link_id → scouts_list.id)' AS reason,
    (SELECT COUNT(*) FROM ops.v_cabinet_leads_missing_scout_alerts) AS alerts_count
WHERE EXISTS (
    SELECT 1 FROM information_schema.views
    WHERE table_schema = 'ops' AND table_name = 'v_cabinet_leads_missing_scout_alerts'
);

COMMENT ON SCHEMA public IS 
'Backfill desde cabinet_leads requiere mapping 1:1 confiable. Por ahora, usar vista ops.v_cabinet_leads_missing_scout_alerts para revisión manual.';

