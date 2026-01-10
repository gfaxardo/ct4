-- ============================================================================
-- INVENTARIO: Fuentes de Scout Attribution
-- ============================================================================
-- Propósito: Listar todas las tablas/vistas que contienen información de scout_id
-- Ejecución: Script de diagnóstico (no crea objetos)
-- ============================================================================

-- 1. Verificar existencia de tablas/vistas candidatas
SELECT 
    'TABLAS/VISTAS CANDIDATAS' AS inventory_type,
    schemaname,
    tablename,
    CASE 
        WHEN schemaname || '.' || tablename = 'observational.lead_ledger' THEN 'source-of-truth'
        WHEN schemaname || '.' || tablename = 'observational.lead_events' THEN 'eventos'
        WHEN schemaname || '.' || tablename = 'public.module_ct_scouting_daily' THEN 'scouting_daily'
        WHEN schemaname || '.' || tablename = 'public.module_ct_cabinet_leads' THEN 'cabinet_leads'
        WHEN schemaname || '.' || tablename = 'public.module_ct_migrations' THEN 'migrations'
        WHEN schemaname || '.' || tablename = 'public.module_ct_scouts_list' THEN 'scouts_list'
        ELSE 'other'
    END AS source_role
FROM pg_tables
WHERE (
    tablename LIKE '%scout%' 
    OR tablename LIKE '%lead%'
    OR tablename LIKE '%cabinet%'
    OR tablename LIKE '%migration%'
)
AND schemaname IN ('public', 'observational', 'ops', 'canon')
UNION ALL
SELECT 
    'VISTAS',
    schemaname,
    viewname AS tablename,
    CASE 
        WHEN schemaname || '.' || viewname = 'ops.v_yango_collection_with_scout' THEN 'cobranza_yango'
        WHEN schemaname || '.' || viewname = 'ops.v_yango_cabinet_claims_for_collection' THEN 'cobranza_yango_base'
        WHEN schemaname || '.' || viewname LIKE '%scout%attribution%' THEN 'attribution_views'
        ELSE 'other'
    END AS source_role
FROM pg_views
WHERE (
    viewname LIKE '%scout%' 
    OR viewname LIKE '%lead%'
    OR viewname LIKE '%cabinet%'
    OR viewname LIKE '%yango%'
)
AND schemaname IN ('public', 'observational', 'ops', 'canon')
ORDER BY inventory_type, schemaname, tablename;

-- 2. Verificar columnas de scout_id en tablas candidatas
SELECT 
    table_schema,
    table_name,
    column_name,
    data_type
FROM information_schema.columns
WHERE (
    column_name LIKE '%scout%'
    OR column_name = 'attributed_scout_id'
)
AND table_schema IN ('public', 'observational', 'ops', 'canon')
ORDER BY table_schema, table_name, column_name;

-- 3. Verificar cobranza Yango (objeto canónico)
SELECT 
    'COBRANZA_YANGO_CANDIDATES' AS check_type,
    schemaname,
    viewname AS object_name,
    'VIEW' AS object_type
FROM pg_views
WHERE schemaname = 'ops'
AND (
    viewname LIKE '%yango%' 
    AND (viewname LIKE '%claims%' OR viewname LIKE '%collection%' OR viewname LIKE '%cobranza%')
)
UNION ALL
SELECT 
    'COBRANZA_YANGO_CANDIDATES',
    schemaname,
    matviewname AS object_name,
    'MATERIALIZED_VIEW' AS object_type
FROM pg_matviews
WHERE schemaname = 'ops'
AND (
    matviewname LIKE '%yango%' 
    AND (matviewname LIKE '%claims%' OR matviewname LIKE '%collection%' OR matviewname LIKE '%cobranza%')
)
ORDER BY object_type, object_name;

-- 4. Resumen de identidad canónica
SELECT 
    'IDENTITY_REGISTRY' AS check_type,
    COUNT(*) AS total_persons
FROM canon.identity_registry
UNION ALL
SELECT 
    'IDENTITY_LINKS',
    COUNT(*)
FROM canon.identity_links
WHERE source_table = 'module_ct_scouting_daily'
UNION ALL
SELECT 
    'LEAD_LEDGER_WITH_SCOUT',
    COUNT(*)
FROM observational.lead_ledger
WHERE attributed_scout_id IS NOT NULL;
