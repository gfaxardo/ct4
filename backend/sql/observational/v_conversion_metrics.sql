-- Vista de Métricas de Conversión (Fase 2.2)
-- Proporciona métricas de conversión por lead/persona agrupada por (person_key, origin_tag)
-- 
-- NOTA: Esta vista requiere que exista la columna sum_work_time_seconds en public.summary_daily.
-- Si la columna no existe, el usuario debe modificar la vista para usar count_orders_completed > 0
-- como indicador de conexión (ver comentario en la sección first_connection_date).

CREATE OR REPLACE VIEW observational.v_conversion_metrics AS
WITH lead_events_with_origin AS (
    -- Paso 1a: Agregar origin_tag a cada evento
    SELECT 
        le.person_key,
        le.event_date,
        le.scout_id,
        le.created_at,
        COALESCE(
            le.payload_json->>'origin_tag',
            CASE 
                WHEN le.source_table = 'module_ct_migrations' THEN 'fleet_migration'
                WHEN le.source_table = 'module_ct_cabinet_leads' THEN 'cabinet'
                WHEN le.source_table = 'module_ct_scouting_daily' THEN 'cabinet'
                ELSE COALESCE((SELECT attributed_source FROM observational.lead_ledger ll WHERE ll.person_key = le.person_key LIMIT 1), 'unknown')
            END
        ) AS origin_tag
    FROM observational.lead_events le
    WHERE le.person_key IS NOT NULL
),
lead_origin_base AS (
    -- Paso 1b: Agrupar por (person_key, origin_tag) y obtener lead_date y scout_id
    SELECT 
        lewo.person_key,
        lewo.origin_tag,
        MIN(lewo.event_date) AS lead_date,
        -- Para fleet_migration: scout_id del evento más reciente; para cabinet: NULL
        CASE 
            WHEN lewo.origin_tag = 'fleet_migration' 
            THEN (
                SELECT lewo2.scout_id 
                FROM lead_events_with_origin lewo2 
                WHERE lewo2.person_key = lewo.person_key
                    AND lewo2.origin_tag = 'fleet_migration'
                ORDER BY lewo2.event_date DESC, lewo2.created_at DESC
                LIMIT 1
            )
            ELSE NULL
        END AS scout_id
    FROM lead_events_with_origin lewo
    GROUP BY lewo.person_key, lewo.origin_tag
),
driver_resolution AS (
    -- Paso 2: Resolver driver_id desde canon.identity_links
    SELECT DISTINCT ON (lob.person_key, lob.origin_tag)
        lob.person_key,
        lob.origin_tag,
        lob.lead_date,
        lob.scout_id,
        il.source_pk AS driver_id
    FROM lead_origin_base lob
    LEFT JOIN canon.identity_links il 
        ON il.person_key = lob.person_key 
        AND il.source_table = 'drivers'
    ORDER BY lob.person_key, lob.origin_tag, il.linked_at DESC NULLS LAST
),
drivers_info AS (
    -- Paso 3: Obtener hire_date desde public.drivers
    SELECT 
        dr.person_key,
        dr.origin_tag,
        dr.lead_date,
        dr.scout_id,
        dr.driver_id,
        d.hire_date
    FROM driver_resolution dr
    LEFT JOIN public.drivers d ON d.driver_id = dr.driver_id
),
summary_daily_normalized AS (
    -- Paso 4: Normalizar summary_daily con fecha convertida
    SELECT 
        driver_id,
        to_date(date_file, 'DD-MM-YYYY') AS prod_date,
        count_orders_completed,
        -- NOTA: Si sum_work_time_seconds no existe, reemplazar esta línea con:
        -- CASE WHEN count_orders_completed > 0 THEN 1 ELSE 0 END AS has_connection
        CASE 
            WHEN sum_work_time_seconds > 0 THEN 1 
            ELSE 0 
        END AS has_connection
    FROM public.summary_daily
    WHERE date_file IS NOT NULL
        AND date_file ~ '^\d{2}-\d{2}-\d{4}$'  -- Validar formato DD-MM-YYYY
),
daily_production_metrics AS (
    -- Paso 5: Calcular métricas diarias acumulativas por driver
    SELECT 
        driver_id,
        prod_date,
        count_orders_completed,
        has_connection,
        SUM(count_orders_completed) OVER (
            PARTITION BY driver_id 
            ORDER BY prod_date 
            ROWS UNBOUNDED PRECEDING
        ) AS cumulative_trips
    FROM summary_daily_normalized
),
connection_events AS (
    -- Primera conexión por lead (person_key, origin_tag) desde lead_date
    SELECT 
        di.person_key,
        di.origin_tag,
        di.driver_id,
        MIN(dpm.prod_date) AS first_connection_date
    FROM drivers_info di
    INNER JOIN daily_production_metrics dpm
        ON dpm.driver_id = di.driver_id
        AND dpm.prod_date >= di.lead_date
    WHERE dpm.has_connection = 1
    GROUP BY di.person_key, di.origin_tag, di.driver_id
),
trip_events AS (
    -- Primer viaje por lead (person_key, origin_tag) desde lead_date
    SELECT 
        di.person_key,
        di.origin_tag,
        di.driver_id,
        MIN(dpm.prod_date) AS first_trip_date
    FROM drivers_info di
    INNER JOIN daily_production_metrics dpm
        ON dpm.driver_id = di.driver_id
        AND dpm.prod_date >= di.lead_date
    WHERE dpm.count_orders_completed > 0
    GROUP BY di.person_key, di.origin_tag, di.driver_id
),
drivers_with_production AS (
    -- Combinar drivers_info con producción diaria para calcular acumulados desde lead_date
    SELECT 
        di.person_key,
        di.origin_tag,
        di.driver_id,
        di.lead_date,
        dpm.prod_date,
        dpm.count_orders_completed,
        SUM(dpm.count_orders_completed) OVER (
            PARTITION BY di.person_key, di.origin_tag, di.driver_id
            ORDER BY dpm.prod_date
            ROWS UNBOUNDED PRECEDING
        ) AS cumulative_trips_from_lead
    FROM drivers_info di
    INNER JOIN daily_production_metrics dpm
        ON dpm.driver_id = di.driver_id
        AND dpm.prod_date >= di.lead_date
),
trip_hit_5 AS (
    -- Primera fecha donde acumulado desde lead_date >= 5 viajes
    SELECT DISTINCT ON (person_key, origin_tag)
        person_key,
        origin_tag,
        driver_id,
        prod_date AS trip_5_date
    FROM drivers_with_production
    WHERE cumulative_trips_from_lead >= 5
    ORDER BY person_key, origin_tag, prod_date ASC
),
trip_hit_25 AS (
    -- Primera fecha donde acumulado desde lead_date >= 25 viajes
    SELECT DISTINCT ON (person_key, origin_tag)
        person_key,
        origin_tag,
        driver_id,
        prod_date AS trip_25_date
    FROM drivers_with_production
    WHERE cumulative_trips_from_lead >= 25
    ORDER BY person_key, origin_tag, prod_date ASC
),
time_windows AS (
    -- Calcular viajes en ventanas de 7, 14, 30 días desde lead_date
    SELECT 
        di.person_key,
        di.origin_tag,
        di.driver_id,
        di.lead_date,
        -- Viajes en primeros 7 días
        COALESCE(SUM(CASE 
            WHEN dpm.prod_date >= di.lead_date 
                AND dpm.prod_date < di.lead_date + INTERVAL '7 days'
            THEN dpm.count_orders_completed 
            ELSE 0 
        END), 0) AS trips_7d,
        -- Viajes en primeros 14 días
        COALESCE(SUM(CASE 
            WHEN dpm.prod_date >= di.lead_date 
                AND dpm.prod_date < di.lead_date + INTERVAL '14 days'
            THEN dpm.count_orders_completed 
            ELSE 0 
        END), 0) AS trips_14d,
        -- Viajes en primeros 30 días
        COALESCE(SUM(CASE 
            WHEN dpm.prod_date >= di.lead_date 
                AND dpm.prod_date < di.lead_date + INTERVAL '30 days'
            THEN dpm.count_orders_completed 
            ELSE 0 
        END), 0) AS trips_30d
    FROM drivers_info di
    LEFT JOIN daily_production_metrics dpm 
        ON dpm.driver_id = di.driver_id
        AND dpm.prod_date >= di.lead_date
    GROUP BY di.person_key, di.origin_tag, di.driver_id, di.lead_date
)
-- Selección final combinando todas las métricas
SELECT 
    di.person_key,
    di.origin_tag,
    di.lead_date,
    di.scout_id,
    di.driver_id,
    di.hire_date,
    ce.first_connection_date,
    te.first_trip_date,
    te.first_trip_date AS trip_1_date,
    t5.trip_5_date,
    t25.trip_25_date,
    -- Calcular tiempos en días (NULL si no hay fecha)
    CASE 
        WHEN ce.first_connection_date IS NOT NULL 
        THEN (ce.first_connection_date - di.lead_date)
        ELSE NULL 
    END AS time_to_connection_days,
    CASE 
        WHEN te.first_trip_date IS NOT NULL 
        THEN (te.first_trip_date - di.lead_date)
        ELSE NULL 
    END AS time_to_1_days,
    CASE 
        WHEN t5.trip_5_date IS NOT NULL 
        THEN (t5.trip_5_date - di.lead_date)
        ELSE NULL 
    END AS time_to_5_days,
    CASE 
        WHEN t25.trip_25_date IS NOT NULL 
        THEN (t25.trip_25_date - di.lead_date)
        ELSE NULL 
    END AS time_to_25_days,
    tw.trips_7d,
    tw.trips_14d,
    tw.trips_30d
