-- ============================================================================
-- Sistema de Observabilidad Canónica de Ingestas ("Data Health") - COMPLETO
-- ============================================================================
-- IMPORTANTE ANTES DE EJECUTAR:
-- 1. Ejecutar primero: backend/sql/ops/check_data_health_tables.sql
-- 2. Si alguna tabla opcional no existe, comentar su CTE correspondiente:
--    - raw.module_ct_cabinet_payments -> comentar source_raw_module_ct_cabinet_payments
--    - public.module_ct_cabinet_migrations -> comentar source_module_ct_cabinet_migrations
--    - public.module_ct_scout_drivers -> comentar source_module_ct_scout_drivers
--    - public.module_ct_cabinet_payments -> comentar source_module_ct_cabinet_payments
--    - public.module_ct_scouts_list -> comentar source_module_ct_scouts_list
-- 3. También comentar su línea en UNION ALL al final de cada vista
-- ============================================================================
-- PROPÓSITO:
-- Proporciona visibilidad sobre el estado de frescura y salud de las ingestas
-- de datos del sistema YEGO. Permite monitorear:
-- - Hasta cuándo está actualizada cada fuente
-- - Si la ingesta está caída
-- - Cuánto se ingesta por día
--
-- DISEÑO:
-- Este sistema funciona con fuentes heterogéneas (date_file varchar DD-MM-YYYY,
-- created_at timestamps, snapshot_at, etc.) y no depende de datestyle de PostgreSQL.
-- Es robusto ante datos sucios mediante validación de regex antes de parsear fechas.
--
-- DIFERENCIA NEGOCIO VS INGESTA:
-- - business_date: fecha del evento/transacción en el mundo real (ej: fecha de pago)
-- - ingestion_ts: timestamp de cuándo se ingirió/registró el dato en el sistema
-- 
-- PARSEO DE date_file:
-- - Solo parseamos si coincide con regex '^\d{2}-\d{2}-\d{4}$' (DD-MM-YYYY)
-- - O si coincide con regex '^\d{4}-\d{2}-\d{2}$' (YYYY-MM-DD)
-- - Evitamos usar to_date() sin validación previa para prevenir errores por datos sucios
--
-- POR QUÉ EVITAMOS datestyle:
-- - PostgreSQL datestyle puede variar entre sesiones/servidores
-- - Usar formato explícito en to_date() hace el código portable y predecible
-- ============================================================================

-- ============================================================================
-- Vista: ops.v_data_sources_catalog
-- ============================================================================
-- Catálogo de todas las fuentes monitoreadas con sus metadatos.
-- Incluye: source_name, schema_name, object_name, source_type, y expresiones SQL
-- para business_date e ingestion_ts.
-- ============================================================================

CREATE OR REPLACE VIEW ops.v_data_sources_catalog AS
SELECT * FROM (VALUES
    -- ACTIVITY: Fuentes de actividad operativa
    ('summary_daily', 'public', 'summary_daily', 'activity',
     'CASE WHEN date_file ~ ''^\d{2}-\d{2}-\d{4}$'' THEN to_date(date_file, ''DD-MM-YYYY'') WHEN date_file ~ ''^\d{4}-\d{2}-\d{2}$'' THEN to_date(date_file, ''YYYY-MM-DD'') ELSE NULL END',
     'created_at::timestamptz'),
    
    -- LEDGER: Ledgers históricos
    ('yango_payment_ledger', 'ops', 'yango_payment_ledger', 'ledger',
     'pay_date',
     'snapshot_at'),
    
    -- UPSTREAM: Fuentes RAW críticas (upstream de procesamiento)
    -- COMENTADO: raw.module_ct_cabinet_payments no existe en esta base de datos
    -- ('raw_module_ct_cabinet_payments', 'raw', 'module_ct_cabinet_payments', 'upstream',
    --  'COALESCE(pay_date, payment_date, date, CASE WHEN date_file ~ ''^\d{2}-\d{2}-\d{4}$'' THEN to_date(date_file, ''DD-MM-YYYY'') WHEN date_file ~ ''^\d{4}-\d{2}-\d{2}$'' THEN to_date(date_file, ''YYYY-MM-DD'') ELSE NULL END)',
    --  'COALESCE(snapshot_at, loaded_at, ingested_at, created_at, updated_at)::timestamptz'),
    
    -- CT_INGEST: Fuentes de Control Tower (ingestas)
    ('module_ct_cabinet_leads', 'public', 'module_ct_cabinet_leads', 'ct_ingest',
     'lead_created_at::date',
     'lead_created_at::timestamptz'),
    
    ('module_ct_scouting_daily', 'public', 'module_ct_scouting_daily', 'ct_ingest',
     'registration_date',
     'created_at::timestamptz'),
    
    -- COMENTADO: module_ct_cabinet_migrations no existe en esta base de datos
    -- ('module_ct_cabinet_migrations', 'public', 'module_ct_cabinet_migrations', 'ct_ingest',
    --  'COALESCE(migration_date, created_at::date)',
    --  'COALESCE(created_at, updated_at)::timestamptz'),
    
    ('module_ct_scout_drivers', 'public', 'module_ct_scout_drivers', 'ct_ingest',
     'created_at::date',
     'COALESCE(created_at, updated_at)::timestamptz'),
    
    ('module_ct_cabinet_payments', 'public', 'module_ct_cabinet_payments', 'ct_ingest',
     'COALESCE(pay_date, payment_date, date, created_at::date)',
     'COALESCE(snapshot_at, created_at, updated_at)::timestamptz'),
    
    -- MASTER: Tablas maestras (siempre GREEN salvo si no hay datos)
    ('drivers', 'public', 'drivers', 'master',
     'COALESCE(hire_date, created_at::date, updated_at::date)',
     'COALESCE(updated_at, created_at)::timestamptz'),
    
    ('module_ct_scouts_list', 'public', 'module_ct_scouts_list', 'master',
     'COALESCE(created_at::date, updated_at::date)',
     'COALESCE(updated_at, created_at)::timestamptz')
) AS t(source_name, schema_name, object_name, source_type, business_date_expr, ingestion_ts_expr);

