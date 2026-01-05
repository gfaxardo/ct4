-- ============================================================================
-- Vista: ops.v_cabinet_funnel_status
-- ============================================================================
-- PROPÓSITO:
-- Vista canónica C1 (Funnel) que muestra el estado operativo de cada driver
-- en el funnel de conversión. 1 fila por driver_id.
-- ============================================================================
-- GRANO:
-- 1 fila por driver_id
-- ============================================================================
-- ESTADOS DEL FUNNEL (mutuamente excluyentes, prioridad top-down):
-- 1. registered_incomplete: existe registro/origen pero NO hay identidad (person_key NULL o no matchea)
-- 2. registered_complete: hay person_key pero NO conectado (first_connection_date IS NULL)
-- 3. connected_no_trips: conectado pero trips_total=0
-- 4. reached_m1: milestone determinístico >=1
-- 5. reached_m5: milestone determinístico >=5
-- 6. reached_m25: milestone determinístico >=25
-- ============================================================================
-- FUENTES:
-- - Identidad: canon.identity_links (person_key)
-- - Conexión: observational.v_conversion_metrics (first_connection_date)
-- - Trips/milestones: ops.v_cabinet_milestones_achieved_from_trips (determinística)
-- - Origin: ops.v_payment_calculation (origin_tag)
-- ============================================================================

CREATE OR REPLACE VIEW ops.v_cabinet_funnel_status AS
WITH driver_identity AS (
    -- Resolver person_key por driver_id desde identity_links
    SELECT DISTINCT ON (il.source_pk)
        il.source_pk AS driver_id,
        il.person_key
    FROM canon.identity_links il
    WHERE il.source_table = 'drivers'
        AND il.source_pk IS NOT NULL
    ORDER BY il.source_pk, il.linked_at DESC
),
driver_origin AS (
    -- Obtener origin_tag por driver_id (prioridad: cabinet > fleet_migration > unknown)
    SELECT DISTINCT ON (pc.driver_id)
        pc.driver_id,
        COALESCE(
            MAX(CASE WHEN pc.origin_tag = 'cabinet' THEN 'cabinet' END),
            MAX(CASE WHEN pc.origin_tag = 'fleet_migration' THEN 'fleet_migration' END),
            'unknown'
        ) AS origin_tag
    FROM ops.v_payment_calculation pc
    WHERE pc.driver_id IS NOT NULL
    GROUP BY pc.driver_id
),
driver_connection AS (
    -- Obtener first_connection_date desde v_conversion_metrics
    SELECT DISTINCT ON (vcm.driver_id)
        vcm.driver_id,
        vcm.first_connection_date,
        vcm.trips_30d AS trips_total  -- Usar trips_30d como proxy de trips_total
    FROM observational.v_conversion_metrics vcm
    WHERE vcm.driver_id IS NOT NULL
    ORDER BY vcm.driver_id, vcm.lead_date DESC
),
driver_milestones AS (
    -- Obtener milestones determinísticos (cumulativos)
    SELECT 
        m.driver_id,
        BOOL_OR(m.milestone_value = 1 AND m.achieved_flag = true) AS m1_achieved,
        MIN(CASE WHEN m.milestone_value = 1 AND m.achieved_flag = true THEN m.achieved_date END) AS m1_date,
        BOOL_OR(m.milestone_value = 5 AND m.achieved_flag = true) AS m5_achieved,
        MIN(CASE WHEN m.milestone_value = 5 AND m.achieved_flag = true THEN m.achieved_date END) AS m5_date,
        BOOL_OR(m.milestone_value = 25 AND m.achieved_flag = true) AS m25_achieved,
        MIN(CASE WHEN m.milestone_value = 25 AND m.achieved_flag = true THEN m.achieved_date END) AS m25_date,
        -- highest_milestone: el milestone más alto alcanzado
        MAX(CASE 
            WHEN m.milestone_value = 25 AND m.achieved_flag = true THEN 25
            WHEN m.milestone_value = 5 AND m.achieved_flag = true THEN 5
            WHEN m.milestone_value = 1 AND m.achieved_flag = true THEN 1
            ELSE 0
        END) AS highest_milestone
    FROM ops.v_cabinet_milestones_achieved_from_trips m
    GROUP BY m.driver_id
),
all_drivers AS (
    -- Base: todos los drivers que aparecen en alguna fuente
    SELECT DISTINCT driver_id
    FROM (
        SELECT driver_id FROM driver_identity
        UNION
        SELECT driver_id FROM driver_origin
        UNION
        SELECT driver_id FROM driver_connection
        UNION
        SELECT driver_id FROM driver_milestones
    ) combined
)
SELECT 
    ad.driver_id,
    di.person_key,
    COALESCE(do.origin_tag, 'unknown') AS origin_tag,
    -- Funnel status (prioridad top-down)
    CASE 
        -- 1. registered_incomplete: existe registro pero NO hay identidad
        WHEN di.person_key IS NULL THEN 'registered_incomplete'
        -- 2. registered_complete: hay person_key pero NO conectado
        WHEN di.person_key IS NOT NULL AND dc.first_connection_date IS NULL THEN 'registered_complete'
        -- 3. connected_no_trips: conectado pero trips_total=0
        WHEN dc.first_connection_date IS NOT NULL AND COALESCE(dc.trips_total, 0) = 0 THEN 'connected_no_trips'
        -- 4. reached_m25: milestone determinístico >=25
        WHEN dm.m25_achieved = true THEN 'reached_m25'
        -- 5. reached_m5: milestone determinístico >=5
        WHEN dm.m5_achieved = true THEN 'reached_m5'
        -- 6. reached_m1: milestone determinístico >=1
        WHEN dm.m1_achieved = true THEN 'reached_m1'
        -- Default: connected pero sin milestone
        ELSE 'connected_no_trips'
    END AS funnel_status,
    -- Flags y fechas
    (dc.first_connection_date IS NOT NULL) AS connected_flag,
    dc.first_connection_date AS connected_date,
    COALESCE(dc.trips_total, 0) AS trips_total,
    COALESCE(dm.highest_milestone, 0) AS highest_milestone,
    dm.m1_date,
    dm.m5_date,
    dm.m25_date
