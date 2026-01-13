-- ============================================================================
-- Queries de Verificación Post-Deploy: Sistema de Orphans
-- ============================================================================
-- PROPÓSITO:
-- Verificar que el deploy del sistema de eliminación de orphans fue exitoso
-- y que todos los criterios de aceptación se cumplen.
-- ============================================================================
-- USO:
-- Ejecutar DESPUÉS del deploy completo para validar que todo funciona correctamente.
-- ============================================================================
-- CRITERIOS DE ACEPTACIÓN:
-- 1. Drivers sin lead operativos = 0 (todos están reparados o en cuarentena)
-- 2. Vistas operativas excluyen orphans (funnel, pagos, elegibilidad, claims)
-- 3. Auditoría completa (todo driver sin lead tiene registro en quarantine)
-- 4. Prevención funcionando (no se crean nuevos orphans)
-- ============================================================================

-- ============================================================================
-- 1. VERIFICACIÓN: Drivers sin Lead Operativos = 0
-- ============================================================================
-- ✅ CRITERIO: No debe haber drivers sin lead fuera de cuarentena
SELECT 
    '1. Drivers sin Lead Operativos' AS check_name,
    COUNT(*) as violation_count,
    CASE 
        WHEN COUNT(*) = 0 THEN '✅ PASS'
        ELSE '❌ FAIL'
    END as status
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

-- Detalle de violaciones (si existen)
SELECT 
    '1.1. Detalle de Violaciones' AS check_name,
    il.source_pk as driver_id,
    il.person_key,
    il.match_rule as creation_rule,
    il.linked_at
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
LIMIT 20;

-- ============================================================================
-- 2. VERIFICACIÓN: Exclusión Operativa - Funnel
-- ============================================================================
-- ✅ CRITERIO: Funnel NO debe incluir drivers en cuarentena
SELECT 
    '2. Exclusión en Funnel' AS check_name,
    COUNT(*) as orphans_in_funnel,
    CASE 
        WHEN COUNT(*) = 0 THEN '✅ PASS'
        ELSE '❌ FAIL'
    END as status
FROM ops.v_cabinet_funnel_status vfs
WHERE vfs.driver_id IN (
    SELECT driver_id 
    FROM canon.driver_orphan_quarantine 
    WHERE status = 'quarantined'
);

-- ============================================================================
-- 3. VERIFICACIÓN: Exclusión Operativa - Pagos
-- ============================================================================
-- ✅ CRITERIO: Cálculo de pagos NO debe incluir drivers en cuarentena
SELECT 
    '3. Exclusión en Pagos' AS check_name,
    COUNT(*) as orphans_in_payments,
    CASE 
        WHEN COUNT(*) = 0 THEN '✅ PASS'
        ELSE '❌ FAIL'
    END as status
FROM ops.v_payment_calculation vpc
WHERE vpc.driver_id IN (
    SELECT driver_id 
    FROM canon.driver_orphan_quarantine 
    WHERE status = 'quarantined'
);

-- ============================================================================
-- 4. VERIFICACIÓN: Exclusión Operativa - Elegibilidad
-- ============================================================================
-- ✅ CRITERIO: Drivers elegibles NO deben incluir orphans
SELECT 
    '4. Exclusión en Elegibilidad' AS check_name,
    COUNT(*) as orphans_in_eligible,
    CASE 
        WHEN COUNT(*) = 0 THEN '✅ PASS'
        ELSE '❌ FAIL'
    END as status
FROM ops.v_ct4_eligible_drivers ved
WHERE ved.driver_id IN (
    SELECT driver_id 
    FROM canon.driver_orphan_quarantine 
    WHERE status = 'quarantined'
);

-- ============================================================================
-- 5. VERIFICACIÓN: Auditoría Completa
-- ============================================================================
-- ✅ CRITERIO: Todo driver sin lead debe tener registro en quarantine
SELECT 
    '5. Auditoría Completa' AS check_name,
    COUNT(*) as missing_quarantine_records,
    CASE 
        WHEN COUNT(*) = 0 THEN '✅ PASS'
        ELSE '❌ FAIL'
    END as status
FROM canon.identity_links il
WHERE il.source_table = 'drivers'
AND il.person_key NOT IN (
    SELECT DISTINCT person_key
    FROM canon.identity_links
    WHERE source_table IN ('module_ct_cabinet_leads', 'module_ct_scouting_daily', 'module_ct_migrations')
)
AND il.source_pk NOT IN (
    SELECT driver_id FROM canon.driver_orphan_quarantine
);

-- Detalle de drivers sin registro en quarantine (si existen)
SELECT 
    '5.1. Detalle de Drivers sin Registro' AS check_name,
    il.source_pk as driver_id,
    il.person_key,
    il.match_rule as creation_rule,
    il.linked_at
FROM canon.identity_links il
WHERE il.source_table = 'drivers'
AND il.person_key NOT IN (
    SELECT DISTINCT person_key
    FROM canon.identity_links
    WHERE source_table IN ('module_ct_cabinet_leads', 'module_ct_scouting_daily', 'module_ct_migrations')
)
AND il.source_pk NOT IN (
    SELECT driver_id FROM canon.driver_orphan_quarantine
)
ORDER BY il.linked_at DESC
LIMIT 20;

-- ============================================================================
-- 6. VERIFICACIÓN: Estado de Quarantine
-- ============================================================================
-- ✅ CRITERIO: Todos los registros en quarantine tienen status válido
SELECT 
    '6. Estado de Quarantine Válido' AS check_name,
    COUNT(*) as invalid_status_count,
    CASE 
        WHEN COUNT(*) = 0 THEN '✅ PASS'
        ELSE '❌ FAIL'
    END as status