COMMENT ON VIEW ops.v_data_sources_catalog IS 
'Catálogo de todas las fuentes monitoreadas en el sistema de Data Health. Incluye metadatos y expresiones SQL para calcular business_date e ingestion_ts.';

COMMENT ON COLUMN ops.v_data_sources_catalog.source_name IS 
'Nombre canónico de la fuente (usado en otras vistas).';

COMMENT ON COLUMN ops.v_data_sources_catalog.schema_name IS 
'Schema donde reside la tabla/vista (public, ops, raw, etc.).';

COMMENT ON COLUMN ops.v_data_sources_catalog.object_name IS 
'Nombre de la tabla o vista.';

COMMENT ON COLUMN ops.v_data_sources_catalog.source_type IS 
'Tipo de fuente: activity (operativa), ledger (histórico), upstream (RAW crítico), ct_ingest (Control Tower), master (maestra).';

COMMENT ON COLUMN ops.v_data_sources_catalog.business_date_expr IS 
'Expresión SQL para calcular business_date (texto, se evalúa dinámicamente).';

COMMENT ON COLUMN ops.v_data_sources_catalog.ingestion_ts_expr IS 
'Expresión SQL para calcular ingestion_ts (texto, se evalúa dinámicamente).';

-- ============================================================================
-- Vista: ops.v_data_freshness_status
-- ============================================================================
-- 1 fila por fuente con métricas de frescura
-- ============================================================================

