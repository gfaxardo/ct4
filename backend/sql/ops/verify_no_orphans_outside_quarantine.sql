-- ============================================================================
-- Verificación de Integridad: No Drivers sin Leads fuera de Cuarentena
-- ============================================================================
-- PROPÓSITO:
-- Verificar que NO existen drivers operativos sin leads asociados (excepto en cuarentena).
-- Este query debe retornar 0 filas en un sistema saludable.
-- ============================================================================
-- CRITERIO DE ACEPTACIÓN:
-- - drivers_without_leads operativos = 0 (excepto quarantined)
-- - Todos los drivers en cuarentena tienen audit trail completo
-- ============================================================================

-- Query de verificación principal
SELECT 
    'ERROR: Drivers sin leads fuera de cuarentena' as check_name,
    COUNT(*) as violation_count,
    array_agg(DISTINCT il.match_rule) as rules_found,
    array_agg(DISTINCT il.source_pk) FILTER (WHERE il.source_pk IS NOT NULL) as sample_driver_ids
FROM canon.identity_links il
WHERE il.source_table = 'drivers'
AND il.person_key NOT IN (
    SELECT DISTINCT person_key
    FROM canon.identity_links
    WHERE source_table IN ('module_ct_cabinet_leads', 'module_ct_scouting_daily', 'module_ct_migrations')
)
AND il.source_pk NOT IN (
    SELECT driver_id 
    FROM canon.driver_orphan_quarantine 
    WHERE status = 'quarantined'
);

-- Query detallado (si hay violaciones)
SELECT 
    il.source_pk as driver_id,
    il.person_key,
    il.match_rule as creation_rule,
    il.linked_at,
    il.evidence,
    CASE 
        WHEN EXISTS (
            SELECT 1 
            FROM canon.driver_orphan_quarantine q 
            WHERE q.driver_id = il.source_pk
        ) THEN 'IN_QUARANTINE'
        ELSE 'NOT_QUARANTINED'
    END as quarantine_status
FROM canon.identity_links il
WHERE il.source_table = 'drivers'
AND il.person_key NOT IN (
    SELECT DISTINCT person_key
    FROM canon.identity_links
    WHERE source_table IN ('module_ct_cabinet_leads', 'module_ct_scouting_daily', 'module_ct_migrations')
)
AND il.source_pk NOT IN (
    SELECT driver_id 
    FROM canon.driver_orphan_quarantine 
    WHERE status = 'quarantined'
)
ORDER BY il.linked_at DESC
LIMIT 100;

-- Query de resumen por regla
SELECT 
    il.match_rule,
    COUNT(*) as count,
    COUNT(*) FILTER (WHERE il.source_pk IN (
        SELECT driver_id FROM canon.driver_orphan_quarantine WHERE status = 'quarantined'
    )) as in_quarantine,
    COUNT(*) FILTER (WHERE il.source_pk NOT IN (
        SELECT driver_id FROM canon.driver_orphan_quarantine WHERE status = 'quarantined'
    )) as not_quarantined
FROM canon.identity_links il
WHERE il.source_table = 'drivers'
AND il.person_key NOT IN (
    SELECT DISTINCT person_key
    FROM canon.identity_links
    WHERE source_table IN ('module_ct_cabinet_leads', 'module_ct_scouting_daily', 'module_ct_migrations')
)
GROUP BY il.match_rule
ORDER BY count DESC;

-- Verificar que las vistas operativas excluyen drivers en cuarentena
SELECT 
    'Verificación: Vista funnel excluye drivers en cuarentena' as check_name,
    COUNT(*) as drivers_in_quarantine_but_in_funnel
FROM ops.v_cabinet_funnel_status vfs
WHERE vfs.driver_id IN (
    SELECT driver_id 
    FROM canon.driver_orphan_quarantine 
    WHERE status = 'quarantined'
);
-- Este query debe retornar 0 filas



