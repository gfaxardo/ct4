-- ============================================================================
-- Vista: ops.v_cabinet_milestones_achieved_from_trips
-- ============================================================================
-- PROPÓSITO:
-- Vista determinística que calcula milestones ACHIEVED basándose únicamente
-- en viajes reales desde summary_daily. NO depende de eventos históricos
-- ni de reglas de pago. Cálculo puro basado en acumulación de trips.
--
-- ARQUITECTURA:
-- Esta vista es una alternativa determinística a v_cabinet_milestones_achieved
-- que resuelve inconsistencias como M5 achieved sin M1 achieved.
--
-- CAPA: C2 - Elegibilidad (ACHIEVED) - Versión Determinística
-- ============================================================================
-- REGLAS DE NEGOCIO:
-- 1. M1 ACHIEVED si trips acumulados >= 1
-- 2. M5 ACHIEVED si trips acumulados >= 5
-- 3. M25 ACHIEVED si trips acumulados >= 25
-- 4. Si se alcanza un milestone mayor, todos los menores se consideran achieved
--    (ej: si M5 achieved, entonces M1 también está achieved)
-- 5. achieved_date = primer día en que trips acumulados >= milestone_value
-- 6. trips_at_achieved = trips acumulados en achieved_date
-- 7. Read-only: NO modifica historia, NO recalcula pagos
-- ============================================================================
-- FUENTE OPERATIVA:
-- - Tabla: public.summary_daily
-- - Columna trips: count_orders_completed
-- - Columna fecha: date_file (formato 'DD-MM-YYYY')
-- - Parseo: to_date(date_file, 'DD-MM-YYYY')
-- ============================================================================
-- GRANO:
-- (driver_id, milestone_value) - 1 fila por milestone alcanzado
-- ============================================================================
-- USO:
-- - Consultar milestones determinísticos basados en viajes reales
-- - Comparar con v_cabinet_milestones_achieved para detectar inconsistencias
-- - Auditoría de inconsistencias M5 sin M1, M25 sin M5, etc.
-- ============================================================================