CREATE OR REPLACE VIEW ops.v_data_freshness_status AS
WITH source_summary_daily AS (
    SELECT 
        'summary_daily' AS source_name,
        MAX(CASE 
            WHEN date_file ~ '^\d{2}-\d{2}-\d{4}$' THEN to_date(date_file, 'DD-MM-YYYY')
            WHEN date_file ~ '^\d{4}-\d{2}-\d{2}$' THEN to_date(date_file, 'YYYY-MM-DD')
            ELSE NULL
        END) AS max_business_date,
        CURRENT_DATE - MAX(CASE 
            WHEN date_file ~ '^\d{2}-\d{2}-\d{4}$' THEN to_date(date_file, 'DD-MM-YYYY')
            WHEN date_file ~ '^\d{4}-\d{2}-\d{2}$' THEN to_date(date_file, 'YYYY-MM-DD')
            ELSE NULL
        END) AS business_days_lag,
        MAX(created_at)::timestamptz AS max_ingestion_ts,
        NOW() - MAX(created_at)::timestamptz AS ingestion_lag_interval,
        COUNT(*) FILTER (
            WHERE CASE 
                WHEN date_file ~ '^\d{2}-\d{2}-\d{4}$' THEN to_date(date_file, 'DD-MM-YYYY')
                WHEN date_file ~ '^\d{4}-\d{2}-\d{2}$' THEN to_date(date_file, 'YYYY-MM-DD')
                ELSE NULL
            END = CURRENT_DATE - INTERVAL '1 day'
        ) AS rows_business_yesterday,
        COUNT(*) FILTER (
            WHERE CASE 
                WHEN date_file ~ '^\d{2}-\d{2}-\d{4}$' THEN to_date(date_file, 'DD-MM-YYYY')
                WHEN date_file ~ '^\d{4}-\d{2}-\d{2}$' THEN to_date(date_file, 'YYYY-MM-DD')
                ELSE NULL
            END = CURRENT_DATE
        ) AS rows_business_today,
        COUNT(*) FILTER (WHERE created_at::date = CURRENT_DATE - INTERVAL '1 day') AS rows_ingested_yesterday,
        COUNT(*) FILTER (WHERE created_at::date = CURRENT_DATE) AS rows_ingested_today
    FROM public.summary_daily
    WHERE date_file IS NOT NULL
        AND (date_file ~ '^\d{2}-\d{2}-\d{4}$' OR date_file ~ '^\d{4}-\d{2}-\d{2}$')
),
source_yango_payment_ledger AS (
    SELECT 
        'yango_payment_ledger' AS source_name,
        MAX(pay_date) AS max_business_date,
        CURRENT_DATE - MAX(pay_date) AS business_days_lag,
        MAX(snapshot_at) AS max_ingestion_ts,
        NOW() - MAX(snapshot_at) AS ingestion_lag_interval,
        COUNT(*) FILTER (WHERE pay_date = CURRENT_DATE - INTERVAL '1 day') AS rows_business_yesterday,
        COUNT(*) FILTER (WHERE pay_date = CURRENT_DATE) AS rows_business_today,
        COUNT(*) FILTER (WHERE snapshot_at::date = CURRENT_DATE - INTERVAL '1 day') AS rows_ingested_yesterday,
        COUNT(*) FILTER (WHERE snapshot_at::date = CURRENT_DATE) AS rows_ingested_today
    FROM ops.yango_payment_ledger
    WHERE pay_date IS NOT NULL
),
-- COMENTADO: raw.module_ct_cabinet_payments no existe en esta base de datos
-- Descomenta esta CTE cuando la tabla esté disponible
/*
source_raw_module_ct_cabinet_payments AS (
    -- RAW: upstream crítico
    -- NOTA: Si la tabla raw.module_ct_cabinet_payments no existe, esta CTE retornará 0 filas
    SELECT 
        'raw_module_ct_cabinet_payments' AS source_name,
        MAX(COALESCE(
            pay_date,
            payment_date,
            date,
            CASE 
                WHEN date_file ~ '^\d{2}-\d{2}-\d{4}$' THEN to_date(date_file, 'DD-MM-YYYY')
                WHEN date_file ~ '^\d{4}-\d{2}-\d{2}$' THEN to_date(date_file, 'YYYY-MM-DD')
                ELSE NULL
            END,
            created_at::date
        )) AS max_business_date,
        CURRENT_DATE - MAX(COALESCE(
            pay_date,
            payment_date,
            date,
            CASE 
                WHEN date_file ~ '^\d{2}-\d{2}-\d{4}$' THEN to_date(date_file, 'DD-MM-YYYY')
                WHEN date_file ~ '^\d{4}-\d{2}-\d{2}$' THEN to_date(date_file, 'YYYY-MM-DD')
                ELSE NULL
            END,
            created_at::date
        )) AS business_days_lag,
        MAX(COALESCE(
            snapshot_at,
            loaded_at,
            ingested_at,
            created_at,
            updated_at
        ))::timestamptz AS max_ingestion_ts,
        NOW() - MAX(COALESCE(
            snapshot_at,
            loaded_at,
            ingested_at,
            created_at,
            updated_at
        ))::timestamptz AS ingestion_lag_interval,
        COUNT(*) FILTER (
            WHERE COALESCE(pay_date, payment_date, date, created_at::date) = CURRENT_DATE - INTERVAL '1 day'
        ) AS rows_business_yesterday,
        COUNT(*) FILTER (
            WHERE COALESCE(pay_date, payment_date, date, created_at::date) = CURRENT_DATE
        ) AS rows_business_today,
        COUNT(*) FILTER (
            WHERE COALESCE(snapshot_at, loaded_at, ingested_at, created_at, updated_at)::date = CURRENT_DATE - INTERVAL '1 day'
        ) AS rows_ingested_yesterday,
        COUNT(*) FILTER (
            WHERE COALESCE(snapshot_at, loaded_at, ingested_at, created_at, updated_at)::date = CURRENT_DATE
        ) AS rows_ingested_today
    FROM raw.module_ct_cabinet_payments
    WHERE (pay_date IS NOT NULL OR payment_date IS NOT NULL OR date IS NOT NULL OR created_at IS NOT NULL)
),
*/
source_module_ct_cabinet_leads AS (
    SELECT 
        'module_ct_cabinet_leads' AS source_name,
        MAX(lead_created_at::date) AS max_business_date,
        CURRENT_DATE - MAX(lead_created_at::date) AS business_days_lag,
        MAX(lead_created_at)::timestamptz AS max_ingestion_ts,
        NOW() - MAX(lead_created_at)::timestamptz AS ingestion_lag_interval,
        COUNT(*) FILTER (WHERE lead_created_at::date = CURRENT_DATE - INTERVAL '1 day') AS rows_business_yesterday,
        COUNT(*) FILTER (WHERE lead_created_at::date = CURRENT_DATE) AS rows_business_today,
        COUNT(*) FILTER (WHERE lead_created_at::date = CURRENT_DATE - INTERVAL '1 day') AS rows_ingested_yesterday,
        COUNT(*) FILTER (WHERE lead_created_at::date = CURRENT_DATE) AS rows_ingested_today
    FROM public.module_ct_cabinet_leads
    WHERE lead_created_at IS NOT NULL
),
source_module_ct_scouting_daily AS (
    SELECT 
        'module_ct_scouting_daily' AS source_name,
        MAX(registration_date) AS max_business_date,
        CURRENT_DATE - MAX(registration_date) AS business_days_lag,
        MAX(created_at)::timestamptz AS max_ingestion_ts,
        NOW() - MAX(created_at)::timestamptz AS ingestion_lag_interval,
        COUNT(*) FILTER (WHERE registration_date = CURRENT_DATE - INTERVAL '1 day') AS rows_business_yesterday,
        COUNT(*) FILTER (WHERE registration_date = CURRENT_DATE) AS rows_business_today,
        COUNT(*) FILTER (WHERE created_at::date = CURRENT_DATE - INTERVAL '1 day') AS rows_ingested_yesterday,
        COUNT(*) FILTER (WHERE created_at::date = CURRENT_DATE) AS rows_ingested_today
    FROM public.module_ct_scouting_daily
    WHERE registration_date IS NOT NULL
),
-- COMENTADO: module_ct_cabinet_migrations no existe en esta base de datos
-- Descomenta esta CTE cuando la tabla esté disponible
/*
source_module_ct_cabinet_migrations AS (
    -- NOTA: Si la tabla no existe, esta CTE retornará 0 filas
    SELECT 
        'module_ct_cabinet_migrations' AS source_name,
        MAX(COALESCE(migration_date, created_at::date)) AS max_business_date,
        CURRENT_DATE - MAX(COALESCE(migration_date, created_at::date)) AS business_days_lag,
        MAX(COALESCE(created_at, updated_at))::timestamptz AS max_ingestion_ts,
        NOW() - MAX(COALESCE(created_at, updated_at))::timestamptz AS ingestion_lag_interval,
        COUNT(*) FILTER (
            WHERE COALESCE(migration_date, created_at::date) = CURRENT_DATE - INTERVAL '1 day'
        ) AS rows_business_yesterday,
        COUNT(*) FILTER (
            WHERE COALESCE(migration_date, created_at::date) = CURRENT_DATE
        ) AS rows_business_today,
        COUNT(*) FILTER (
            WHERE COALESCE(created_at, updated_at)::date = CURRENT_DATE - INTERVAL '1 day'
        ) AS rows_ingested_yesterday,
        COUNT(*) FILTER (
            WHERE COALESCE(created_at, updated_at)::date = CURRENT_DATE
        ) AS rows_ingested_today
    FROM public.module_ct_cabinet_migrations
    WHERE (migration_date IS NOT NULL OR created_at IS NOT NULL)
),
*/
source_module_ct_scout_drivers AS (
    -- NOTA: Si la tabla no existe, esta CTE retornará 0 filas
    -- CORREGIDO: La tabla solo tiene created_at (no tiene date ni registration_date)
    SELECT 
        'module_ct_scout_drivers' AS source_name,
        MAX(created_at::date) AS max_business_date,
        CURRENT_DATE - MAX(created_at::date) AS business_days_lag,
        MAX(COALESCE(created_at, updated_at))::timestamptz AS max_ingestion_ts,
        NOW() - MAX(COALESCE(created_at, updated_at))::timestamptz AS ingestion_lag_interval,
        COUNT(*) FILTER (
            WHERE created_at::date = CURRENT_DATE - INTERVAL '1 day'
        ) AS rows_business_yesterday,
        COUNT(*) FILTER (
            WHERE created_at::date = CURRENT_DATE
        ) AS rows_business_today,
        COUNT(*) FILTER (
            WHERE COALESCE(created_at, updated_at)::date = CURRENT_DATE - INTERVAL '1 day'
        ) AS rows_ingested_yesterday,
        COUNT(*) FILTER (
            WHERE COALESCE(created_at, updated_at)::date = CURRENT_DATE
        ) AS rows_ingested_today
    FROM public.module_ct_scout_drivers
    WHERE created_at IS NOT NULL
),
source_module_ct_cabinet_payments AS (
    -- NOTA: Si la tabla no existe, esta CTE retornará 0 filas
    SELECT 
        'module_ct_cabinet_payments' AS source_name,
        MAX(COALESCE(pay_date, payment_date, date, created_at::date)) AS max_business_date,
        CURRENT_DATE - MAX(COALESCE(pay_date, payment_date, date, created_at::date)) AS business_days_lag,
        MAX(COALESCE(snapshot_at, created_at, updated_at))::timestamptz AS max_ingestion_ts,
        NOW() - MAX(COALESCE(snapshot_at, created_at, updated_at))::timestamptz AS ingestion_lag_interval,
        COUNT(*) FILTER (
            WHERE COALESCE(pay_date, payment_date, date, created_at::date) = CURRENT_DATE - INTERVAL '1 day'
        ) AS rows_business_yesterday,
        COUNT(*) FILTER (
            WHERE COALESCE(pay_date, payment_date, date, created_at::date) = CURRENT_DATE
        ) AS rows_business_today,
        COUNT(*) FILTER (
            WHERE COALESCE(snapshot_at, created_at, updated_at)::date = CURRENT_DATE - INTERVAL '1 day'
        ) AS rows_ingested_yesterday,
        COUNT(*) FILTER (
            WHERE COALESCE(snapshot_at, created_at, updated_at)::date = CURRENT_DATE
        ) AS rows_ingested_today
    FROM public.module_ct_cabinet_payments
    WHERE (pay_date IS NOT NULL OR payment_date IS NOT NULL OR date IS NOT NULL OR created_at IS NOT NULL)
),
source_drivers AS (
    SELECT 
        'drivers' AS source_name,
        MAX(COALESCE(hire_date, created_at::date, updated_at::date)) AS max_business_date,
        CURRENT_DATE - MAX(COALESCE(hire_date, created_at::date, updated_at::date)) AS business_days_lag,
        MAX(COALESCE(updated_at, created_at))::timestamptz AS max_ingestion_ts,
        NOW() - MAX(COALESCE(updated_at, created_at))::timestamptz AS ingestion_lag_interval,
        COUNT(*) FILTER (
            WHERE COALESCE(hire_date, created_at::date, updated_at::date) = CURRENT_DATE - INTERVAL '1 day'
        ) AS rows_business_yesterday,
        COUNT(*) FILTER (
            WHERE COALESCE(hire_date, created_at::date, updated_at::date) = CURRENT_DATE
        ) AS rows_business_today,
        COUNT(*) FILTER (
            WHERE COALESCE(updated_at, created_at)::date = CURRENT_DATE - INTERVAL '1 day'
        ) AS rows_ingested_yesterday,
        COUNT(*) FILTER (
            WHERE COALESCE(updated_at, created_at)::date = CURRENT_DATE
        ) AS rows_ingested_today
    FROM public.drivers
    WHERE created_at IS NOT NULL OR updated_at IS NOT NULL
),
source_module_ct_scouts_list AS (
    -- NOTA: Si la tabla no existe, esta CTE retornará 0 filas
    SELECT 
        'module_ct_scouts_list' AS source_name,
        MAX(COALESCE(created_at::date, updated_at::date)) AS max_business_date,
        CURRENT_DATE - MAX(COALESCE(created_at::date, updated_at::date)) AS business_days_lag,
        MAX(COALESCE(updated_at, created_at))::timestamptz AS max_ingestion_ts,
        NOW() - MAX(COALESCE(updated_at, created_at))::timestamptz AS ingestion_lag_interval,
        COUNT(*) FILTER (
            WHERE COALESCE(created_at::date, updated_at::date) = CURRENT_DATE - INTERVAL '1 day'
        ) AS rows_business_yesterday,
        COUNT(*) FILTER (
            WHERE COALESCE(created_at::date, updated_at::date) = CURRENT_DATE
        ) AS rows_business_today,
        COUNT(*) FILTER (
            WHERE COALESCE(updated_at, created_at)::date = CURRENT_DATE - INTERVAL '1 day'
        ) AS rows_ingested_yesterday,
        COUNT(*) FILTER (
            WHERE COALESCE(updated_at, created_at)::date = CURRENT_DATE
        ) AS rows_ingested_today
    FROM public.module_ct_scouts_list
    WHERE (created_at IS NOT NULL OR updated_at IS NOT NULL)
)
-- NOTA: Las CTEs opcionales (raw.module_ct_cabinet_payments, module_ct_cabinet_migrations, etc.)
-- solo retornarán filas si las tablas existen. Si no existen, la vista se creará igual pero
-- esas fuentes no aparecerán en los resultados.
SELECT * FROM source_summary_daily
UNION ALL
SELECT * FROM source_yango_payment_ledger
-- UNION ALL
-- SELECT * FROM source_raw_module_ct_cabinet_payments  -- COMENTADO: tabla no existe
UNION ALL
SELECT * FROM source_module_ct_cabinet_leads
UNION ALL
SELECT * FROM source_module_ct_scouting_daily
-- UNION ALL
-- SELECT * FROM source_module_ct_cabinet_migrations  -- COMENTADO: tabla no existe
UNION ALL
SELECT * FROM source_module_ct_scout_drivers
UNION ALL
SELECT * FROM source_module_ct_cabinet_payments
UNION ALL
SELECT * FROM source_drivers
UNION ALL
SELECT * FROM source_module_ct_scouts_list;

