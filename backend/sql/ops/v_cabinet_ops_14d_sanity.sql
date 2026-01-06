-- ============================================================================
-- Vista: ops.v_cabinet_ops_14d_sanity
-- ============================================================================
-- PROPÓSITO:
-- Capa operativa de SANITY CHECK alineada a CLAIMS (ventana de 14 días).
-- Proporciona métricas operativas basadas en viajes reales desde summary_daily
-- para validar coherencia entre achieved, claims y operación real.
-- ============================================================================
-- GRANO:
-- 1 fila por driver_id (GARANTIZADO)
-- ============================================================================
-- REGLAS:
-- 1. Ventana de 14 días: desde lead_date hasta lead_date + 14 días
-- 2. Viajes reales: solo count_orders_completed desde summary_daily dentro de ventana
-- 3. Conexión: basada en sum_work_time_seconds > 0 o count_orders_completed > 0
-- 4. NO incluye lógica de pagos ni claims (puramente operativo)
-- ============================================================================
-- FUENTES:
-- - lead_date: observational.v_conversion_metrics
-- - first_connection_date: observational.v_conversion_metrics
-- - Viajes: public.summary_daily (count_orders_completed)
-- ============================================================================

CREATE OR REPLACE VIEW ops.v_cabinet_ops_14d_sanity AS
WITH conversion_base AS (
    -- Base: lead_date y first_connection_date desde v_conversion_metrics
    SELECT DISTINCT ON (driver_id)
        driver_id,
        lead_date,
        first_connection_date
    FROM observational.v_conversion_metrics
    WHERE origin_tag = 'cabinet'
        AND driver_id IS NOT NULL
        AND lead_date IS NOT NULL
    ORDER BY driver_id, lead_date DESC
),
summary_daily_normalized AS (
    -- Normalizar summary_daily con fecha convertida
    SELECT 
        driver_id,
        to_date(date_file, 'DD-MM-YYYY') AS prod_date,
        count_orders_completed,
        -- Conexión: sum_work_time_seconds > 0 o count_orders_completed > 0
        CASE 
            WHEN COALESCE(sum_work_time_seconds, 0) > 0 THEN 1
            WHEN count_orders_completed > 0 THEN 1
            ELSE 0
        END AS has_connection
    FROM public.summary_daily
    WHERE driver_id IS NOT NULL
        AND date_file IS NOT NULL
        AND date_file ~ '^\d{2}-\d{2}-\d{4}$'  -- Validar formato DD-MM-YYYY
),
trips_within_14d AS (
    -- Viajes dentro de ventana de 14 días desde lead_date
    SELECT 
        cb.driver_id,
        cb.lead_date,
        cb.first_connection_date,
        -- Ventana de 14 días: desde lead_date hasta lead_date + 14 días
        cb.lead_date + INTERVAL '14 days' AS window_end_date,
        -- Viajes completados dentro de ventana
        COALESCE(SUM(sd.count_orders_completed), 0) AS trips_completed_14d_from_lead,
        -- Primera fecha con viaje dentro de ventana
        MIN(CASE 
            WHEN sd.count_orders_completed > 0 
                AND sd.prod_date >= cb.lead_date 
                AND sd.prod_date < cb.lead_date + INTERVAL '14 days'
            THEN sd.prod_date 
        END) AS first_trip_date_within_14d,
        -- Primera fecha con conexión dentro de ventana
        MIN(CASE 
            WHEN sd.has_connection = 1 
                AND sd.prod_date >= cb.lead_date 
                AND sd.prod_date < cb.lead_date + INTERVAL '14 days'
            THEN sd.prod_date 
        END) AS first_connection_date_within_14d
    FROM conversion_base cb
    LEFT JOIN summary_daily_normalized sd
        ON sd.driver_id = cb.driver_id
        AND sd.prod_date >= cb.lead_date
        AND sd.prod_date < cb.lead_date + INTERVAL '14 days'
    GROUP BY cb.driver_id, cb.lead_date, cb.first_connection_date
)
SELECT 
    t.driver_id,
    t.lead_date,
    t.first_connection_date,
    -- Flag: conexión ocurrió dentro de ventana de 14 días
    CASE 
        WHEN t.first_connection_date_within_14d IS NOT NULL THEN true
        ELSE false
    END AS connection_within_14d_flag,
    -- Fecha de conexión dentro de ventana (NULL si fuera de ventana)
    t.first_connection_date_within_14d AS connection_date_within_14d,
    -- Viajes completados dentro de ventana de 14 días
    t.trips_completed_14d_from_lead,
    -- Primera fecha con viaje dentro de ventana (NULL si no hubo viajes)
    t.first_trip_date_within_14d
FROM trips_within_14d t;

-- ============================================================================
-- Comentarios de la Vista
-- ============================================================================
COMMENT ON VIEW ops.v_cabinet_ops_14d_sanity IS 
'Capa operativa de SANITY CHECK alineada a CLAIMS (ventana de 14 días). Proporciona métricas operativas basadas en viajes reales desde summary_daily para validar coherencia entre achieved, claims y operación real. Grano: 1 fila por driver_id.';

COMMENT ON COLUMN ops.v_cabinet_ops_14d_sanity.driver_id IS 
'ID del conductor.';

COMMENT ON COLUMN ops.v_cabinet_ops_14d_sanity.lead_date IS 
'Fecha de lead desde observational.v_conversion_metrics (origen del driver).';

COMMENT ON COLUMN ops.v_cabinet_ops_14d_sanity.first_connection_date IS 
'Primera fecha de conexión desde observational.v_conversion_metrics (puede ser fuera de ventana).';

COMMENT ON COLUMN ops.v_cabinet_ops_14d_sanity.connection_within_14d_flag IS 
'Flag indicando si la conexión ocurrió dentro de la ventana de 14 días desde lead_date. TRUE si first_connection_date_within_14d IS NOT NULL.';

COMMENT ON COLUMN ops.v_cabinet_ops_14d_sanity.connection_date_within_14d IS 
'Primera fecha de conexión dentro de la ventana de 14 días. NULL si la conexión ocurrió fuera de ventana o no hubo conexión.';

COMMENT ON COLUMN ops.v_cabinet_ops_14d_sanity.trips_completed_14d_from_lead IS 
'Total de viajes completados (count_orders_completed) dentro de la ventana de 14 días desde lead_date. Fuente: public.summary_daily.';

COMMENT ON COLUMN ops.v_cabinet_ops_14d_sanity.first_trip_date_within_14d IS 
'Primera fecha con viaje completado dentro de la ventana de 14 días. NULL si no hubo viajes dentro de ventana.';