CREATE OR REPLACE VIEW ops.v_cabinet_milestones_achieved_from_trips AS
WITH cleaned_summary_daily AS (
    -- Paso 1: Limpiar y parsear summary_daily
    -- Filtrar solo registros con date_file válido y count_orders_completed > 0
    SELECT 
        driver_id,
        to_date(date_file, 'DD-MM-YYYY') AS trip_date,
        count_orders_completed AS trips
    FROM public.summary_daily
    WHERE driver_id IS NOT NULL
        AND date_file IS NOT NULL
        AND date_file ~ '^\d{2}-\d{2}-\d{4}$'  -- Formato válido DD-MM-YYYY
        AND count_orders_completed > 0  -- Solo días con viajes
),
trips_accumulated AS (
    -- Paso 2: Calcular trips acumulados por driver ordenados por fecha
    -- Window function para acumular desde el primer viaje
    SELECT 
        driver_id,
        trip_date,
        trips,
        SUM(trips) OVER (
            PARTITION BY driver_id 
            ORDER BY trip_date 
            ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW
        ) AS cumulative_trips
    FROM cleaned_summary_daily
),
milestone_thresholds AS (
    -- Paso 3: Definir thresholds de milestones
    SELECT 1 AS milestone_value
    UNION ALL SELECT 5
    UNION ALL SELECT 25
),
milestone_first_achieved AS (
    -- Paso 4: Para cada driver y milestone, encontrar el primer día donde
    -- trips acumulados >= milestone_value
    SELECT DISTINCT
        ta.driver_id,
        mt.milestone_value,
        MIN(ta.trip_date) AS achieved_date,
        MIN(ta.cumulative_trips) AS trips_at_achieved
    FROM trips_accumulated ta
    CROSS JOIN milestone_thresholds mt
    WHERE ta.cumulative_trips >= mt.milestone_value
    GROUP BY ta.driver_id, mt.milestone_value
),
milestone_expanded AS (
    -- Paso 5: Expandir milestones - calcular milestones menores faltantes
    -- Si M5 está achieved pero M1 no, calcular M1 desde trips_accumulated
    -- Si M25 está achieved pero M5 o M1 no, calcularlos desde trips_accumulated
    
    -- Milestones directamente alcanzados
    SELECT 
        driver_id,
        milestone_value,
        achieved_date,
        trips_at_achieved
    FROM milestone_first_achieved
    
    UNION ALL
    
    -- Si M5 está achieved pero M1 no, calcular M1 (primer día con >= 1 trip)
    SELECT 
        m5.driver_id,
        1 AS milestone_value,
        MIN(ta.trip_date) AS achieved_date,
        MIN(ta.cumulative_trips) AS trips_at_achieved
    FROM milestone_first_achieved m5
    INNER JOIN trips_accumulated ta ON ta.driver_id = m5.driver_id
    WHERE m5.milestone_value = 5
        AND ta.cumulative_trips >= 1
        AND NOT EXISTS (
            SELECT 1 
            FROM milestone_first_achieved m1
            WHERE m1.driver_id = m5.driver_id
                AND m1.milestone_value = 1
        )
    GROUP BY m5.driver_id
    
    UNION ALL
    
    -- Si M25 está achieved pero M5 no, calcular M5 (primer día con >= 5 trips)
    SELECT 
        m25.driver_id,
        5 AS milestone_value,
        MIN(ta.trip_date) AS achieved_date,
        MIN(ta.cumulative_trips) AS trips_at_achieved
    FROM milestone_first_achieved m25
    INNER JOIN trips_accumulated ta ON ta.driver_id = m25.driver_id
    WHERE m25.milestone_value = 25
        AND ta.cumulative_trips >= 5
        AND NOT EXISTS (
            SELECT 1 
            FROM milestone_first_achieved m5
            WHERE m5.driver_id = m25.driver_id
                AND m5.milestone_value = 5
        )
    GROUP BY m25.driver_id
    
    UNION ALL
    
    -- Si M25 está achieved pero M1 no, calcular M1 (primer día con >= 1 trip)
    SELECT 
        m25.driver_id,
        1 AS milestone_value,
        MIN(ta.trip_date) AS achieved_date,
        MIN(ta.cumulative_trips) AS trips_at_achieved
    FROM milestone_first_achieved m25
    INNER JOIN trips_accumulated ta ON ta.driver_id = m25.driver_id
    WHERE m25.milestone_value = 25
        AND ta.cumulative_trips >= 1
        AND NOT EXISTS (
            SELECT 1 
            FROM milestone_first_achieved m1
            WHERE m1.driver_id = m25.driver_id
                AND m1.milestone_value = 1
        )
    GROUP BY m25.driver_id
)
SELECT 
    driver_id,
    milestone_value,
    true AS achieved_flag,  -- Siempre true en esta vista
    achieved_date,
    trips_at_achieved
FROM milestone_expanded
ORDER BY driver_id, milestone_value;

-- ============================================================================
-- Comentarios
-- ============================================================================
COMMENT ON VIEW ops.v_cabinet_milestones_achieved_from_trips IS 
'Vista determinística que calcula milestones ACHIEVED basándose únicamente en viajes reales desde summary_daily. Resuelve inconsistencias como M5 achieved sin M1 achieved. Cálculo puro basado en acumulación de trips. Read-only. Grano: (driver_id, milestone_value).';

COMMENT ON COLUMN ops.v_cabinet_milestones_achieved_from_trips.driver_id IS 
'ID del conductor que alcanzó el milestone.';

COMMENT ON COLUMN ops.v_cabinet_milestones_achieved_from_trips.milestone_value IS 
'Valor del milestone alcanzado (1, 5, o 25).';

COMMENT ON COLUMN ops.v_cabinet_milestones_achieved_from_trips.achieved_flag IS 
'Flag indicando si se alcanzó el milestone (siempre true en esta vista).';

COMMENT ON COLUMN ops.v_cabinet_milestones_achieved_from_trips.achieved_date IS 
'Primer día en que trips acumulados >= milestone_value según summary_daily.';

COMMENT ON COLUMN ops.v_cabinet_milestones_achieved_from_trips.trips_at_achieved IS 
'Cantidad de trips acumulados en achieved_date (puede ser >= milestone_value si se alcanza en un día con múltiples viajes).';