FROM all_drivers ad
LEFT JOIN driver_identity di ON di.driver_id = ad.driver_id
LEFT JOIN driver_origin do ON do.driver_id = ad.driver_id
LEFT JOIN driver_connection dc ON dc.driver_id = ad.driver_id
LEFT JOIN driver_milestones dm ON dm.driver_id = ad.driver_id;

-- ============================================================================
-- Comentarios de la Vista
-- ============================================================================
COMMENT ON VIEW ops.v_cabinet_funnel_status IS 
'Vista canónica C1 (Funnel) que muestra el estado operativo de cada driver en el funnel de conversión. 1 fila por driver_id. Estados mutuamente excluyentes con prioridad top-down.';

COMMENT ON COLUMN ops.v_cabinet_funnel_status.driver_id IS 
'ID del conductor. Grano principal de la vista (1 fila por driver_id).';

COMMENT ON COLUMN ops.v_cabinet_funnel_status.person_key IS 
'Person key del conductor desde canon.identity_links. NULL si no hay identidad.';

COMMENT ON COLUMN ops.v_cabinet_funnel_status.origin_tag IS 
'Origen del lead: cabinet, fleet_migration o unknown. Prioridad: cabinet > fleet_migration > unknown.';

COMMENT ON COLUMN ops.v_cabinet_funnel_status.funnel_status IS 
'Estado del driver en el funnel (mutuamente excluyente): registered_incomplete, registered_complete, connected_no_trips, reached_m1, reached_m5, reached_m25.';

COMMENT ON COLUMN ops.v_cabinet_funnel_status.connected_flag IS 
'Flag indicando si el driver se conectó (first_connection_date IS NOT NULL).';

COMMENT ON COLUMN ops.v_cabinet_funnel_status.connected_date IS 
'Primera fecha de conexión desde observational.v_conversion_metrics.first_connection_date.';

COMMENT ON COLUMN ops.v_cabinet_funnel_status.trips_total IS 
'Total de viajes acumulados (proxy: trips_30d desde v_conversion_metrics).';

COMMENT ON COLUMN ops.v_cabinet_funnel_status.highest_milestone IS 
'Milestone más alto alcanzado: 0 (ninguno), 1 (M1), 5 (M5), 25 (M25).';

COMMENT ON COLUMN ops.v_cabinet_funnel_status.m1_date IS 
'Fecha en que se alcanzó M1 (milestone determinístico). NULL si no se alcanzó.';

COMMENT ON COLUMN ops.v_cabinet_funnel_status.m5_date IS 
'Fecha en que se alcanzó M5 (milestone determinístico). NULL si no se alcanzó.';

COMMENT ON COLUMN ops.v_cabinet_funnel_status.m25_date IS 
'Fecha en que se alcanzó M25 (milestone determinístico). NULL si no se alcanzó.';

