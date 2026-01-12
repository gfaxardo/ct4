-- ============================================================================
-- DIAGNÓSTICO: Brecha de drivers "Sin scout" en cobranza Yango
-- ============================================================================
-- OBJETIVO: Identificar la causa raíz de drivers sin scout en /pagos/cobranza-yango
-- 
-- HIPÓTESIS A VALIDAR:
-- H1: El LEFT JOIN LATERAL requiere lead_date exacto, perdiendo matches
-- H2: Los drivers no tienen person_key (problema de identidad C0)
-- H3: La atribución scout está solo a nivel person_key pero no se propaga a driver_id
-- H4: El join a lead_ledger falla por falta de datos en observational.lead_ledger
-- H5: Hay múltiples lead_date para el mismo driver_id y el join toma el incorrecto
-- ============================================================================

-- ============================================================================
-- SANITY CHECK 1: Conteo base de drivers en v_cabinet_financial_14d
-- ============================================================================
SELECT 
    'SANITY_CHECK_1: Total drivers en v_cabinet_financial_14d' AS check_name,
    COUNT(*) AS total_drivers,
    COUNT(DISTINCT driver_id) AS unique_drivers,
    COUNT(DISTINCT lead_date) AS unique_lead_dates
FROM ops.v_cabinet_financial_14d;

-- ============================================================================
-- SANITY CHECK 2: Drivers con milestones pero sin scout (desde endpoint)
-- ============================================================================
WITH financial_data AS (
    SELECT 
        cf.driver_id,
        cf.lead_date,
        cf.reached_m1_14d,
        cf.reached_m5_14d,
        cf.reached_m25_14d,
        scout.scout_id,
        scout.is_scout_resolved
    FROM ops.v_cabinet_financial_14d cf
    LEFT JOIN LATERAL (
        SELECT DISTINCT ON (driver_id, lead_date)
            scout_id,
            scout_name,
            scout_quality_bucket,
            is_scout_resolved
        FROM ops.v_yango_collection_with_scout
        WHERE driver_id = cf.driver_id
            AND lead_date = cf.lead_date
            AND scout_id IS NOT NULL
        ORDER BY driver_id, lead_date, 
            CASE scout_quality_bucket
                WHEN 'SATISFACTORY_LEDGER' THEN 1
                WHEN 'EVENTS_ONLY' THEN 2
                WHEN 'SCOUTING_DAILY_ONLY' THEN 3
                ELSE 4
            END,
            milestone_value
        LIMIT 1
    ) scout ON true
)
SELECT 
    'SANITY_CHECK_2: Drivers con milestones pero sin scout' AS check_name,
    COUNT(*) FILTER (WHERE (reached_m1_14d OR reached_m5_14d OR reached_m25_14d) AND (scout_id IS NULL OR is_scout_resolved = false)) AS drivers_with_milestones_no_scout,
    COUNT(*) FILTER (WHERE (reached_m1_14d OR reached_m5_14d OR reached_m25_14d) AND scout_id IS NOT NULL) AS drivers_with_milestones_with_scout,
    COUNT(*) AS total_drivers_with_milestones
FROM financial_data
WHERE reached_m1_14d OR reached_m5_14d OR reached_m25_14d;

-- ============================================================================
-- HIPÓTESIS H1: Join requiere lead_date exacto
-- ============================================================================
-- Test 1: Join por driver_id SOLO (sin lead_date)
WITH drivers_in_financial AS (
    SELECT DISTINCT driver_id, lead_date
    FROM ops.v_cabinet_financial_14d
    LIMIT 100  -- Muestra representativa
),
match_by_driver_only AS (
    SELECT 
        df.driver_id,
        df.lead_date AS financial_lead_date,
        COUNT(DISTINCT ysc.scout_id) AS scout_count_driver_only
    FROM drivers_in_financial df
    LEFT JOIN ops.v_yango_collection_with_scout ysc
        ON ysc.driver_id = df.driver_id
        AND ysc.scout_id IS NOT NULL
    GROUP BY df.driver_id, df.lead_date
),
match_by_driver_and_date AS (
    SELECT 
        df.driver_id,
        df.lead_date AS financial_lead_date,
        COUNT(DISTINCT ysc.scout_id) AS scout_count_driver_and_date
    FROM drivers_in_financial df
    LEFT JOIN ops.v_yango_collection_with_scout ysc
        ON ysc.driver_id = df.driver_id
        AND ysc.lead_date = df.lead_date
        AND ysc.scout_id IS NOT NULL
    GROUP BY df.driver_id, df.lead_date
)
SELECT 
    'H1_TEST: Join driver_id SOLO vs driver_id+lead_date' AS check_name,
    COUNT(*) FILTER (WHERE mbd.scout_count_driver_only > 0 AND mbd.scout_count_driver_and_date = 0) AS drivers_with_scout_driver_only_but_not_with_date,
    COUNT(*) FILTER (WHERE mbd.scout_count_driver_only > 0) AS total_drivers_with_scout_by_driver,
    COUNT(*) FILTER (WHERE mbd.scout_count_driver_and_date > 0) AS total_drivers_with_scout_by_driver_and_date
FROM match_by_driver_only mbd
LEFT JOIN match_by_driver_and_date mbd2 
    ON mbd.driver_id = mbd2.driver_id 
    AND mbd.financial_lead_date = mbd2.financial_lead_date;

