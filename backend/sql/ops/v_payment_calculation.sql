-- Vista de Cálculo de Pagos (Payment Calculation View)
-- Calcula elegibilidad y montos de pago para scouts y partners (Yango)
-- basándose en métricas de conversión y reglas de pago configurables.
--
-- Estructura: Una fila por (person_key, origin_tag, rule_id)
-- Permite múltiples filas por person_key cuando cumple múltiples reglas/hitos.

CREATE OR REPLACE VIEW ops.v_payment_calculation AS
WITH conversion_metrics_base AS (
    -- Base: Datos de conversión por lead
    -- EXCLUIR drivers en cuarentena activa (quarantined)
    SELECT 
        person_key,
        origin_tag,
        lead_date,
        scout_id,
        driver_id
    FROM observational.v_conversion_metrics
    WHERE driver_id IS NOT NULL
        AND driver_id NOT IN (
            SELECT driver_id 
            FROM canon.driver_orphan_quarantine 
            WHERE status = 'quarantined'
        )
),
all_payment_rules AS (
    -- Unión de reglas de scouts y partners con scope
    SELECT 
        id AS rule_id,
        'scout' AS rule_scope,
        origin_tag,
        window_days,
        milestone_trips,
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
        apr.rule_id,
        apr.rule_scope,
        apr.milestone_trips,
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
    -- Normalizar summary_daily con fecha convertida (similar a v_conversion_metrics)
    SELECT 
        driver_id,
        to_date(date_file, 'DD-MM-YYYY') AS prod_date,
        count_orders_completed
    FROM public.summary_daily
    WHERE date_file IS NOT NULL
        AND date_file ~ '^\d{2}-\d{2}-\d{4}$'  -- Validar formato DD-MM-YYYY
),
trips_from_lead_date AS (
    -- Calcular viajes acumulados desde lead_date (para todos los días, no solo dentro de ventana)
    SELECT 
        rwm.person_key,
        rwm.origin_tag,
        rwm.rule_id,
        rwm.rule_scope,
        rwm.lead_date,
        rwm.driver_id,
        rwm.milestone_trips,
        rwm.window_days,
        rwm.amount,
        rwm.currency,
        rwm.rule_valid_from,
        rwm.rule_valid_to,
        rwm.scout_id,
        sd.prod_date,
        sd.count_orders_completed,
        -- Viajes acumulados desde lead_date hasta prod_date (incluyendo todos los días)
        SUM(sd.count_orders_completed) OVER (
            PARTITION BY rwm.person_key, rwm.origin_tag, rwm.driver_id
            ORDER BY sd.prod_date
            ROWS UNBOUNDED PRECEDING
        ) AS cumulative_trips_from_lead
    FROM rules_with_metrics rwm
    INNER JOIN summary_daily_normalized sd
        ON sd.driver_id = rwm.driver_id
        AND sd.prod_date >= rwm.lead_date
        AND sd.count_orders_completed > 0  -- Solo días con viajes completados
),
trips_within_window AS (
    -- Filtrar solo días dentro de la ventana de la regla
    SELECT 
        person_key,
        origin_tag,
        rule_id,
        rule_scope,
        lead_date,
        driver_id,
        scout_id,
        milestone_trips,
        window_days,
        amount,
        currency,
        rule_valid_from,
        rule_valid_to,
        prod_date,
        count_orders_completed,
        cumulative_trips_from_lead
    FROM trips_from_lead_date
    WHERE prod_date < lead_date + (window_days || ' days')::INTERVAL
),
milestone_achievement AS (
    -- Encontrar la primera fecha donde se alcanza el milestone dentro de la ventana
    SELECT DISTINCT ON (person_key, origin_tag, rule_id)
        person_key,
        origin_tag,
        rule_id,
        rule_scope,
        lead_date,
        driver_id,
        scout_id,
        milestone_trips,
        window_days,
        amount,
        currency,
        rule_valid_from,
        rule_valid_to,
        prod_date AS achieved_date,
        cumulative_trips_from_lead AS achieved_trips_in_window
    FROM trips_within_window
    WHERE cumulative_trips_from_lead >= milestone_trips
    ORDER BY person_key, origin_tag, rule_id, prod_date ASC
),
all_rule_combinations AS (
    -- Asegurar que todas las combinaciones de reglas aparezcan, incluso si no se alcanzó el milestone
    SELECT 
        rwm.person_key,
        rwm.origin_tag,
        rwm.rule_id,
        rwm.rule_scope,
        rwm.lead_date,
        rwm.driver_id,
        rwm.scout_id,
        rwm.milestone_trips,
        rwm.window_days,
        rwm.amount,
        rwm.currency,
        rwm.rule_valid_from,
        rwm.rule_valid_to,
        ma.achieved_date,
        ma.achieved_trips_in_window
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
    arc.milestone_trips,
    arc.window_days,
    arc.currency,
    arc.amount,
    arc.rule_valid_from,
    arc.rule_valid_to,
    -- milestone_achieved: Si se alcanzó el milestone dentro de la ventana
    (arc.achieved_date IS NOT NULL) AS milestone_achieved,
    -- achieved_date: Fecha en que se alcanza el milestone (NULL si no se alcanza)
    arc.achieved_date,
    -- achieved_trips_in_window: Viajes acumulados en achieved_date dentro de la ventana
    COALESCE(arc.achieved_trips_in_window, 0) AS achieved_trips_in_window,
    -- is_payable: milestone_achieved AND lead_date dentro de vigencia de regla
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
        WHEN arc.rule_scope = 'scout' AND arc.origin_tag = 'cabinet' THEN 
            'cabinet_7d_' || arc.milestone_trips || 'trips'
        WHEN arc.rule_scope = 'scout' AND arc.origin_tag = 'fleet_migration' THEN 
            'migration_30d_' || arc.milestone_trips || 'trips'
        ELSE 
            arc.origin_tag || '_' || arc.window_days || 'd_' || arc.milestone_trips || 'trips'
    END AS payment_scheme
FROM all_rule_combinations arc
ORDER BY arc.person_key, arc.origin_tag, arc.rule_scope, arc.milestone_trips;

-- Comentarios en la vista y columnas principales
COMMENT ON VIEW ops.v_payment_calculation IS 
'Vista de cálculo de elegibilidad y montos de pago para scouts y partners (Yango).
Genera una fila por (person_key, origin_tag, rule_id), permitiendo múltiples filas cuando una persona cumple múltiples reglas/hitos.

La vista:
- Calcula viajes dinámicamente desde summary_daily usando window_days de cada regla
- Determina si se alcanzó el milestone dentro de la ventana especificada
- Calcula fechas de logro (achieved_date) y pagabilidad (payable_date)
- Filtra reglas según vigencia (valid_from/valid_to) y estado activo

USO:
- Consultar todas las reglas aplicables: SELECT * FROM ops.v_payment_calculation WHERE person_key = ?
- Consultar solo pagos elegibles: SELECT * FROM ops.v_payment_calculation WHERE is_payable = true
- Agrupar por scout o partner para sumar montos totales
';

COMMENT ON COLUMN ops.v_payment_calculation.person_key IS 'Identificador canónico de la persona desde v_conversion_metrics';
COMMENT ON COLUMN ops.v_payment_calculation.origin_tag IS 'Origen del lead: cabinet o fleet_migration';
COMMENT ON COLUMN ops.v_payment_calculation.scout_id IS 'ID del scout (solo si origin_tag=fleet_migration, NULL para cabinet)';
COMMENT ON COLUMN ops.v_payment_calculation.rule_scope IS 'Alcance de la regla: partner (Yango→Yego) o scout (Yego→Scouts)';
COMMENT ON COLUMN ops.v_payment_calculation.milestone_achieved IS 'Indica si se alcanzó el milestone dentro de la ventana especificada';
COMMENT ON COLUMN ops.v_payment_calculation.achieved_date IS 'Fecha en que se alcanza el milestone dentro de la ventana (NULL si no se alcanza)';
COMMENT ON COLUMN ops.v_payment_calculation.achieved_trips_in_window IS 'Viajes acumulados en achieved_date dentro de la ventana';
COMMENT ON COLUMN ops.v_payment_calculation.is_payable IS 'Indica si el pago es elegible (milestone_achieved AND dentro de vigencia de regla)';
COMMENT ON COLUMN ops.v_payment_calculation.payable_date IS 'Fecha calculada para realizar el pago (achieved_date + offset: 14 días partner, 7 días scout cabinet, 30 días migration)';
COMMENT ON COLUMN ops.v_payment_calculation.payment_scheme IS 'String descriptivo del esquema de pago (ej: cabinet_7d_5trips, yango_14d_25trips)';

