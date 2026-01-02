-- ============================================================================
-- DB Discovery: Registry de Fuentes
-- ============================================================================
-- Este script lista todos los objetos (tablas, vistas, materialized views)
-- en los schemas: public, ops, canon, raw (si existe), observational (si existe)
-- 
-- Campos incluidos:
-- - schema_name: nombre del schema
-- - object_name: nombre del objeto
-- - object_type: tipo (table/view/matview)
-- - estimated_rows: estimación de filas (pg_class.reltuples)
-- - size_mb: tamaño total en MB (pg_total_relation_size)
-- - last_analyze: última vez que se analizó (si disponible)
-- ============================================================================

SELECT 
    n.nspname AS schema_name,
    c.relname AS object_name,
    CASE 
        WHEN c.relkind = 'r' THEN 'table'
        WHEN c.relkind = 'v' THEN 'view'
        WHEN c.relkind = 'm' THEN 'matview'
        ELSE 'other'
    END AS object_type,
    COALESCE(c.reltuples::bigint, 0) AS estimated_rows,
    ROUND(pg_total_relation_size(c.oid) / 1024.0 / 1024.0, 2) AS size_mb,
    COALESCE(s.last_analyze::text, '') AS last_analyze
FROM pg_class c
JOIN pg_namespace n ON n.oid = c.relnamespace
LEFT JOIN pg_stat_user_tables s ON s.schemaname = n.nspname AND s.relname = c.relname
WHERE n.nspname IN ('public', 'ops', 'canon', 'raw', 'observational')
    AND EXISTS (
        SELECT 1 FROM pg_namespace ns 
        WHERE ns.nspname = n.nspname
    )  -- Solo schemas que existen
    AND c.relkind IN ('r', 'v', 'm')  -- r=table, v=view, m=matview
    AND NOT c.relname LIKE 'pg_%'  -- Excluir tablas del sistema
ORDER BY 
    n.nspname,
    CASE 
        WHEN c.relkind = 'r' THEN 1
        WHEN c.relkind = 'm' THEN 2
        WHEN c.relkind = 'v' THEN 3
        ELSE 4
    END,
    c.relname;

-- ============================================================================
-- COMANDOS PARA EJECUTAR Y EXPORTAR A CSV
-- ============================================================================
-- 
-- Opción 1: Usando psql con COPY (requiere permisos de superusuario o propietario)
-- psql -h 168.119.226.236 -p 5432 -U yego_user -d yego_integral -f discovery_objects.sql -o discovery_objects.csv -A -F ","
--
-- Opción 2: Usando psql con \copy (no requiere permisos especiales)
-- psql -h 168.119.226.236 -p 5432 -U yego_user -d yego_integral -c "\copy (SELECT n.nspname AS schema_name, c.relname AS object_name, CASE WHEN c.relkind = 'r' THEN 'table' WHEN c.relkind = 'v' THEN 'view' WHEN c.relkind = 'm' THEN 'matview' ELSE 'other' END AS object_type, COALESCE(c.reltuples::bigint, 0) AS estimated_rows, ROUND(pg_total_relation_size(c.oid) / 1024.0 / 1024.0, 2) AS size_mb, COALESCE(s.last_analyze::text, '') AS last_analyze FROM pg_class c JOIN pg_namespace n ON n.oid = c.relnamespace LEFT JOIN pg_stat_user_tables s ON s.schemaname = n.nspname AND s.relname = c.relname WHERE n.nspname IN ('public', 'ops', 'canon', 'raw') AND c.relkind IN ('r', 'v', 'm') AND NOT c.relname LIKE 'pg_%' ORDER BY n.nspname, CASE WHEN c.relkind = 'r' THEN 1 WHEN c.relkind = 'm' THEN 2 WHEN c.relkind = 'v' THEN 3 ELSE 4 END, c.relname) TO 'discovery_objects.csv' WITH CSV HEADER;"
--
-- Opción 3: Usando script Python (recomendado)
-- python backend/scripts/discovery_objects.py
--
-- ============================================================================