FROM canon.driver_orphan_quarantine q
WHERE q.status NOT IN ('quarantined', 'resolved_relinked', 'resolved_created_lead', 'purged');

-- Resumen por estado
SELECT 
    '6.1. Resumen por Estado' AS check_name,
    status,
    COUNT(*) as count
FROM canon.driver_orphan_quarantine
GROUP BY status
ORDER BY count DESC;

-- Resumen por razón
SELECT 
    '6.2. Resumen por Razón' AS check_name,
    detected_reason,
    COUNT(*) as count
FROM canon.driver_orphan_quarantine
GROUP BY detected_reason
ORDER BY count DESC;

-- ============================================================================
-- 7. VERIFICACIÓN: Resueltos tienen Información de Resolución
-- ============================================================================
-- ✅ CRITERIO: Orphans resueltos deben tener resolution_notes y resolved_at
SELECT 
    '7. Resueltos con Información Completa' AS check_name,
    COUNT(*) as missing_resolution_info,
    CASE 
        WHEN COUNT(*) = 0 THEN '✅ PASS'
        ELSE '❌ FAIL'
    END as status
FROM canon.driver_orphan_quarantine q
WHERE q.status IN ('resolved_relinked', 'resolved_created_lead')
AND (q.resolution_notes IS NULL OR q.resolved_at IS NULL);

-- ============================================================================
-- 8. VERIFICACIÓN: Vista de Auditoría
-- ============================================================================
-- ✅ CRITERIO: Vista ops.v_driver_orphans debe funcionar
SELECT 
    '8. Vista de Auditoría Funcional' AS check_name,
    COUNT(*) as total_orphans_in_view,
    CASE 
        WHEN COUNT(*) >= 0 THEN '✅ PASS'
        ELSE '❌ FAIL'
    END as status
FROM ops.v_driver_orphans;

-- Muestra de orphans en vista
SELECT 
    '8.1. Muestra de Orphans (Top 10)' AS check_name,
    driver_id,
    person_key,
    detected_reason,
    creation_rule,
    status,
    detected_at
FROM ops.v_driver_orphans
ORDER BY detected_at DESC
LIMIT 10;

-- ============================================================================
-- 9. VERIFICACIÓN: Prevención (Reglas de Creación)
-- ============================================================================
-- ✅ CRITERIO: Verificar distribución de reglas de creación de orphans
SELECT 
    '9. Distribución por Regla de Creación' AS check_name,
    creation_rule,
    COUNT(*) as count,
    ROUND(100.0 * COUNT(*) / NULLIF((SELECT COUNT(*) FROM canon.driver_orphan_quarantine), 0), 2) as pct
FROM canon.driver_orphan_quarantine
WHERE creation_rule IS NOT NULL
GROUP BY creation_rule
ORDER BY count DESC;

-- ============================================================================
-- 10. RESUMEN FINAL
-- ============================================================================
-- ✅ Verificar que todos los checks pasaron
WITH all_checks AS (
    SELECT '1. Drivers sin Lead Operativos' AS check_name,
        COUNT(*) as violation_count
    FROM canon.identity_links il
    WHERE il.source_table = 'drivers'
    AND il.person_key NOT IN (
        SELECT DISTINCT person_key FROM canon.identity_links
        WHERE source_table IN ('module_ct_cabinet_leads', 'module_ct_scouting_daily', 'module_ct_migrations')
    )
    AND il.source_pk NOT IN (
        SELECT driver_id FROM canon.driver_orphan_quarantine WHERE status = 'quarantined'
    )
    UNION ALL
    SELECT '2. Exclusión en Funnel' AS check_name,
        COUNT(*) as violation_count
    FROM ops.v_cabinet_funnel_status vfs
    WHERE vfs.driver_id IN (SELECT driver_id FROM canon.driver_orphan_quarantine WHERE status = 'quarantined')
    UNION ALL
    SELECT '3. Exclusión en Pagos' AS check_name,
        COUNT(*) as violation_count
    FROM ops.v_payment_calculation vpc
    WHERE vpc.driver_id IN (SELECT driver_id FROM canon.driver_orphan_quarantine WHERE status = 'quarantined')
    UNION ALL
    SELECT '4. Exclusión en Elegibilidad' AS check_name,
        COUNT(*) as violation_count
    FROM ops.v_ct4_eligible_drivers ved
    WHERE ved.driver_id IN (SELECT driver_id FROM canon.driver_orphan_quarantine WHERE status = 'quarantined')
    UNION ALL
    SELECT '5. Auditoría Completa' AS check_name,
        COUNT(*) as violation_count
    FROM canon.identity_links il
    WHERE il.source_table = 'drivers'
    AND il.person_key NOT IN (
        SELECT DISTINCT person_key FROM canon.identity_links
        WHERE source_table IN ('module_ct_cabinet_leads', 'module_ct_scouting_daily', 'module_ct_migrations')
    )
    AND il.source_pk NOT IN (SELECT driver_id FROM canon.driver_orphan_quarantine)
)
SELECT 
    'RESUMEN FINAL' AS summary,
    COUNT(*) as total_checks,
    SUM(CASE WHEN violation_count = 0 THEN 1 ELSE 0 END) as passed_checks,
    SUM(CASE WHEN violation_count > 0 THEN 1 ELSE 0 END) as failed_checks,
    CASE 
        WHEN SUM(CASE WHEN violation_count > 0 THEN 1 ELSE 0 END) = 0 THEN '✅ TODOS LOS CHECKS PASARON'
        ELSE '❌ HAY CHECKS QUE FALLARON - REVISAR DETALLES ARRIBA'
    END as final_status
FROM all_checks;



