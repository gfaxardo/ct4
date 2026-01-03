-- ============================================================================
-- SCRIPT DE DEPLOYMENT: Driver Matrix Views
-- ============================================================================
-- PROPÓSITO:
-- Crea (o reemplaza) TODAS las vistas necesarias para ops.v_payments_driver_matrix_cabinet
-- en el orden correcto de dependencias.
--
-- ORDEN DE EJECUCIÓN:
-- 1. ops.v_payment_calculation (vista canónica C2 - fuente core)
-- 2. ops.v_claims_payment_status_cabinet (usa v_payment_calculation, NO vistas UI)
-- 3. ops.v_yango_cabinet_claims_for_collection
-- 4. ops.v_yango_payments_claims_cabinet_14d
-- 5. ops.v_payments_driver_matrix_cabinet
--
-- VALIDACIONES:
-- - Verifica existencia de objetos base antes de crear vistas
-- - Falla con mensaje claro si falta algún objeto base
-- - Valida existencia final de todas las vistas creadas
-- ============================================================================

-- ============================================================================
-- SECCIÓN 1: VALIDACIÓN DE OBJETOS BASE
-- ============================================================================
-- Verificar que existen las tablas/vistas base necesarias antes de continuar

DO $$
DECLARE
    missing_objects TEXT[] := ARRAY[]::TEXT[];
BEGIN
    -- Verificar tablas/vistas base
    IF NOT EXISTS (SELECT 1 FROM information_schema.tables WHERE table_schema = 'ops' AND table_name = 'scout_payment_rules') THEN
        missing_objects := array_append(missing_objects, 'ops.scout_payment_rules');
    END IF;
    
    IF NOT EXISTS (SELECT 1 FROM information_schema.tables WHERE table_schema = 'ops' AND table_name = 'partner_payment_rules') THEN
        missing_objects := array_append(missing_objects, 'ops.partner_payment_rules');
    END IF;
    
    IF NOT EXISTS (SELECT 1 FROM information_schema.tables WHERE table_schema = 'public' AND table_name = 'drivers') THEN
        missing_objects := array_append(missing_objects, 'public.drivers');
    END IF;
    
    IF NOT EXISTS (SELECT 1 FROM information_schema.tables WHERE table_schema = 'public' AND table_name = 'summary_daily') THEN
        missing_objects := array_append(missing_objects, 'public.summary_daily');
    END IF;
    
    IF NOT EXISTS (SELECT 1 FROM information_schema.views WHERE table_schema = 'observational' AND table_name = 'v_conversion_metrics') THEN
        missing_objects := array_append(missing_objects, 'observational.v_conversion_metrics');
    END IF;
    
    -- NO verificar vistas UI/report (v_yango_receivable_payable_detail, v_partner_payments_report_ui)
    -- Driver Matrix usa solo vistas canónicas core
    
    IF NOT EXISTS (SELECT 1 FROM information_schema.views WHERE table_schema = 'ops' AND table_name = 'v_yango_payments_ledger_latest_enriched') THEN
        missing_objects := array_append(missing_objects, 'ops.v_yango_payments_ledger_latest_enriched');
    END IF;
    
    IF array_length(missing_objects, 1) > 0 THEN
        RAISE EXCEPTION 'ERROR: Faltan objetos base necesarios: %', array_to_string(missing_objects, ', ');
    END IF;
END $$;

-- ============================================================================
-- SECCIÓN 2: CREAR ops.v_payment_calculation
-- ============================================================================
-- Usar v_payment_calculation_updated si existe el SQL, sino usar v_payment_calculation
-- Por ahora usamos v_payment_calculation (versión base)
-- IMPORTANTE: DROP antes de CREATE para evitar error "cannot drop columns from view"

DROP VIEW IF EXISTS ops.v_payment_calculation CASCADE;