-- Comentarios freshness_status
COMMENT ON VIEW ops.v_data_freshness_status IS 
'Vista de frescura de datos por fuente. 1 fila por fuente con métricas de business_date e ingestion_ts.';

-- ============================================================================
-- Vista: ops.v_data_ingestion_daily
-- ============================================================================
-- 1 fila por (source_name, metric_type, metric_date) con rows_count
-- ============================================================================

CREATE OR REPLACE VIEW ops.v_data_ingestion_daily AS
WITH source_summary_daily_daily AS (
    SELECT 
        'summary_daily' AS source_name,
        'business' AS metric_type,
        CASE 
            WHEN date_file ~ '^\d{2}-\d{2}-\d{4}$' THEN to_date(date_file, 'DD-MM-YYYY')
            WHEN date_file ~ '^\d{4}-\d{2}-\d{2}$' THEN to_date(date_file, 'YYYY-MM-DD')
            ELSE NULL
        END AS metric_date,
        COUNT(*) AS rows_count
    FROM public.summary_daily
    WHERE date_file IS NOT NULL
        AND (date_file ~ '^\d{2}-\d{2}-\d{4}$' OR date_file ~ '^\d{4}-\d{2}-\d{2}$')
        AND CASE 
            WHEN date_file ~ '^\d{2}-\d{2}-\d{4}$' THEN to_date(date_file, 'DD-MM-YYYY')
            WHEN date_file ~ '^\d{4}-\d{2}-\d{2}$' THEN to_date(date_file, 'YYYY-MM-DD')
            ELSE NULL
        END IS NOT NULL
        AND CASE 
            WHEN date_file ~ '^\d{2}-\d{2}-\d{4}$' THEN to_date(date_file, 'DD-MM-YYYY')
            WHEN date_file ~ '^\d{4}-\d{2}-\d{2}$' THEN to_date(date_file, 'YYYY-MM-DD')
            ELSE NULL
        END >= CURRENT_DATE - INTERVAL '90 days'
    GROUP BY 
        CASE 
            WHEN date_file ~ '^\d{2}-\d{2}-\d{4}$' THEN to_date(date_file, 'DD-MM-YYYY')
            WHEN date_file ~ '^\d{4}-\d{2}-\d{2}$' THEN to_date(date_file, 'YYYY-MM-DD')
            ELSE NULL
        END
    UNION ALL
    SELECT 
        'summary_daily' AS source_name,
        'ingestion' AS metric_type,
        created_at::date AS metric_date,
        COUNT(*) AS rows_count
    FROM public.summary_daily
    WHERE created_at IS NOT NULL
        AND created_at::date >= CURRENT_DATE - INTERVAL '90 days'
    GROUP BY created_at::date
),
source_yango_payment_ledger_daily AS (
    SELECT 
        'yango_payment_ledger' AS source_name,
        'business' AS metric_type,
        pay_date AS metric_date,
        COUNT(*) AS rows_count
    FROM ops.yango_payment_ledger
    WHERE pay_date IS NOT NULL
        AND pay_date >= CURRENT_DATE - INTERVAL '90 days'
    GROUP BY pay_date
    UNION ALL
    SELECT 
        'yango_payment_ledger' AS source_name,
        'ingestion' AS metric_type,
        snapshot_at::date AS metric_date,
        COUNT(*) AS rows_count
    FROM ops.yango_payment_ledger
    WHERE snapshot_at IS NOT NULL
        AND snapshot_at::date >= CURRENT_DATE - INTERVAL '90 days'
    GROUP BY snapshot_at::date
),
-- COMENTADO: raw.module_ct_cabinet_payments no existe en esta base de datos
-- Descomenta esta CTE cuando la tabla esté disponible
/*
source_raw_module_ct_cabinet_payments_daily AS (
    -- NOTA: Si raw.module_ct_cabinet_payments no existe, comentar esta CTE y su línea en UNION ALL
    SELECT 
        'raw_module_ct_cabinet_payments' AS source_name,
        'business' AS metric_type,
        COALESCE(pay_date, payment_date, date, created_at::date) AS metric_date,
        COUNT(*) AS rows_count
    FROM raw.module_ct_cabinet_payments
    WHERE COALESCE(pay_date, payment_date, date, created_at::date) >= CURRENT_DATE - INTERVAL '90 days'
    GROUP BY COALESCE(pay_date, payment_date, date, created_at::date)
    UNION ALL
    SELECT 
        'raw_module_ct_cabinet_payments' AS source_name,
        'ingestion' AS metric_type,
        COALESCE(snapshot_at, loaded_at, ingested_at, created_at, updated_at)::date AS metric_date,
        COUNT(*) AS rows_count
    FROM raw.module_ct_cabinet_payments
    WHERE COALESCE(snapshot_at, loaded_at, ingested_at, created_at, updated_at)::date >= CURRENT_DATE - INTERVAL '90 days'
    GROUP BY COALESCE(snapshot_at, loaded_at, ingested_at, created_at, updated_at)::date
),
*/
source_module_ct_cabinet_leads_daily AS (
    SELECT 
        'module_ct_cabinet_leads' AS source_name,
        'business' AS metric_type,
        lead_created_at::date AS metric_date,
        COUNT(*) AS rows_count
    FROM public.module_ct_cabinet_leads
    WHERE lead_created_at IS NOT NULL
        AND lead_created_at::date >= CURRENT_DATE - INTERVAL '90 days'
    GROUP BY lead_created_at::date
    UNION ALL
    SELECT 
        'module_ct_cabinet_leads' AS source_name,
        'ingestion' AS metric_type,
        lead_created_at::date AS metric_date,
        COUNT(*) AS rows_count
    FROM public.module_ct_cabinet_leads
    WHERE lead_created_at IS NOT NULL
        AND lead_created_at::date >= CURRENT_DATE - INTERVAL '90 days'
    GROUP BY lead_created_at::date
),
source_module_ct_scouting_daily_daily AS (
    SELECT 
        'module_ct_scouting_daily' AS source_name,
        'business' AS metric_type,
        registration_date AS metric_date,
        COUNT(*) AS rows_count
    FROM public.module_ct_scouting_daily
    WHERE registration_date IS NOT NULL
        AND registration_date >= CURRENT_DATE - INTERVAL '90 days'
    GROUP BY registration_date
    UNION ALL
    SELECT 
        'module_ct_scouting_daily' AS source_name,
        'ingestion' AS metric_type,
        created_at::date AS metric_date,
        COUNT(*) AS rows_count
    FROM public.module_ct_scouting_daily
    WHERE created_at IS NOT NULL
        AND created_at::date >= CURRENT_DATE - INTERVAL '90 days'
    GROUP BY created_at::date
),
-- COMENTADO: module_ct_cabinet_migrations no existe en esta base de datos
-- Descomenta esta CTE cuando la tabla esté disponible
/*
source_module_ct_cabinet_migrations_daily AS (
    -- NOTA: Si la tabla no existe, comentar esta CTE y su línea en UNION ALL
    SELECT 
        'module_ct_cabinet_migrations' AS source_name,
        'business' AS metric_type,
        COALESCE(migration_date, created_at::date) AS metric_date,
        COUNT(*) AS rows_count
    FROM public.module_ct_cabinet_migrations
    WHERE COALESCE(migration_date, created_at::date) >= CURRENT_DATE - INTERVAL '90 days'
    GROUP BY COALESCE(migration_date, created_at::date)
    UNION ALL
    SELECT 
        'module_ct_cabinet_migrations' AS source_name,
        'ingestion' AS metric_type,
        COALESCE(created_at, updated_at)::date AS metric_date,
        COUNT(*) AS rows_count
    FROM public.module_ct_cabinet_migrations
    WHERE COALESCE(created_at, updated_at)::date >= CURRENT_DATE - INTERVAL '90 days'
    GROUP BY COALESCE(created_at, updated_at)::date
),
*/
source_module_ct_scout_drivers_daily AS (
    -- NOTA: Si la tabla no existe, comentar esta CTE y su línea en UNION ALL
    -- CORREGIDO: La tabla solo tiene created_at (no tiene date ni registration_date)
    SELECT 
        'module_ct_scout_drivers' AS source_name,
        'business' AS metric_type,
        created_at::date AS metric_date,
        COUNT(*) AS rows_count
    FROM public.module_ct_scout_drivers
    WHERE created_at IS NOT NULL
        AND created_at::date >= CURRENT_DATE - INTERVAL '90 days'
    GROUP BY created_at::date
    UNION ALL
    SELECT 
        'module_ct_scout_drivers' AS source_name,
        'ingestion' AS metric_type,
        COALESCE(created_at, updated_at)::date AS metric_date,
        COUNT(*) AS rows_count
    FROM public.module_ct_scout_drivers
    WHERE COALESCE(created_at, updated_at)::date >= CURRENT_DATE - INTERVAL '90 days'
    GROUP BY COALESCE(created_at, updated_at)::date
),
source_module_ct_cabinet_payments_daily AS (
    -- NOTA: Si la tabla no existe, comentar esta CTE y su línea en UNION ALL
    SELECT 
        'module_ct_cabinet_payments' AS source_name,
        'business' AS metric_type,
        COALESCE(pay_date, payment_date, date, created_at::date) AS metric_date,
        COUNT(*) AS rows_count
    FROM public.module_ct_cabinet_payments
    WHERE COALESCE(pay_date, payment_date, date, created_at::date) >= CURRENT_DATE - INTERVAL '90 days'
    GROUP BY COALESCE(pay_date, payment_date, date, created_at::date)
    UNION ALL
    SELECT 
        'module_ct_cabinet_payments' AS source_name,
        'ingestion' AS metric_type,
        COALESCE(snapshot_at, created_at, updated_at)::date AS metric_date,
        COUNT(*) AS rows_count
    FROM public.module_ct_cabinet_payments
    WHERE COALESCE(snapshot_at, created_at, updated_at)::date >= CURRENT_DATE - INTERVAL '90 days'
    GROUP BY COALESCE(snapshot_at, created_at, updated_at)::date
),
source_drivers_daily AS (
    SELECT 
        'drivers' AS source_name,
        'business' AS metric_type,
        COALESCE(hire_date, COALESCE(updated_at, created_at)::date) AS metric_date,
        COUNT(*) AS rows_count
    FROM public.drivers
    WHERE (created_at IS NOT NULL OR updated_at IS NOT NULL)
        AND COALESCE(hire_date, COALESCE(updated_at, created_at)::date) >= CURRENT_DATE - INTERVAL '90 days'
    GROUP BY COALESCE(hire_date, COALESCE(updated_at, created_at)::date)
    UNION ALL
    SELECT 
        'drivers' AS source_name,
        'ingestion' AS metric_type,
        COALESCE(updated_at, created_at)::date AS metric_date,
        COUNT(*) AS rows_count
    FROM public.drivers
    WHERE (created_at IS NOT NULL OR updated_at IS NOT NULL)
        AND COALESCE(updated_at, created_at)::date >= CURRENT_DATE - INTERVAL '90 days'
    GROUP BY COALESCE(updated_at, created_at)::date
),
source_module_ct_scouts_list_daily AS (
    -- NOTA: Si la tabla no existe, comentar esta CTE y su línea en UNION ALL
    SELECT 
        'module_ct_scouts_list' AS source_name,
        'business' AS metric_type,
        COALESCE(created_at::date, updated_at::date) AS metric_date,
        COUNT(*) AS rows_count
    FROM public.module_ct_scouts_list
    WHERE COALESCE(created_at::date, updated_at::date) >= CURRENT_DATE - INTERVAL '90 days'
    GROUP BY COALESCE(created_at::date, updated_at::date)
    UNION ALL
    SELECT 
        'module_ct_scouts_list' AS source_name,
        'ingestion' AS metric_type,
        COALESCE(updated_at, created_at)::date AS metric_date,
        COUNT(*) AS rows_count
    FROM public.module_ct_scouts_list
    WHERE COALESCE(updated_at, created_at)::date >= CURRENT_DATE - INTERVAL '90 days'
    GROUP BY COALESCE(updated_at, created_at)::date
)
-- NOTA IMPORTANTE: Si alguna tabla opcional no existe (raw.module_ct_cabinet_payments, 
-- module_ct_cabinet_migrations, module_ct_scout_drivers, module_ct_cabinet_payments, module_ct_scouts_list),
-- comentar la CTE correspondiente (source_*_daily) y su línea en UNION ALL.
SELECT * FROM source_summary_daily_daily
UNION ALL
SELECT * FROM source_yango_payment_ledger_daily
-- UNION ALL
-- SELECT * FROM source_raw_module_ct_cabinet_payments_daily  -- COMENTADO: tabla no existe
UNION ALL
SELECT * FROM source_module_ct_cabinet_leads_daily
UNION ALL
SELECT * FROM source_module_ct_scouting_daily_daily
-- UNION ALL
-- SELECT * FROM source_module_ct_cabinet_migrations_daily  -- COMENTADO: tabla no existe
UNION ALL
SELECT * FROM source_module_ct_scout_drivers_daily
UNION ALL
SELECT * FROM source_module_ct_cabinet_payments_daily
UNION ALL
SELECT * FROM source_drivers_daily
UNION ALL
SELECT * FROM source_module_ct_scouts_list_daily;

