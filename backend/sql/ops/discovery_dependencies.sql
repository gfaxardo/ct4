-- ============================================================================
-- DB Discovery: Dependencias entre Objetos
-- ============================================================================
-- Este script detecta dependencias directas (parents) para views y matviews
-- usando pg_depend y pg_rewrite.
-- 
-- Output:
-- - parent_schema: schema del objeto padre (del cual depende)
-- - parent_name: nombre del objeto padre
-- - child_schema: schema del objeto hijo (que depende)
-- - child_name: nombre del objeto hijo
-- - dependency_type: tipo de dependencia ('sql_view_dep', 'matview_dep', etc.)
-- ============================================================================

WITH view_dependencies AS (
    -- Dependencias de views regulares
    SELECT DISTINCT
        n_parent.nspname AS parent_schema,
        c_parent.relname AS parent_name,
        n_child.nspname AS child_schema,
        c_child.relname AS child_name,
        'sql_view_dep' AS dependency_type
    FROM pg_depend d
    JOIN pg_rewrite r ON d.objid = r.oid
    JOIN pg_class c_child ON r.ev_class = c_child.oid
    JOIN pg_namespace n_child ON c_child.relnamespace = n_child.oid
    JOIN pg_class c_parent ON d.refobjid = c_parent.oid
    JOIN pg_namespace n_parent ON c_parent.relnamespace = n_parent.oid
    WHERE c_child.relkind = 'v'  -- views regulares
        AND c_parent.relkind IN ('r', 'v', 'm')  -- tablas, vistas, matviews
        AND n_child.nspname IN ('public', 'ops', 'canon', 'raw', 'observational')
        AND n_parent.nspname IN ('public', 'ops', 'canon', 'raw', 'observational')
        AND d.deptype = 'n'  -- dependencia normal
        AND NOT c_child.relname LIKE 'pg_%'
        AND NOT c_parent.relname LIKE 'pg_%'
    
    UNION ALL
    
    -- Dependencias de materialized views
    SELECT DISTINCT
        n_parent.nspname AS parent_schema,
        c_parent.relname AS parent_name,
        n_child.nspname AS child_schema,
        c_child.relname AS child_name,
        'matview_dep' AS dependency_type
    FROM pg_depend d
    JOIN pg_class c_child ON d.objid = c_child.oid
    JOIN pg_namespace n_child ON c_child.relnamespace = n_child.oid
    JOIN pg_class c_parent ON d.refobjid = c_parent.oid
    JOIN pg_namespace n_parent ON c_parent.relnamespace = n_parent.oid
    WHERE c_child.relkind = 'm'  -- materialized views
        AND c_parent.relkind IN ('r', 'v', 'm')  -- tablas, vistas, matviews
        AND n_child.nspname IN ('public', 'ops', 'canon', 'raw', 'observational')
        AND n_parent.nspname IN ('public', 'ops', 'canon', 'raw', 'observational')
        AND d.deptype = 'n'  -- dependencia normal
        AND NOT c_child.relname LIKE 'pg_%'
        AND NOT c_parent.relname LIKE 'pg_%'
)
SELECT 
    parent_schema,
    parent_name,
    child_schema,
    child_name,
    dependency_type
FROM view_dependencies
ORDER BY child_schema, child_name, parent_schema, parent_name;

-- ============================================================================
-- COMANDOS PARA EJECUTAR Y EXPORTAR A CSV
-- ============================================================================
-- 
-- Opción 1: Usando script Python (recomendado)
-- python backend/scripts/discovery_dependencies.py
--
-- Opción 2: Usando psql con \copy
-- psql -h 168.119.226.236 -p 5432 -U yego_user -d yego_integral -c "\copy (SELECT ...) TO 'discovery_dependencies.csv' WITH CSV HEADER;"
--
-- ============================================================================