-- ============================================================================
-- HIPÓTESIS H2: Drivers sin person_key
-- ============================================================================
WITH drivers_person_key AS (
    SELECT DISTINCT
        cf.driver_id,
        cf.lead_date,
        -- Intentar obtener person_key desde v_yango_cabinet_claims_for_collection
        (SELECT DISTINCT person_key 
         FROM ops.v_yango_cabinet_claims_for_collection 
         WHERE driver_id = cf.driver_id 
         LIMIT 1) AS person_key
    FROM ops.v_cabinet_financial_14d cf
    WHERE (cf.reached_m1_14d OR cf.reached_m5_14d OR cf.reached_m25_14d)
)
SELECT 
    'H2_TEST: Drivers sin person_key' AS check_name,
    COUNT(*) AS total_drivers_with_milestones,
    COUNT(*) FILTER (WHERE person_key IS NULL) AS drivers_without_person_key,
    ROUND(COUNT(*) FILTER (WHERE person_key IS NULL)::NUMERIC / NULLIF(COUNT(*), 0) * 100, 2) AS pct_without_person_key
FROM drivers_person_key;

-- ============================================================================
-- HIPÓTESIS H3: Atribución scout a nivel person_key pero no a nivel driver_id
-- ============================================================================
WITH drivers_with_person_key AS (
    SELECT DISTINCT
        cf.driver_id,
        ycc.person_key
    FROM ops.v_cabinet_financial_14d cf
    INNER JOIN ops.v_yango_cabinet_claims_for_collection ycc
        ON ycc.driver_id = cf.driver_id
    WHERE (cf.reached_m1_14d OR cf.reached_m5_14d OR cf.reached_m25_14d)
        AND ycc.person_key IS NOT NULL
    LIMIT 100
),
scout_by_person_key AS (
    SELECT 
        dwpk.driver_id,
        dwpk.person_key,
        ll.attributed_scout_id AS scout_id_from_ledger
    FROM drivers_with_person_key dwpk
    LEFT JOIN observational.lead_ledger ll
        ON ll.person_key = dwpk.person_key
        AND ll.attributed_scout_id IS NOT NULL
),
scout_by_collection_view AS (
    SELECT DISTINCT
        dwpk.driver_id,
        dwpk.person_key,
        ysc.scout_id AS scout_id_from_collection_view
    FROM drivers_with_person_key dwpk
    LEFT JOIN ops.v_yango_collection_with_scout ysc
        ON ysc.driver_id = dwpk.driver_id
        AND ysc.scout_id IS NOT NULL
)
SELECT 
    'H3_TEST: Scout por person_key vs por collection_view' AS check_name,
    COUNT(*) FILTER (WHERE spk.scout_id_from_ledger IS NOT NULL AND scv.scout_id_from_collection_view IS NULL) AS has_scout_by_person_key_but_not_in_collection_view,
    COUNT(*) FILTER (WHERE spk.scout_id_from_ledger IS NOT NULL) AS total_with_scout_by_person_key,
    COUNT(*) FILTER (WHERE scv.scout_id_from_collection_view IS NOT NULL) AS total_with_scout_in_collection_view
FROM scout_by_person_key spk
LEFT JOIN scout_by_collection_view scv
    ON spk.driver_id = scv.driver_id
    AND spk.person_key = scv.person_key;

-- ============================================================================
-- HIPÓTESIS H4: Falta de datos en lead_ledger
-- ============================================================================
WITH drivers_in_claims AS (
    SELECT DISTINCT
        ycc.driver_id,
        ycc.person_key
    FROM ops.v_yango_cabinet_claims_for_collection ycc
    WHERE ycc.person_key IS NOT NULL
    LIMIT 100
)
SELECT 
    'H4_TEST: Cobertura de lead_ledger' AS check_name,
    COUNT(DISTINCT dic.person_key) AS total_person_keys_in_claims,
    COUNT(DISTINCT ll.person_key) FILTER (WHERE ll.attributed_scout_id IS NOT NULL) AS person_keys_with_scout_in_ledger,
    COUNT(DISTINCT dic.person_key) FILTER (WHERE NOT EXISTS (
        SELECT 1 FROM observational.lead_ledger ll2 
        WHERE ll2.person_key = dic.person_key
    )) AS person_keys_missing_in_ledger
FROM drivers_in_claims dic
LEFT JOIN observational.lead_ledger ll
    ON ll.person_key = dic.person_key
    AND ll.attributed_scout_id IS NOT NULL;

-- ============================================================================
-- HIPÓTESIS H5: Múltiples lead_date por driver_id
-- ============================================================================
SELECT 
    'H5_TEST: Múltiples lead_date por driver_id' AS check_name,
    COUNT(*) FILTER (WHERE lead_date_count > 1) AS drivers_with_multiple_lead_dates,
    COUNT(DISTINCT driver_id) AS total_drivers,
    MAX(lead_date_count) AS max_lead_dates_per_driver
FROM (
    SELECT 
        driver_id,
        COUNT(DISTINCT lead_date) AS lead_date_count
    FROM ops.v_cabinet_financial_14d
    GROUP BY driver_id
) driver_date_counts;

-- ============================================================================
-- RESUMEN: Diagnóstico completo
-- ============================================================================
SELECT 
    'RESUMEN_DIAGNOSTICO' AS summary_type,
    (SELECT COUNT(*) FROM ops.v_cabinet_financial_14d) AS total_drivers_in_financial,
    (SELECT COUNT(*) FROM ops.v_cabinet_financial_14d WHERE reached_m1_14d OR reached_m5_14d OR reached_m25_14d) AS drivers_with_milestones,
    (SELECT COUNT(DISTINCT person_key) FROM ops.v_yango_cabinet_claims_for_collection WHERE person_key IS NOT NULL) AS total_person_keys_in_claims,
    (SELECT COUNT(DISTINCT person_key) FROM observational.lead_ledger WHERE attributed_scout_id IS NOT NULL) AS person_keys_with_scout_in_ledger,
    (SELECT COUNT(DISTINCT driver_id) FROM ops.v_yango_collection_with_scout WHERE scout_id IS NOT NULL) AS drivers_with_scout_in_collection_view;