COMMENT ON VIEW ops.v_data_ingestion_daily IS 
'Vista diaria de ingesta por fuente. 1 fila por (source_name, metric_type, metric_date) con rows_count.';

-- ============================================================================
-- Vista: ops.v_data_health_status
-- ============================================================================
-- Basada en ops.v_data_freshness_status
-- Agrega source_type y health_status calculado según reglas por tipo
-- ============================================================================

CREATE OR REPLACE VIEW ops.v_data_health_status AS
SELECT 
    f.source_name,
    c.source_type,
    f.max_business_date,
    f.business_days_lag,
    f.max_ingestion_ts,
    f.ingestion_lag_interval,
    f.rows_business_yesterday,
    f.rows_business_today,
    f.rows_ingested_yesterday,
    f.rows_ingested_today,
    CASE 
        -- MASTER: siempre GREEN salvo si no hay datos
        WHEN c.source_type = 'master' THEN
            CASE 
                WHEN f.max_ingestion_ts IS NULL THEN 'RED_NO_DATA'
                ELSE 'GREEN_OK'
            END
        
        -- ACTIVITY: summary_daily
        WHEN c.source_type = 'activity' THEN
            CASE 
                WHEN f.rows_ingested_today = 0 AND f.rows_ingested_yesterday = 0 THEN 'RED_NO_INGESTION_2D'
                WHEN f.ingestion_lag_interval > INTERVAL '18 hours' THEN 'RED_INGESTION_STALE'
                WHEN f.business_days_lag >= 2 THEN 'YELLOW_BUSINESS_LAG'
                ELSE 'GREEN_OK'
            END
        
        -- UPSTREAM / LEDGER / CT_INGEST: reglas específicas
        WHEN c.source_type IN ('upstream', 'ledger', 'ct_ingest') THEN
            CASE 
                WHEN f.rows_ingested_today = 0 AND f.rows_ingested_yesterday = 0 THEN 'RED_NO_INGESTION_2D'
                WHEN f.rows_ingested_today = 0 AND f.rows_ingested_yesterday > 0 THEN 'YELLOW_INGESTION_1D'
                WHEN f.ingestion_lag_interval > INTERVAL '18 hours' THEN 'RED_INGESTION_STALE'
                WHEN f.business_days_lag >= 2 THEN 'YELLOW_BUSINESS_LAG'
                ELSE 'GREEN_OK'
            END
        
        ELSE 'UNKNOWN'
    END AS health_status
