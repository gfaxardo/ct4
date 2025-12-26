-- Vista de Cálculo de Pagos (Payment Calculation View) - ACTUALIZADA
-- Calcula elegibilidad y montos de pago para scouts y partners (Yango)
-- Soporta milestones de tipo 'trips' y 'connection' para reglas scout
--
-- Estructura: Una fila por (person_key, origin_tag, rule_id)
-- Permite múltiples filas por person_key cuando cumple múltiples reglas/hitos.

-- Drop la vista existente antes de recrearla (necesario cuando cambia el orden/columnas)
DROP VIEW IF EXISTS ops.v_payment_calculation CASCADE;

CREATE VIEW ops.v_payment_calculation AS
WITH conversion_metrics_base AS (
    -- Base: Datos de conversión por lead (enriquecido con first_connection_date)
    SELECT 
        cm.person_key,
        cm.origin_tag,
        cm.lead_date,
        cm.scout_id,
        cm.driver_id,
        cm.first_connection_date
    FROM observational.v_conversion_metrics cm
    WHERE cm.driver_id IS NOT NULL
),
all_payment_rules AS (
    -- Unión de reglas de scouts (con milestone_type/milestone_value) y partners (legacy milestone_trips)
    SELECT 
        id AS rule_id,
        'scout' AS rule_scope,
        origin_tag,
        window_days,
        milestone_trips,  -- Legacy, mantener compatibilidad
        COALESCE(milestone_type, 'trips') AS milestone_type,
        COALESCE(milestone_value, milestone_trips) AS milestone_value,
        amount,
        currency,
        valid_from AS rule_valid_from,
        valid_to AS rule_valid_to,
        is_active
    FROM ops.scout_payment_rules
    WHERE is_active = true
    
    UNION ALL
    
    SELECT 
        id AS rule_id,
        'partner' AS rule_scope,
        origin_tag,
        window_days,
        milestone_trips,
        'trips' AS milestone_type,  -- Partner siempre es trips
        milestone_trips AS milestone_value,
        amount,
        currency,
        valid_from AS rule_valid_from,
        valid_to AS rule_valid_to,
        is_active
    FROM ops.partner_payment_rules
    WHERE is_active = true
),
rules_with_metrics AS (
    -- Combinar métricas con reglas aplicables
    SELECT 
        cmb.person_key,
        cmb.origin_tag,
        cmb.lead_date,
        cmb.scout_id,
        cmb.driver_id,
        cmb.first_connection_date,
        apr.rule_id,
        apr.rule_scope,
        apr.milestone_trips,  -- Legacy
        apr.milestone_type,
        apr.milestone_value,
        apr.window_days,
        apr.amount,
        apr.currency,
        apr.rule_valid_from,
        apr.rule_valid_to
    FROM conversion_metrics_base cmb
    INNER JOIN all_payment_rules apr
        ON apr.origin_tag = cmb.origin_tag
        -- Filtrar solo reglas que aplican según vigencia
        AND cmb.lead_date >= apr.rule_valid_from
        AND (apr.rule_valid_to IS NULL OR cmb.lead_date <= apr.rule_valid_to)
),
summary_daily_normalized AS (
    -- Normalizar summary_daily con fecha convertida
    SELECT 
        driver_id,
        to_date(date_file, 'DD-MM-YYYY') AS prod_date,
        count_orders_completed
    FROM public.summary_daily
    WHERE date_file IS NOT NULL
        AND date_file ~ '^\d{2}-\d{2}-\d{4}$'
),
trips_from_lead_date AS (
    -- Calcular viajes acumulados desde lead_date (solo para reglas tipo 'trips')
    SELECT 
        rwm.person_key,
        rwm.origin_tag,
        rwm.rule_id,
        rwm.rule_scope,
        rwm.lead_date,
        rwm.driver_id,
        rwm.milestone_trips,
        rwm.milestone_type,
        rwm.milestone_value,
        rwm.window_days,
        rwm.amount,
        rwm.currency,
        rwm.rule_valid_from,
        rwm.rule_valid_to,
        rwm.scout_id,
        rwm.first_connection_date,
        sd.prod_date,
        sd.count_orders_completed,
        SUM(sd.count_orders_completed) OVER (
            PARTITION BY rwm.person_key, rwm.origin_tag, rwm.driver_id
            ORDER BY sd.prod_date
            ROWS UNBOUNDED PRECEDING
        ) AS cumulative_trips_from_lead
    FROM rules_with_metrics rwm
    INNER JOIN summary_daily_normalized sd
        ON sd.driver_id = rwm.driver_id
        AND sd.prod_date >= rwm.lead_date
        AND sd.count_orders_completed > 0
    WHERE rwm.milestone_type = 'trips'
),
trips_within_window AS (
    -- Filtrar solo días dentro de la ventana (para milestones tipo trips)
    SELECT 
        person_key,
        origin_tag,
        rule_id,
        rule_scope,
        lead_date,
        driver_id,
        scout_id,
        milestone_trips,
        milestone_type,
        milestone_value,
        window_days,
        amount,
        currency,
        rule_valid_from,
        rule_valid_to,
        first_connection_date,
        prod_date,
        count_orders_completed,
        cumulative_trips_from_lead
    FROM trips_from_lead_date
    WHERE prod_date < lead_date + (window_days || ' days')::INTERVAL
),
milestone_achievement_trips AS (
    -- Logro de milestone tipo 'trips': encontrar primera fecha donde se alcanza el milestone
    SELECT DISTINCT ON (person_key, origin_tag, rule_id)
        person_key,
        origin_tag,
        rule_id,
        rule_scope,
        lead_date,
        driver_id,
        scout_id,
        milestone_trips,
        milestone_type,
        milestone_value,
        window_days,
        amount,
        currency,
        rule_valid_from,
        rule_valid_to,
        first_connection_date,
        prod_date AS achieved_date,
        cumulative_trips_from_lead AS achieved_trips_in_window
    FROM trips_within_window
    WHERE cumulative_trips_from_lead >= milestone_value
    ORDER BY person_key, origin_tag, rule_id, prod_date ASC
),
trips_for_connection AS (
    -- Calcular trips_in_window para reglas connection (aunque el milestone sea connection)
    SELECT 
        rwm.person_key,
        rwm.origin_tag,
        rwm.rule_id,
        rwm.driver_id,
        rwm.lead_date,
        rwm.window_days,
        COALESCE(SUM(sd.count_orders_completed), 0) AS trips_in_window
    FROM rules_with_metrics rwm
    LEFT JOIN summary_daily_normalized sd
        ON sd.driver_id = rwm.driver_id
        AND sd.prod_date >= rwm.lead_date
        AND sd.prod_date < rwm.lead_date + (rwm.window_days || ' days')::INTERVAL
        AND sd.count_orders_completed > 0
    WHERE rwm.milestone_type = 'connection'
    GROUP BY rwm.person_key, rwm.origin_tag, rwm.rule_id, rwm.driver_id, rwm.lead_date, rwm.window_days
),
milestone_achievement_connection AS (
    -- Logro de milestone tipo 'connection': usar first_connection_date
    SELECT 
        rwm.person_key,
        rwm.origin_tag,
        rwm.rule_id,
        rwm.rule_scope,
        rwm.lead_date,
        rwm.driver_id,
        rwm.scout_id,
        rwm.milestone_trips,
        rwm.milestone_type,
        rwm.milestone_value,
        rwm.window_days,
        rwm.amount,
        rwm.currency,
        rwm.rule_valid_from,
        rwm.rule_valid_to,
        rwm.first_connection_date,
        rwm.first_connection_date AS achieved_date,
        COALESCE(tfc.trips_in_window, 0) AS achieved_trips_in_window
    FROM rules_with_metrics rwm
    LEFT JOIN trips_for_connection tfc
        ON tfc.person_key = rwm.person_key
        AND tfc.origin_tag = rwm.origin_tag
        AND tfc.rule_id = rwm.rule_id
    WHERE rwm.milestone_type = 'connection'
        AND rwm.first_connection_date IS NOT NULL
        AND rwm.first_connection_date <= rwm.lead_date + (rwm.window_days || ' days')::INTERVAL
),
milestone_achievement AS (
    -- Unificar logros de ambos tipos
    SELECT * FROM milestone_achievement_trips
    UNION ALL
    SELECT * FROM milestone_achievement_connection
),
all_rule_combinations AS (
    -- Asegurar que todas las combinaciones aparezcan, incluso si no se alcanzó el milestone
    SELECT 
        rwm.person_key,
        rwm.origin_tag,
        rwm.rule_id,
        rwm.rule_scope,
        rwm.lead_date,
        rwm.driver_id,
        rwm.scout_id,
        rwm.milestone_trips,
        rwm.milestone_type,
        rwm.milestone_value,
        rwm.window_days,
        rwm.amount,
        rwm.currency,
        rwm.rule_valid_from,
        rwm.rule_valid_to,
        rwm.first_connection_date,
        ma.achieved_date,
        COALESCE(ma.achieved_trips_in_window, 0) AS achieved_trips_in_window
    FROM rules_with_metrics rwm
    LEFT JOIN milestone_achievement ma
        ON ma.person_key = rwm.person_key
        AND ma.origin_tag = rwm.origin_tag
        AND ma.rule_id = rwm.rule_id
)
-- Selección final con todos los campos calculados
SELECT 
    arc.person_key,
    arc.origin_tag,
    arc.scout_id,
    arc.driver_id,
    arc.lead_date,
    arc.rule_id,
    arc.rule_scope,
    arc.milestone_trips,  -- Legacy, mantener compatibilidad
    arc.milestone_type,
    arc.milestone_value,
    arc.window_days,
    arc.currency,
    arc.amount,
    arc.rule_valid_from,
    arc.rule_valid_to,
    -- milestone_achieved: Si se alcanzó el milestone dentro de la ventana
    (arc.achieved_date IS NOT NULL) AS milestone_achieved,
    -- achieved_date: Fecha en que se alcanza el milestone
    arc.achieved_date,
    -- achieved_trips_in_window: Viajes acumulados en achieved_date (solo para trips)
    arc.achieved_trips_in_window,
    -- is_payable: milestone_achieved AND lead_date dentro de vigencia
    (arc.achieved_date IS NOT NULL 
        AND arc.lead_date >= arc.rule_valid_from 
        AND (arc.rule_valid_to IS NULL OR arc.lead_date <= arc.rule_valid_to)
    ) AS is_payable,
    -- payable_date: achieved_date + offset según tipo
    CASE 
        WHEN arc.achieved_date IS NOT NULL THEN
            CASE 
                WHEN arc.rule_scope = 'partner' THEN arc.achieved_date + INTERVAL '14 days'
                WHEN arc.rule_scope = 'scout' AND arc.origin_tag = 'cabinet' THEN arc.achieved_date + INTERVAL '7 days'
                WHEN arc.rule_scope = 'scout' AND arc.origin_tag = 'fleet_migration' THEN arc.achieved_date + INTERVAL '30 days'
                ELSE NULL
            END
        ELSE NULL
    END::DATE AS payable_date,
    -- payment_scheme: String descriptivo
    CASE 
        WHEN arc.rule_scope = 'partner' AND arc.origin_tag = 'cabinet' THEN 
            'yango_14d_' || arc.milestone_trips || 'trips'
        WHEN arc.rule_scope = 'scout' AND arc.origin_tag = 'cabinet' AND arc.milestone_type = 'trips' THEN 
            'cabinet_7d_' || arc.milestone_value || 'trips'
        WHEN arc.rule_scope = 'scout' AND arc.origin_tag = 'cabinet' AND arc.milestone_type = 'connection' THEN 
            'cabinet_7d_connection'
        WHEN arc.rule_scope = 'scout' AND arc.origin_tag = 'fleet_migration' AND arc.milestone_type = 'trips' THEN 
            'migration_30d_' || arc.milestone_value || 'trips'
        WHEN arc.rule_scope = 'scout' AND arc.origin_tag = 'fleet_migration' AND arc.milestone_type = 'connection' THEN 
            'migration_30d_connection'
        ELSE 
            arc.origin_tag || '_' || arc.window_days || 'd_' || 
            CASE WHEN arc.milestone_type = 'connection' THEN 'connection' ELSE arc.milestone_value::text || 'trips' END
    END AS payment_scheme
FROM all_rule_combinations arc
ORDER BY arc.person_key, arc.origin_tag, arc.rule_scope, arc.milestone_type, arc.milestone_value;

-- Comentarios actualizados
COMMENT ON VIEW ops.v_payment_calculation IS 
'Vista de cálculo de elegibilidad y montos de pago para scouts y partners.
Soporta milestones tipo trips y connection para reglas scout.
Genera una fila por (person_key, origin_tag, rule_id).';

COMMENT ON COLUMN ops.v_payment_calculation.milestone_type IS 'Tipo de milestone: trips o connection (solo scout)';
COMMENT ON COLUMN ops.v_payment_calculation.milestone_value IS 'Valor del milestone: número de viajes para trips, generalmente 1 para connection';

