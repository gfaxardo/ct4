-- Vista de análisis de brechas de identidad para leads Cabinet
-- Identifica leads sin person_key, sin origin, o con actividad sin identidad
-- Grano: 1 fila por lead_id

CREATE OR REPLACE VIEW ops.v_identity_gap_analysis AS
WITH cabinet_leads AS (
    SELECT 
        COALESCE(cl.external_id, cl.id::TEXT) AS lead_id,
        cl.id AS lead_id_raw,
        cl.lead_created_at::DATE AS lead_date,
        cl.park_phone,
        cl.first_name,
        cl.middle_name,
        cl.last_name,
        cl.asset_plate_number
    FROM public.module_ct_cabinet_leads cl
),
identity_links AS (
    SELECT 
        il.source_pk AS lead_id,
        il.person_key,
        il.linked_at
    FROM canon.identity_links il
    WHERE il.source_table = 'module_ct_cabinet_leads'
),
identity_origins AS (
    SELECT 
        io.person_key,
        io.origin_tag,
        io.origin_source_id
    FROM canon.identity_origin io
    WHERE io.origin_tag = 'cabinet_lead'
),
driver_activity AS (
    SELECT 
        il.person_key,
        COUNT(DISTINCT sd.driver_id) AS driver_count,
        SUM(sd.count_orders_completed) AS total_trips
    FROM public.summary_daily sd
    JOIN canon.identity_links il ON il.source_pk = sd.driver_id 
        AND il.source_table = 'drivers'
    GROUP BY il.person_key
),
trips_14d AS (
    SELECT 
        il_link.person_key,
        cl.lead_id,
        cl.lead_date,
        SUM(sd.count_orders_completed) AS trips_14d
    FROM cabinet_leads cl
    LEFT JOIN identity_links il_link ON il_link.lead_id = cl.lead_id
    LEFT JOIN canon.identity_links il_driver ON il_driver.person_key = il_link.person_key 
        AND il_driver.source_table = 'drivers'
    LEFT JOIN public.summary_daily sd ON sd.driver_id = il_driver.source_pk
        AND (
            CASE 
                WHEN sd.date_file ~ '^\d{4}-\d{2}-\d{2}$' THEN sd.date_file::DATE
                WHEN sd.date_file ~ '^\d{2}-\d{2}-\d{4}$' THEN TO_DATE(sd.date_file, 'DD-MM-YYYY')
                ELSE NULL
            END
        ) IS NOT NULL
        AND (
            CASE 
                WHEN sd.date_file ~ '^\d{4}-\d{2}-\d{2}$' THEN sd.date_file::DATE
                WHEN sd.date_file ~ '^\d{2}-\d{2}-\d{4}$' THEN TO_DATE(sd.date_file, 'DD-MM-YYYY')
                ELSE NULL
            END
        ) BETWEEN cl.lead_date AND cl.lead_date + INTERVAL '14 days'
    GROUP BY il_link.person_key, cl.lead_id, cl.lead_date
)
SELECT 
    cl.lead_id,
    cl.lead_date,
    il.person_key,
    CASE WHEN il.person_key IS NOT NULL THEN TRUE ELSE FALSE END AS has_identity,
    CASE WHEN io.person_key IS NOT NULL THEN TRUE ELSE FALSE END AS has_origin,
    CASE WHEN da.person_key IS NOT NULL THEN TRUE ELSE FALSE END AS has_driver_activity,
    COALESCE(t14.trips_14d, 0) AS trips_14d,
    CASE 
        WHEN il.person_key IS NULL THEN 'no_identity'
        WHEN il.person_key IS NOT NULL AND io.person_key IS NULL THEN 'no_origin'
        WHEN il.person_key IS NULL AND da.person_key IS NOT NULL THEN 'activity_without_identity'
        WHEN il.person_key IS NULL AND da.person_key IS NULL THEN 'no_activity'
        ELSE 'resolved'
    END AS gap_reason,
    CURRENT_DATE - cl.lead_date AS gap_age_days,
    CASE 
        WHEN (il.person_key IS NULL AND da.person_key IS NOT NULL) OR 
             (il.person_key IS NULL AND CURRENT_DATE - cl.lead_date >= 7) THEN 'high'
        WHEN il.person_key IS NULL AND CURRENT_DATE - cl.lead_date >= 2 THEN 'medium'
        ELSE 'low'
    END AS risk_level
FROM cabinet_leads cl
LEFT JOIN identity_links il ON il.lead_id = cl.lead_id
LEFT JOIN identity_origins io ON io.person_key = il.person_key 
    AND io.origin_source_id = cl.lead_id
LEFT JOIN driver_activity da ON da.person_key = il.person_key
LEFT JOIN trips_14d t14 ON t14.lead_id = cl.lead_id AND t14.person_key = il.person_key;

COMMENT ON VIEW ops.v_identity_gap_analysis IS 
'Análisis de brechas de identidad para leads Cabinet. Identifica leads sin person_key, sin origin, o con actividad sin identidad. Grano: 1 fila por lead_id.';

COMMENT ON COLUMN ops.v_identity_gap_analysis.lead_id IS 
'ID del lead (external_id o id)';

COMMENT ON COLUMN ops.v_identity_gap_analysis.lead_date IS 
'Fecha de creación del lead';

COMMENT ON COLUMN ops.v_identity_gap_analysis.person_key IS 
'Person key asignado (NULL si no tiene identidad)';

COMMENT ON COLUMN ops.v_identity_gap_analysis.has_identity IS 
'TRUE si tiene person_key asignado';

COMMENT ON COLUMN ops.v_identity_gap_analysis.has_origin IS 
'TRUE si tiene registro en canon.identity_origin';

COMMENT ON COLUMN ops.v_identity_gap_analysis.has_driver_activity IS 
'TRUE si tiene actividad en summary_daily';

COMMENT ON COLUMN ops.v_identity_gap_analysis.trips_14d IS 
'Total de viajes completados dentro de la ventana de 14 días desde lead_date';

COMMENT ON COLUMN ops.v_identity_gap_analysis.gap_reason IS 
'Razón de la brecha: no_identity, no_origin, activity_without_identity, no_activity, resolved';

COMMENT ON COLUMN ops.v_identity_gap_analysis.gap_age_days IS 
'Días desde lead_date hasta hoy';

COMMENT ON COLUMN ops.v_identity_gap_analysis.risk_level IS 
'Nivel de riesgo: high (activity sin identity o >=7 días sin resolver), medium (>=2 días sin resolver), low (<2 días)';