FROM ops.v_data_freshness_status f
LEFT JOIN ops.v_data_sources_catalog c ON f.source_name = c.source_name;

COMMENT ON VIEW ops.v_data_health_status IS 
'Vista de salud de datos por fuente. Basada en v_data_freshness_status con source_type y health_status calculado según reglas por tipo.';

COMMENT ON COLUMN ops.v_data_health_status.source_type IS 
'Tipo de fuente: activity, ledger, upstream, ct_ingest, master.';

COMMENT ON COLUMN ops.v_data_health_status.health_status IS 
'Estado de salud calculado según source_type: RED_NO_INGESTION_2D, YELLOW_INGESTION_1D, RED_INGESTION_STALE, YELLOW_BUSINESS_LAG, RED_NO_DATA, GREEN_OK, UNKNOWN.';

-- ============================================================================
-- QUERIES DE VALIDACIÓN
-- ============================================================================
-- Para verificar las vistas:
--
-- SELECT * FROM ops.v_data_sources_catalog ORDER BY source_name;
-- SELECT * FROM ops.v_data_freshness_status ORDER BY source_name;
-- SELECT * FROM ops.v_data_health_status ORDER BY source_type, source_name;
-- SELECT * FROM ops.v_data_ingestion_daily 
--   WHERE metric_date >= CURRENT_DATE - 30 
--   ORDER BY source_name, metric_type, metric_date DESC;
-- ============================================================================

