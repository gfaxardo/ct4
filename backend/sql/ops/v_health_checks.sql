-- ============================================================================
-- Vista: ops.v_health_checks
-- ============================================================================
-- Vista que agrega checks de salud del sistema.
-- Cada check evalúa una condición y retorna status (OK/WARN/ERROR).
-- ============================================================================

CREATE OR REPLACE VIEW ops.v_health_checks AS
WITH checks AS (
    -- Check 1: RAW Data Stale (business_days_lag > 2)
    SELECT
        'raw_data_stale' AS check_key,
        'warning' AS severity,
        CASE
            WHEN MAX(business_days_lag) > 2 THEN 'WARN'
            ELSE 'OK'
        END AS status,
        CASE
            WHEN MAX(business_days_lag) > 2 THEN 
                format('Fuentes RAW con retraso > 2 días: %s', 
                    string_agg(DISTINCT source_name, ', ' ORDER BY source_name))
            ELSE 'Todas las fuentes RAW están al día'
        END AS message,
        NOW() AS last_evaluated_at
    FROM ops.v_data_health_status
    WHERE business_days_lag > 2
    
    UNION ALL
    
    -- Check 2: RAW Data Critical Stale (business_days_lag > 5)
    SELECT
        'raw_data_critical_stale' AS check_key,
        'error' AS severity,
        CASE
            WHEN MAX(business_days_lag) > 5 THEN 'ERROR'
            ELSE 'OK'
        END AS status,
        CASE
            WHEN MAX(business_days_lag) > 5 THEN 
                format('Fuentes RAW con retraso crítico > 5 días: %s', 
                    string_agg(DISTINCT source_name, ', ' ORDER BY source_name))
            ELSE 'No hay fuentes RAW con retraso crítico'
        END AS message,
        NOW() AS last_evaluated_at
    FROM ops.v_data_health_status
    WHERE business_days_lag > 5
    
    UNION ALL
    
    -- Check 3: MV Refresh Stale (minutes_since_refresh > 1440 = 24 horas)
    SELECT
        'mv_refresh_stale' AS check_key,
        'warning' AS severity,
        CASE
            WHEN COUNT(*) > 0 THEN 'WARN'
            ELSE 'OK'
        END AS status,
        CASE
            WHEN COUNT(*) > 0 THEN 
                format('MVs sin refrescar > 24h: %s', 
                    string_agg(DISTINCT mv_name, ', ' ORDER BY mv_name))
            ELSE 'Todas las MVs se refrescaron en las últimas 24 horas'
        END AS message,
        NOW() AS last_evaluated_at
    FROM (
        SELECT
            m.schemaname AS schema_name,
            m.matviewname AS mv_name,
            l.refreshed_at,
            CASE
                WHEN l.refreshed_at IS NULL THEN NULL
                ELSE floor(extract(epoch from (now() - l.refreshed_at))/60)::int
            END AS minutes_since_refresh
        FROM pg_matviews m
        LEFT JOIN LATERAL (
            SELECT refreshed_at
            FROM ops.mv_refresh_log
            WHERE schema_name = m.schemaname AND mv_name = m.matviewname
            ORDER BY refreshed_at DESC
            LIMIT 1
        ) l ON true
        WHERE m.schemaname IN ('ops','canon')
    ) mv_health
    WHERE minutes_since_refresh IS NULL OR minutes_since_refresh > 1440
    
    UNION ALL
    
    -- Check 4: MV Refresh Failed
    SELECT
        'mv_refresh_failed' AS check_key,
        'error' AS severity,
        CASE
            WHEN COUNT(*) > 0 THEN 'ERROR'
            ELSE 'OK'
        END AS status,
        CASE
            WHEN COUNT(*) > 0 THEN 
                format('MVs con último refresh fallido: %s', 
                    string_agg(DISTINCT mv_name, ', ' ORDER BY mv_name))
            ELSE 'Todas las MVs se refrescaron exitosamente'
        END AS message,
        NOW() AS last_evaluated_at
    FROM (
        SELECT DISTINCT
            l.schema_name,
            l.mv_name,
            l.status,
            l.refreshed_at,
            ROW_NUMBER() OVER (PARTITION BY l.schema_name, l.mv_name ORDER BY l.refreshed_at DESC) AS rn
        FROM ops.mv_refresh_log l
        WHERE l.schema_name IN ('ops','canon')
    ) latest_refresh
    WHERE rn = 1 AND status = 'FAILED'
    
    UNION ALL
    
    -- Check 5: MV Not Populated
    SELECT
        'mv_not_populated' AS check_key,
        'error' AS severity,
        CASE
            WHEN COUNT(*) > 0 THEN 'ERROR'
            ELSE 'OK'
        END AS status,
        CASE
            WHEN COUNT(*) > 0 THEN 
                format('MVs no pobladas: %s', 
                    string_agg(DISTINCT matviewname, ', ' ORDER BY matviewname))
            ELSE 'Todas las MVs están pobladas'
        END AS message,
        NOW() AS last_evaluated_at
    FROM pg_matviews
    WHERE schemaname IN ('ops','canon') AND NOT ispopulated
    
    UNION ALL
    
    -- Check 6: RAW Data Health Status Errors
    SELECT
        'raw_data_health_errors' AS check_key,
        'error' AS severity,
        CASE
            WHEN COUNT(*) > 0 THEN 'ERROR'
            ELSE 'OK'
        END AS status,
        CASE
            WHEN COUNT(*) > 0 THEN 
                format('Fuentes RAW con estado de error: %s', 
                    string_agg(DISTINCT source_name, ', ' ORDER BY source_name))
            ELSE 'No hay fuentes RAW con estado de error'
        END AS message,
        NOW() AS last_evaluated_at
    FROM ops.v_data_health_status
    WHERE health_status LIKE 'RED_%'
    
    UNION ALL
    
    -- Check 7: RAW Data Health Status Warnings
    SELECT
        'raw_data_health_warnings' AS check_key,
        'warning' AS severity,
        CASE
            WHEN COUNT(*) > 0 THEN 'WARN'
            ELSE 'OK'
        END AS status,
        CASE
            WHEN COUNT(*) > 0 THEN 
                format('Fuentes RAW con advertencias: %s', 
                    string_agg(DISTINCT source_name, ', ' ORDER BY source_name))
            ELSE 'No hay fuentes RAW con advertencias'
        END AS message,
        NOW() AS last_evaluated_at
    FROM ops.v_data_health_status
    WHERE health_status LIKE 'YELLOW_%'
    
    UNION ALL
    
    -- Check 8: Critical MV Missing Refresh Log (usando registry)
    SELECT
        'critical_mv_no_refresh_log' AS check_key,
        'info' AS severity,
        CASE
            WHEN COUNT(*) > 0 THEN 'WARN'
            ELSE 'OK'
        END AS status,
        CASE
            WHEN COUNT(*) > 0 THEN 
                format('MVs críticas sin historial de refresh: %s', 
                    string_agg(DISTINCT r.object_name, ', ' ORDER BY r.object_name))
            ELSE 'Todas las MVs críticas tienen historial de refresh'
        END AS message,
        NOW() AS last_evaluated_at
    FROM ops.source_registry r
    WHERE r.object_type = 'matview'
        AND (r.is_critical = true OR r.criticality = 'critical')
        AND NOT EXISTS (
            SELECT 1
            FROM ops.mv_refresh_log l
            WHERE l.schema_name = r.schema_name 
                AND l.mv_name = r.object_name
        )
    
    UNION ALL
    
    -- Check 9: Expected Source Missing (registry dice expected pero no existe en DB)
    SELECT
        'expected_source_missing' AS check_key,
        'error' AS severity,
        CASE
            WHEN COUNT(*) > 0 THEN 'ERROR'
            ELSE 'OK'
        END AS status,
        CASE
            WHEN COUNT(*) > 0 THEN 
                format('Fuentes esperadas que no existen en DB: %s', 
                    string_agg(DISTINCT format('%s.%s', r.schema_name, r.object_name), ', ' ORDER BY r.schema_name, r.object_name))
            ELSE 'Todas las fuentes esperadas existen en DB'
        END AS message,
        NOW() AS last_evaluated_at
    FROM ops.source_registry r
    WHERE r.is_expected = true
        AND NOT EXISTS (
            SELECT 1
            FROM pg_class c
            JOIN pg_namespace n ON n.oid = c.relnamespace
            WHERE n.nspname = r.schema_name
                AND c.relname = r.object_name
                AND c.relkind IN ('r', 'v', 'm')
        )
    
    UNION ALL
    
    -- Check 10: Unregistered Used Object (usado en repo pero no en registry)
    -- Nota: Este check requiere que discovery_usage_backend.csv esté actualizado
    -- Por ahora, verificamos objetos en DB que no están en registry pero deberían estar
    -- (esto es una aproximación; el check completo requeriría leer el CSV)
    SELECT
        'unregistered_used_object' AS check_key,
        'warning' AS severity,
        CASE
            WHEN COUNT(*) > 0 THEN 'WARN'
            ELSE 'OK'
        END AS status,
        CASE
            WHEN COUNT(*) > 0 THEN 
                format('Objetos en DB que no están en registry (posiblemente usados): %s', 
                    string_agg(DISTINCT format('%s.%s', c.schema_name, c.object_name), ', ' ORDER BY c.schema_name, c.object_name) 
                    LIMIT 10)
            ELSE 'Todos los objetos relevantes están en registry'
        END AS message,
        NOW() AS last_evaluated_at
    FROM (
        SELECT n.nspname AS schema_name, c.relname AS object_name
        FROM pg_class c
        JOIN pg_namespace n ON n.oid = c.relnamespace
        WHERE n.nspname IN ('public', 'ops', 'canon', 'raw', 'observational')
            AND c.relkind IN ('r', 'v', 'm')
            AND NOT c.relname LIKE 'pg_%'
            AND NOT EXISTS (
                SELECT 1 FROM ops.source_registry r
                WHERE r.schema_name = n.nspname AND r.object_name = c.relname
            )
    ) c
    WHERE c.schema_name IN ('ops', 'canon')  -- Solo objetos en schemas críticos
        OR (c.schema_name = 'public' AND c.object_name LIKE 'module_ct_%')  -- Tablas module_ct
    
    UNION ALL
    
    -- Check 11: Monitored Not In Health Views (health_enabled=true pero no cubierto)
    SELECT
        'monitored_not_in_health_views' AS check_key,
        'warning' AS severity,
        CASE
            WHEN COUNT(*) > 0 THEN 'WARN'
            ELSE 'OK'
        END AS status,
        CASE
            WHEN COUNT(*) > 0 THEN 
                format('Objetos con health_enabled=true pero no cubiertos por health views: %s', 
                    string_agg(DISTINCT format('%s.%s', r.schema_name, r.object_name), ', ' ORDER BY r.schema_name, r.object_name))
            ELSE 'Todos los objetos monitoreados están cubiertos por health views'
        END AS message,
        NOW() AS last_evaluated_at
    FROM ops.source_registry r
    WHERE r.health_enabled = true
        AND r.layer = 'RAW'
        AND NOT EXISTS (
            SELECT 1 FROM ops.v_data_health_status v
            WHERE v.source_name = r.object_name
        )
    
    UNION ALL
    
    -- Check 12: Health View Source Unknown (aparece en v_data_health_status pero no en registry)
    SELECT
        'health_view_source_unknown' AS check_key,
        'warning' AS severity,
        CASE
            WHEN COUNT(*) > 0 THEN 'WARN'
            ELSE 'OK'
        END AS status,
        CASE
            WHEN COUNT(*) > 0 THEN 
                format('Fuentes en v_data_health_status que no están en registry: %s', 
                    string_agg(DISTINCT v.source_name, ', ' ORDER BY v.source_name))
            ELSE 'Todas las fuentes en health views están en registry'
        END AS message,
        NOW() AS last_evaluated_at
    FROM ops.v_data_health_status v
    WHERE NOT EXISTS (
        SELECT 1 FROM ops.source_registry r
        WHERE r.object_name = v.source_name
            AND r.layer = 'RAW'
    )
    
    UNION ALL
    
    -- Check 13: RAW Source Stale Affecting Critical (RAW stale que alimenta MV crítica)
    SELECT
        'raw_source_stale_affecting_critical' AS check_key,
        'error' AS severity,
        CASE
            WHEN COUNT(*) > 0 THEN 'ERROR'
            ELSE 'OK'
        END AS status,
        CASE
            WHEN COUNT(*) > 0 THEN 
                format('Fuentes RAW stale que afectan MVs críticas: %s', 
                    string_agg(DISTINCT format('%s.%s -> %s.%s', 
                        r_raw.schema_name, r_raw.object_name,
                        r_mv.schema_name, r_mv.object_name), 
                        ', ' ORDER BY r_raw.schema_name, r_raw.object_name))
            ELSE 'No hay fuentes RAW stale afectando MVs críticas'
        END AS message,
        NOW() AS last_evaluated_at
    FROM ops.source_registry r_raw
    JOIN ops.v_data_health_status v ON v.source_name = r_raw.object_name
    JOIN ops.source_registry r_mv ON (
        r_mv.depends_on @> jsonb_build_array(jsonb_build_object('schema', r_raw.schema_name, 'name', r_raw.object_name))
        AND (r_mv.is_critical = true OR r_mv.criticality = 'critical')
        AND r_mv.object_type = 'matview'
    )
    WHERE r_raw.layer = 'RAW'
        AND v.business_days_lag > 2
)
SELECT 
    check_key,
    severity,
    status,
    message,
    CASE check_key
        WHEN 'raw_data_stale' THEN '/ops/health?tab=raw'
        WHEN 'raw_data_critical_stale' THEN '/ops/health?tab=raw'
        WHEN 'raw_data_health_errors' THEN '/ops/health?tab=raw'
        WHEN 'raw_data_health_warnings' THEN '/ops/health?tab=raw'
        WHEN 'mv_refresh_stale' THEN '/ops/health?tab=mv&stale_only=true'
        WHEN 'mv_refresh_failed' THEN '/ops/health?tab=mv'
        WHEN 'mv_not_populated' THEN '/ops/health?tab=mv'
        WHEN 'critical_mv_no_refresh_log' THEN '/ops/health?tab=mv'
        WHEN 'expected_source_missing' THEN '/ops/health?tab=checks'
        WHEN 'unregistered_used_object' THEN '/ops/health?tab=checks'
        WHEN 'monitored_not_in_health_views' THEN '/ops/health?tab=raw'
        WHEN 'health_view_source_unknown' THEN '/ops/health?tab=raw'
        WHEN 'raw_source_stale_affecting_critical' THEN '/ops/health?tab=raw'
        ELSE NULL
    END AS drilldown_url,
    last_evaluated_at
FROM checks
ORDER BY 
    CASE severity 
        WHEN 'error' THEN 1 
        WHEN 'warning' THEN 2 
        WHEN 'info' THEN 3 
    END,
    check_key;

COMMENT ON VIEW ops.v_health_checks IS 
'Vista de checks de salud del sistema. Evalúa condiciones de RAW data, MVs e identidad.';

COMMENT ON COLUMN ops.v_health_checks.check_key IS 
'Identificador único del check (ej: raw_data_stale, mv_refresh_failed).';

COMMENT ON COLUMN ops.v_health_checks.severity IS 
'Severidad del check: error, warning, info.';

COMMENT ON COLUMN ops.v_health_checks.status IS 
'Estado del check: OK, WARN, ERROR.';

COMMENT ON COLUMN ops.v_health_checks.message IS 
'Mensaje descriptivo del estado del check.';

COMMENT ON COLUMN ops.v_health_checks.drilldown_url IS 
'URL para ver detalles del check (ej: /ops/health?tab=raw).';

COMMENT ON COLUMN ops.v_health_checks.last_evaluated_at IS 
'Timestamp de la última evaluación del check.';