CREATE VIEW ops.v_payment_calculation AS
WITH conversion_metrics_base AS (
    -- Base: Datos de conversión por lead
    SELECT 
        person_key,
        origin_tag,
        lead_date,
        scout_id,
        driver_id
    FROM observational.v_conversion_metrics
    WHERE driver_id IS NOT NULL
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

COMMENT ON VIEW ops.v_payment_calculation IS 
'Vista de cálculo de elegibilidad y montos de pago para scouts y partners (Yango).
Genera una fila por (person_key, origin_tag, rule_id), permitiendo múltiples filas cuando una persona cumple múltiples reglas/hitos.';

-- ============================================================================
-- SECCIÓN 3: CREAR ops.v_claims_payment_status_cabinet
-- ============================================================================
-- IMPORTANTE: DROP antes de CREATE para evitar error "cannot drop columns from view"

DROP VIEW IF EXISTS ops.v_claims_payment_status_cabinet CASCADE;

CREATE VIEW ops.v_claims_payment_status_cabinet AS
WITH base_claims_raw AS (
    -- Fuente core: ops.v_payment_calculation (vista canónica C2)
    -- Filtra solo claims de Yango (partner) para cabinet con milestones 1, 5, 25
    SELECT 
        pc.driver_id,
        pc.person_key,
        pc.lead_date,
        pc.milestone_trips AS milestone_value,
        -- Aplicar reglas de negocio para expected_amount (milestone 1=25, 5=35, 25=100)
        -- NO usar amount de la vista, aplicar reglas directamente
        CASE 
            WHEN pc.milestone_trips = 1 THEN 25::numeric(12,2)
            WHEN pc.milestone_trips = 5 THEN 35::numeric(12,2)
            WHEN pc.milestone_trips = 25 THEN 100::numeric(12,2)
            ELSE NULL::numeric(12,2)
        END AS expected_amount
    FROM ops.v_payment_calculation pc
    WHERE pc.origin_tag = 'cabinet'
        AND pc.rule_scope = 'partner'  -- Solo Yango (partner), no scouts
        AND pc.milestone_trips IN (1, 5, 25)
        AND pc.milestone_achieved = true  -- Solo milestones alcanzados
        AND pc.driver_id IS NOT NULL
),
base_claims_dedup AS (
    -- Deduplicación: 1 fila por (driver_id + milestone_value), quedarse con lead_date más reciente
    SELECT DISTINCT ON (driver_id, milestone_value)
        driver_id,
        person_key,
        lead_date,
        milestone_value,
        expected_amount
    FROM base_claims_raw
    ORDER BY driver_id, milestone_value, lead_date DESC
),
base_claims AS (
    SELECT 
        driver_id,
        person_key,
        lead_date,
        milestone_value,
        expected_amount
    FROM base_claims_dedup
)
SELECT 
    c.driver_id,
    c.person_key,
    c.milestone_value,
    c.lead_date,
    c.lead_date + INTERVAL '14 days' AS due_date,
    c.expected_amount,
    
    -- Aging: cálculo de días vencidos y bucket
    GREATEST(0, CURRENT_DATE - (c.lead_date + INTERVAL '14 days')::date) AS days_overdue,
    CASE 
        WHEN (c.lead_date + INTERVAL '14 days')::date >= CURRENT_DATE THEN '0_not_due'
        WHEN (CURRENT_DATE - (c.lead_date + INTERVAL '14 days')::date) BETWEEN 1 AND 7 THEN '1_1_7'
        WHEN (CURRENT_DATE - (c.lead_date + INTERVAL '14 days')::date) BETWEEN 8 AND 14 THEN '2_8_14'
        WHEN (CURRENT_DATE - (c.lead_date + INTERVAL '14 days')::date) BETWEEN 15 AND 30 THEN '3_15_30'
        WHEN (CURRENT_DATE - (c.lead_date + INTERVAL '14 days')::date) BETWEEN 31 AND 60 THEN '4_31_60'
        ELSE '5_60_plus'
    END AS bucket_overdue,
    
    -- Pago exacto: driver_id + milestone matching (usando LATERAL JOIN)
    (p_exact.payment_key IS NOT NULL) AS paid_flag,
    p_exact.pay_date AS paid_date,
    p_exact.payment_key,
    p_exact.identity_status AS payment_identity_status,
    p_exact.match_rule AS payment_match_rule,
    p_exact.match_confidence AS payment_match_confidence,
    
    -- payment_status: ENUM TEXT (mantener compatibilidad)
    CASE 
        WHEN p_exact.payment_key IS NOT NULL THEN 'paid'
        ELSE 'not_paid'
    END AS payment_status,
    
    -- payment_reason: TEXT (mantener compatibilidad, pero será reemplazado por reason_code)
    CASE 
        WHEN p_exact.payment_key IS NOT NULL THEN 'payment_found'
        ELSE 'no_payment_found'
    END AS payment_reason,
    
    -- reason_code: diagnóstico detallado con prioridad
    -- Optimizado: usar LEFT JOIN LATERAL en lugar de subconsultas EXISTS costosas
    CASE 
        WHEN p_exact.payment_key IS NOT NULL THEN 'paid'
        WHEN c.driver_id IS NULL THEN 'missing_driver_id'
        WHEN c.milestone_value IS NULL THEN 'missing_milestone'
        WHEN p_other_milestone.payment_key IS NOT NULL THEN 'payment_found_other_milestone'
        WHEN p_person_key.payment_key IS NOT NULL THEN 'payment_found_person_key_only'
        ELSE 'no_payment_found'
    END AS reason_code,
    
    -- action_priority: prioridad operativa para cobranza
    CASE 
        WHEN p_exact.payment_key IS NOT NULL THEN 'P0_confirmed_paid'
        WHEN (c.lead_date + INTERVAL '14 days')::date >= CURRENT_DATE THEN 'P2_not_due'
        WHEN (CURRENT_DATE - (c.lead_date + INTERVAL '14 days')::date) BETWEEN 8 AND 14 THEN 'P1_watch'
        WHEN (CURRENT_DATE - (c.lead_date + INTERVAL '14 days')::date) >= 15 THEN 'P0_collect_now'
        ELSE 'P2_not_due'
    END AS action_priority

FROM base_claims c
LEFT JOIN LATERAL (
    -- Pago exacto: driver_id + milestone matching
    SELECT 
        payment_key,
        pay_date,
        identity_status,
        match_rule,
        match_confidence
    FROM ops.v_yango_payments_ledger_latest_enriched
    WHERE driver_id_final = c.driver_id
        AND milestone_value = c.milestone_value
        AND is_paid = true
    ORDER BY pay_date DESC, payment_key DESC
    LIMIT 1
) p_exact ON true
-- Optimización: solo ejecutar estos JOINs cuando no hay pago exacto
LEFT JOIN LATERAL (
    -- ¿Existe pago para este driver pero otro milestone?
    SELECT payment_key
    FROM ops.v_yango_payments_ledger_latest_enriched p
    WHERE p.driver_id_final = c.driver_id
        AND p.milestone_value != c.milestone_value
        AND p.is_paid = true
    LIMIT 1
) p_other_milestone ON p_exact.payment_key IS NULL 
    AND c.driver_id IS NOT NULL
    AND c.milestone_value IS NOT NULL
LEFT JOIN LATERAL (
    -- ¿Existe pago para este milestone pero solo por person_key?
    SELECT payment_key
    FROM ops.v_yango_payments_ledger_latest_enriched p
    WHERE p.milestone_value = c.milestone_value
        AND p.is_paid = true
        AND p.person_key_final = c.person_key
        AND (p.driver_id_final IS NULL OR p.driver_id_final != c.driver_id)
    LIMIT 1
) p_person_key ON p_exact.payment_key IS NULL 
    AND p_other_milestone.payment_key IS NULL
    AND c.person_key IS NOT NULL
    AND c.driver_id IS NOT NULL
    AND c.milestone_value IS NOT NULL;

COMMENT ON VIEW ops.v_claims_payment_status_cabinet IS 
'Vista orientada a cobranza que responde: "Para cada conductor que entró por cabinet y alcanzó un milestone, ¿nos pagaron o no, cuándo vence, qué tan vencido está, y por qué no pagaron si no pagaron?". Devuelve exactamente 1 fila por claim (driver_id + milestone).';

-- ============================================================================
-- SECCIÓN 4: CREAR ops.v_yango_cabinet_claims_for_collection
-- ============================================================================
-- IMPORTANTE: DROP antes de CREATE para evitar error "cannot drop columns from view"

DROP VIEW IF EXISTS ops.v_yango_cabinet_claims_for_collection CASCADE;

CREATE VIEW ops.v_yango_cabinet_claims_for_collection AS
SELECT 
    -- Campos de identificación
    c.driver_id,
    c.person_key,
    d.full_name AS driver_name,
    c.milestone_value,
    c.lead_date,
    
    -- Campo de monto (no recalcular, usar de vista base)
    c.expected_amount,
    
    -- Campos derivados Yango
    c.lead_date + INTERVAL '14 days' AS yango_due_date,
    GREATEST(0, CURRENT_DATE - (c.lead_date + INTERVAL '14 days')::date) AS days_overdue_yango,
    CASE 
        WHEN (c.lead_date + INTERVAL '14 days')::date >= CURRENT_DATE THEN '0_not_due'
        WHEN (CURRENT_DATE - (c.lead_date + INTERVAL '14 days')::date) BETWEEN 1 AND 7 THEN '1_1_7'
        WHEN (CURRENT_DATE - (c.lead_date + INTERVAL '14 days')::date) BETWEEN 8 AND 14 THEN '2_8_14'
        WHEN (CURRENT_DATE - (c.lead_date + INTERVAL '14 days')::date) BETWEEN 15 AND 30 THEN '3_15_30'
        ELSE '4_30_plus'
    END AS overdue_bucket_yango,
    
    -- Campo canónico de estado
    CASE
        WHEN c.paid_flag = true THEN 'PAID'
        WHEN c.reason_code = 'payment_found_other_milestone' THEN 'PAID_MISAPPLIED'
        ELSE 'UNPAID'
    END AS yango_payment_status,
    
    -- Campos de evidencia
    c.payment_key,
    c.paid_date AS pay_date,
    c.reason_code,
    c.payment_match_rule AS match_rule,
    c.payment_match_confidence AS match_confidence,
    
    -- Campos de identidad enriquecida (Opción B: diagnóstico de misapplied)
    c.payment_identity_status AS identity_status,
    
    -- suggested_driver_id: driver_id sugerido desde ledger enriched cuando hay misapplied
    -- Optimizado con LEFT JOIN LATERAL para evitar subconsultas correlacionadas costosas
    COALESCE(
        p_other_milestone.driver_id_final,
        p_person_key.driver_id_final
    ) AS suggested_driver_id,
    
    -- is_reconcilable_enriched: flag para identificar claims reconciliables
    -- Regla: identity_status IN ('confirmed','enriched') AND match_confidence >= 0.85
    -- Interpretación: 'high' >= 0.85, 'medium' con 'name_unique' >= 0.85
    CASE
        WHEN c.payment_identity_status IN ('confirmed', 'enriched') 
            AND (
                (c.payment_match_confidence = 'high') OR
                (c.payment_match_confidence = 'medium' AND c.payment_match_rule = 'name_unique')
            )
        THEN true
        ELSE false
    END AS is_reconcilable_enriched

FROM ops.v_claims_payment_status_cabinet c
LEFT JOIN public.drivers d ON d.driver_id = c.driver_id
-- Optimización: usar LEFT JOIN LATERAL solo cuando reason_code lo requiera
-- Esto evita ejecutar subconsultas costosas para todas las filas
LEFT JOIN LATERAL (
    -- Para reason_code = 'payment_found_other_milestone': buscar driver_id del pago encontrado
    SELECT driver_id_final
    FROM ops.v_yango_payments_ledger_latest_enriched p
    WHERE p.driver_id_final = c.driver_id
        AND p.milestone_value != c.milestone_value
        AND p.is_paid = true
    ORDER BY p.pay_date DESC
    LIMIT 1
) p_other_milestone ON c.reason_code = 'payment_found_other_milestone'
LEFT JOIN LATERAL (
    -- Para reason_code = 'payment_found_person_key_only': buscar driver_id_final del pago por person_key
    SELECT driver_id_final
    FROM ops.v_yango_payments_ledger_latest_enriched p
    WHERE p.person_key_final = c.person_key
        AND p.milestone_value = c.milestone_value
        AND p.is_paid = true
        AND p.driver_id_final IS NOT NULL
    ORDER BY p.pay_date DESC
    LIMIT 1
) p_person_key ON c.reason_code = 'payment_found_person_key_only' 
    AND c.person_key IS NOT NULL;

COMMENT ON VIEW ops.v_yango_cabinet_claims_for_collection IS 
'Vista FINAL y cobrable para Yango Cabinet. Indica sin interpretación qué Yango debe pagar (UNPAID), qué ya pagó (PAID) y qué pagó mal (PAID_MISAPPLIED). Basada en ops.v_claims_payment_status_cabinet.';

-- ============================================================================
-- SECCIÓN 5: CREAR ops.v_yango_payments_claims_cabinet_14d
-- ============================================================================
-- IMPORTANTE: DROP antes de CREATE para evitar error "cannot drop columns from view"

DROP VIEW IF EXISTS ops.v_yango_payments_claims_cabinet_14d CASCADE;

CREATE VIEW ops.v_yango_payments_claims_cabinet_14d AS
-- Performance: filter pushdown before joins for UI stability
-- Apply date filter early to reduce data volume before expensive LEFT JOINs
WITH base_claims AS (
    -- Fuente core: ops.v_payment_calculation (vista canónica C2)
    -- Filtra solo claims de Yango (partner) para cabinet con milestones 1, 5, 25
    SELECT 
        pc.driver_id,
        pc.person_key,
        pc.lead_date,
        date_trunc('week', pc.payable_date)::date AS pay_week_start_monday,
        pc.milestone_trips AS milestone_value,
        -- Aplicar reglas de negocio para expected_amount (milestone 1=25, 5=35, 25=100)
        CASE 
            WHEN pc.milestone_trips = 1 THEN 25::numeric(12,2)
            WHEN pc.milestone_trips = 5 THEN 35::numeric(12,2)
            WHEN pc.milestone_trips = 25 THEN 100::numeric(12,2)
            ELSE NULL::numeric(12,2)
        END AS expected_amount,
        pc.currency
    FROM ops.v_payment_calculation pc
    WHERE pc.origin_tag = 'cabinet'
        AND pc.rule_scope = 'partner'  -- Solo Yango (partner), no scouts
        AND pc.milestone_trips IN (1, 5, 25)
        AND pc.milestone_achieved = true  -- Solo milestones alcanzados
        AND pc.driver_id IS NOT NULL
        AND pc.payable_date IS NOT NULL
        -- Performance: filter by date BEFORE expensive JOINs to reduce data volume
        -- Default filter: last 1 week (7 days) from start of current week (very aggressive for UI stability)
        AND date_trunc('week', pc.payable_date)::date >= (date_trunc('week', current_date)::date - interval '7 days')::date
),
-- Usar ledger enriquecido para matching
-- Performance: filter ledger by pay_date BEFORE expensive JOINs to reduce scan volume
ledger_enriched AS (
    SELECT 
        driver_id_final AS driver_id,
        person_key_original AS person_key,
        payment_key,
        pay_date,
        is_paid,
        milestone_value,
        match_rule,
        match_confidence,
        identity_status,
        identity_enriched
    FROM ops.v_yango_payments_ledger_latest_enriched
    WHERE pay_date >= (date_trunc('week', current_date)::date - interval '7 days')::date
        -- Only include paid records for matching (reduces volume significantly)
        AND is_paid = true
)
SELECT 
    e.driver_id,
    e.person_key,
    e.lead_date,
    e.pay_week_start_monday,
    e.milestone_value,
    e.expected_amount,
    e.currency,
    e.lead_date + INTERVAL '14 days' AS due_date,
    CASE 
        WHEN CURRENT_DATE <= (e.lead_date + INTERVAL '14 days') THEN 'active'
        ELSE 'expired'
    END AS window_status,
    -- Campos de paid_confirmed (identity_status='confirmed')
    p_confirmed.payment_key AS paid_payment_key_confirmed,
    p_confirmed.pay_date AS paid_date_confirmed,
    COALESCE(p_confirmed.is_paid, false) AS is_paid_confirmed,
    -- Campos de paid_enriched (identity_status='enriched')
    p_enriched.payment_key AS paid_payment_key_enriched,
    p_enriched.pay_date AS paid_date_enriched,
    COALESCE(p_enriched.is_paid, false) AS is_paid_enriched,
    -- Campos de compatibilidad (usar confirmed primero, luego enriched para visibilidad)
    COALESCE(p_confirmed.payment_key, p_enriched.payment_key) AS paid_payment_key,
    COALESCE(p_confirmed.pay_date, p_enriched.pay_date) AS paid_date,
    COALESCE(p_confirmed.is_paid, p_enriched.is_paid, false) AS paid_is_paid,
    -- Alias de compatibilidad: is_paid = paid_is_paid (para queries legacy)
    COALESCE(p_confirmed.is_paid, p_enriched.is_paid, false) AS is_paid,
    -- is_paid_effective: solo confirmed cuenta como paid real
    COALESCE(p_confirmed.is_paid, false) AS is_paid_effective,
    -- match_method
    CASE 
        WHEN e.driver_id IS NOT NULL AND p_confirmed.payment_key IS NOT NULL THEN 'driver_id'
        WHEN e.driver_id IS NULL AND e.person_key IS NOT NULL AND p_confirmed.payment_key IS NOT NULL THEN 'person_key'
        WHEN e.driver_id IS NOT NULL AND p_enriched.payment_key IS NOT NULL THEN 'driver_id_enriched'
        WHEN e.driver_id IS NULL AND e.person_key IS NOT NULL AND p_enriched.payment_key IS NOT NULL THEN 'person_key_enriched'
        ELSE 'none'
    END AS match_method,
    -- paid_status: separar confirmed vs enriched
    CASE 
        WHEN p_confirmed.is_paid = true THEN 'paid_confirmed'
        WHEN p_enriched.is_paid = true THEN 'paid_enriched'
        WHEN CURRENT_DATE <= (e.lead_date + INTERVAL '14 days') THEN 'pending_active'
        ELSE 'pending_expired'
    END AS paid_status,
    -- Campos de identidad desde ledger (usar confirmed primero, luego enriched)
    COALESCE(p_confirmed.identity_status, p_enriched.identity_status) AS identity_status,
    COALESCE(p_confirmed.match_rule, p_enriched.match_rule) AS match_rule,
    COALESCE(p_confirmed.match_confidence, p_enriched.match_confidence) AS match_confidence
FROM base_claims e
LEFT JOIN ledger_enriched p_confirmed
    ON (
        (e.driver_id IS NOT NULL AND p_confirmed.driver_id = e.driver_id)
        OR (e.driver_id IS NULL AND e.person_key IS NOT NULL AND p_confirmed.person_key = e.person_key AND p_confirmed.driver_id IS NULL)
    )
    AND p_confirmed.milestone_value = e.milestone_value
    AND p_confirmed.identity_status = 'confirmed'
    AND p_confirmed.is_paid = true
LEFT JOIN ledger_enriched p_enriched
    ON (
        (e.driver_id IS NOT NULL AND p_enriched.driver_id = e.driver_id)
        OR (e.driver_id IS NULL AND e.person_key IS NOT NULL AND p_enriched.person_key = e.person_key AND p_enriched.driver_id IS NULL)
    )
    AND p_enriched.milestone_value = e.milestone_value
    AND p_enriched.identity_status = 'enriched'
    AND p_enriched.is_paid = true;

COMMENT ON VIEW ops.v_yango_payments_claims_cabinet_14d IS 
'Vista de claims de pagos Yango Cabinet (ventana 14 días). Separa paid_confirmed (identity_status=confirmed desde upstream) vs paid_enriched (identity_status=enriched por matching por nombre).';

-- ============================================================================
-- SECCIÓN 6: CREAR ops.v_payments_driver_matrix_cabinet
-- ============================================================================
-- IMPORTANTE: DROP antes de CREATE para evitar error "cannot drop columns from view"

DROP VIEW IF EXISTS ops.v_payments_driver_matrix_cabinet CASCADE;

CREATE VIEW ops.v_payments_driver_matrix_cabinet AS
WITH base_claims AS (
    -- Base: claims por driver y milestone desde v_claims_payment_status_cabinet
    SELECT 
        c.driver_id,
        c.person_key,
        c.lead_date,
        c.milestone_value,
        c.expected_amount,
        c.paid_flag,
        c.paid_date,
        c.days_overdue,
        c.payment_status,
        c.reason_code
    FROM ops.v_claims_payment_status_cabinet c
    WHERE c.milestone_value IN (1, 5, 25)
),
-- Enriquecer con yango_payment_status desde v_yango_cabinet_claims_for_collection
yango_status AS (
    SELECT 
        y.driver_id,
        y.milestone_value,
        y.yango_payment_status,
        y.driver_name,
        y.lead_date
    FROM ops.v_yango_cabinet_claims_for_collection y
    WHERE y.milestone_value IN (1, 5, 25)
),
-- Enriquecer con window_status desde v_yango_payments_claims_cabinet_14d
-- Mapear 'active' a 'in_window' para cumplir con requerimiento
window_status_data AS (
    SELECT 
        w.driver_id,
        w.milestone_value,
        CASE 
            WHEN w.window_status = 'active' THEN 'in_window'
            WHEN w.window_status = 'expired' THEN 'expired'
            ELSE w.window_status
        END AS window_status,
        w.lead_date
    FROM ops.v_yango_payments_claims_cabinet_14d w
    WHERE w.milestone_value IN (1, 5, 25)
),
-- Obtener origin_tag y connected_date
-- Usa v_payment_calculation como fuente principal (más común)
origin_and_connected_data AS (
    SELECT DISTINCT ON (driver_id, person_key)
        pc.driver_id,
        pc.person_key,
        pc.origin_tag,
        -- first_connection_date puede venir de v_conversion_metrics si está disponible
        NULL::date AS connected_date,  -- TODO: Obtener desde v_conversion_metrics si es necesario
        pc.lead_date
    FROM ops.v_payment_calculation pc
    WHERE pc.origin_tag IN ('cabinet', 'fleet_migration')
        AND pc.driver_id IS NOT NULL
    ORDER BY pc.driver_id, pc.person_key, pc.lead_date DESC
),
-- Obtener driver_name desde public.drivers
driver_info AS (
    SELECT 
        d.driver_id,
        d.full_name AS driver_name
    FROM public.drivers d
),
-- Agregar por driver_id pivotando milestones
driver_milestones AS (
    SELECT 
        bc.driver_id,
        (array_agg(bc.person_key ORDER BY bc.lead_date DESC NULLS LAST))[1] AS person_key,
        -- Información base del driver
        MAX(di.driver_name) AS driver_name,
        MIN(bc.lead_date) AS lead_date,  -- Primera lead_date entre todos los milestones
        MAX(ocd.origin_tag) AS origin_tag,
        -- connected_flag y connected_date
        -- TODO: Implementar cuando exista fuente confiable de first_connection_date
        -- Por ahora, usar NULL ya que connected_date viene NULL desde origin_and_connected_data
        false AS connected_flag,
        NULL::date AS connected_date,
        -- week_start: lunes de la semana de lead_date
        DATE_TRUNC('week', MIN(bc.lead_date))::date AS week_start,
        -- Milestone M1 (milestone_value = 1)
        BOOL_OR(bc.milestone_value = 1) AS m1_achieved_flag,
        MAX(CASE WHEN bc.milestone_value = 1 THEN bc.lead_date END) AS m1_achieved_date,
        MAX(CASE WHEN bc.milestone_value = 1 THEN bc.expected_amount END) AS m1_expected_amount_yango,
        MAX(CASE WHEN bc.milestone_value = 1 THEN ys.yango_payment_status END) AS m1_yango_payment_status,
        MAX(CASE WHEN bc.milestone_value = 1 THEN ws.window_status END) AS m1_window_status,
        MAX(CASE WHEN bc.milestone_value = 1 THEN bc.days_overdue END) AS m1_overdue_days,
        -- Milestone M5 (milestone_value = 5)
        BOOL_OR(bc.milestone_value = 5) AS m5_achieved_flag,
        MAX(CASE WHEN bc.milestone_value = 5 THEN bc.lead_date END) AS m5_achieved_date,
        MAX(CASE WHEN bc.milestone_value = 5 THEN bc.expected_amount END) AS m5_expected_amount_yango,
        MAX(CASE WHEN bc.milestone_value = 5 THEN ys.yango_payment_status END) AS m5_yango_payment_status,
        MAX(CASE WHEN bc.milestone_value = 5 THEN ws.window_status END) AS m5_window_status,
        MAX(CASE WHEN bc.milestone_value = 5 THEN bc.days_overdue END) AS m5_overdue_days,
        -- Milestone M25 (milestone_value = 25)
        BOOL_OR(bc.milestone_value = 25) AS m25_achieved_flag,
        MAX(CASE WHEN bc.milestone_value = 25 THEN bc.lead_date END) AS m25_achieved_date,
        MAX(CASE WHEN bc.milestone_value = 25 THEN bc.expected_amount END) AS m25_expected_amount_yango,
        MAX(CASE WHEN bc.milestone_value = 25 THEN ys.yango_payment_status END) AS m25_yango_payment_status,
        MAX(CASE WHEN bc.milestone_value = 25 THEN ws.window_status END) AS m25_window_status,
        MAX(CASE WHEN bc.milestone_value = 25 THEN bc.days_overdue END) AS m25_overdue_days,
        -- TODO: Scout - dejar NULLs por ahora
        -- scout_due_flag, scout_paid_flag, scout_amount
        NULL::boolean AS scout_due_flag,
        NULL::boolean AS scout_paid_flag,
        NULL::numeric(12,2) AS scout_amount
    FROM base_claims bc
    LEFT JOIN yango_status ys 
        ON ys.driver_id = bc.driver_id 
        AND ys.milestone_value = bc.milestone_value
    LEFT JOIN window_status_data ws 
        ON ws.driver_id = bc.driver_id 
        AND ws.milestone_value = bc.milestone_value
    LEFT JOIN origin_and_connected_data ocd 
        ON ocd.driver_id = bc.driver_id
        AND (ocd.person_key = bc.person_key OR (ocd.person_key IS NULL AND bc.person_key IS NULL))
    LEFT JOIN driver_info di 
        ON di.driver_id = bc.driver_id
    GROUP BY bc.driver_id
)
SELECT 
    driver_id,
    person_key,
    driver_name,
    lead_date,
    week_start,
    origin_tag,
    connected_flag,
    connected_date,
    -- Milestone M1
    m1_achieved_flag,
    m1_achieved_date,
    m1_expected_amount_yango,
    m1_yango_payment_status,
    m1_window_status,
    m1_overdue_days,
    -- Milestone M5
    m5_achieved_flag,
    m5_achieved_date,
    m5_expected_amount_yango,
    m5_yango_payment_status,
    m5_window_status,
    m5_overdue_days,
    -- Milestone M25
    m25_achieved_flag,
    m25_achieved_date,
    m25_expected_amount_yango,
    m25_yango_payment_status,
    m25_window_status,
    m25_overdue_days,
    -- TODO: Scout - campos NULLs por ahora
    scout_due_flag,
    scout_paid_flag,
    scout_amount
FROM driver_milestones;

COMMENT ON VIEW ops.v_payments_driver_matrix_cabinet IS 
'Vista de PRESENTACIÓN (no recalcula reglas) que muestra 1 fila por driver con columnas por milestones M1/M5/M25 y estados Yango/Scout. Diseñada para visualización en dashboards y reportes operativos. Grano: driver_id (y person_key si aplica).';

-- ============================================================================
-- SECCIÓN 7: VALIDACIÓN FINAL
-- ============================================================================
-- Verificar que todas las vistas se crearon correctamente

DO $$
DECLARE
    missing_views TEXT[] := ARRAY[]::TEXT[];
    view_count INTEGER;
BEGIN
    -- Verificar existencia de las 5 vistas críticas (solo vistas canónicas, NO vistas UI)
    IF NOT EXISTS (SELECT 1 FROM information_schema.views WHERE table_schema = 'ops' AND table_name = 'v_payment_calculation') THEN
        missing_views := array_append(missing_views, 'ops.v_payment_calculation');
    END IF;
    
    IF NOT EXISTS (SELECT 1 FROM information_schema.views WHERE table_schema = 'ops' AND table_name = 'v_claims_payment_status_cabinet') THEN
        missing_views := array_append(missing_views, 'ops.v_claims_payment_status_cabinet');
    END IF;
    
    IF NOT EXISTS (SELECT 1 FROM information_schema.views WHERE table_schema = 'ops' AND table_name = 'v_yango_cabinet_claims_for_collection') THEN
        missing_views := array_append(missing_views, 'ops.v_yango_cabinet_claims_for_collection');
    END IF;
    
    IF NOT EXISTS (SELECT 1 FROM information_schema.views WHERE table_schema = 'ops' AND table_name = 'v_yango_payments_claims_cabinet_14d') THEN
        missing_views := array_append(missing_views, 'ops.v_yango_payments_claims_cabinet_14d');
    END IF;
    
    IF NOT EXISTS (SELECT 1 FROM information_schema.views WHERE table_schema = 'ops' AND table_name = 'v_payments_driver_matrix_cabinet') THEN
        missing_views := array_append(missing_views, 'ops.v_payments_driver_matrix_cabinet');
    END IF;
    
    IF array_length(missing_views, 1) > 0 THEN
        RAISE EXCEPTION 'ERROR: No se pudieron crear las siguientes vistas: %', array_to_string(missing_views, ', ');
    END IF;
    
    -- Verificar que la vista final es accesible (SELECT COUNT)
    BEGIN
        EXECUTE 'SELECT COUNT(*) FROM ops.v_payments_driver_matrix_cabinet' INTO view_count;
        RAISE NOTICE '✅ Deployment exitoso: Todas las vistas creadas correctamente.';
        RAISE NOTICE '✅ Vista final accesible: ops.v_payments_driver_matrix_cabinet tiene % filas.', view_count;
    EXCEPTION WHEN OTHERS THEN
        RAISE EXCEPTION 'ERROR: La vista ops.v_payments_driver_matrix_cabinet existe pero no es accesible: %', SQLERRM;
    END;
END $$;

-- ============================================================================
-- FIN DEL SCRIPT
-- ============================================================================
-- Si llegaste aquí sin errores, todas las vistas fueron creadas exitosamente.
-- Ejecuta el script de verificación: 00_deploy_driver_matrix_verify.sql
-- ============================================================================