FROM drivers_info di
LEFT JOIN connection_events ce 
    ON ce.person_key = di.person_key 
    AND ce.origin_tag = di.origin_tag
    AND ce.driver_id = di.driver_id
LEFT JOIN trip_events te 
    ON te.person_key = di.person_key 
    AND te.origin_tag = di.origin_tag
    AND te.driver_id = di.driver_id
LEFT JOIN trip_hit_5 t5 ON t5.person_key = di.person_key AND t5.origin_tag = di.origin_tag
LEFT JOIN trip_hit_25 t25 ON t25.person_key = di.person_key AND t25.origin_tag = di.origin_tag
LEFT JOIN time_windows tw 
    ON tw.person_key = di.person_key 
    AND tw.origin_tag = di.origin_tag
    AND tw.driver_id = di.driver_id;

COMMENT ON VIEW observational.v_conversion_metrics IS 
'Vista de métricas de conversión por lead/persona. Agrupa por (person_key, origin_tag) y calcula:
- Fechas de hitos: conexión, 1 viaje, 5 viajes, 25 viajes
- Tiempos de conversión en días desde lead_date
- Viajes acumulados en ventanas de 7, 14, 30 días

REQUISITO: La columna sum_work_time_seconds debe existir en public.summary_daily.
Si no existe, modificar la vista reemplazando la columna has_connection en summary_daily_normalized.';

