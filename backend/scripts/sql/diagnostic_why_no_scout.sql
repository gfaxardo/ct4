-- ============================================================================
-- DIAGNÓSTICO: ¿Por qué hay tantos drivers sin scout?
-- ============================================================================

-- TEST 1: ¿Cuántos drivers tienen person_key en v_yango_cabinet_claims_for_collection?
SELECT 
    'TEST_1: Drivers con/sin person_key en claims' AS test_name,
    COUNT(DISTINCT driver_id) AS total_drivers,
    COUNT(DISTINCT driver_id) FILTER (WHERE person_key IS NOT NULL) AS drivers_with_person_key,
    COUNT(DISTINCT driver_id) FILTER (WHERE person_key IS NULL) AS drivers_without_person_key,
    ROUND(COUNT(DISTINCT driver_id) FILTER (WHERE person_key IS NULL)::NUMERIC / NULLIF(COUNT(DISTINCT driver_id), 0) * 100, 2) AS pct_without_person_key
FROM ops.v_yango_cabinet_claims_for_collection;

-- TEST 2: De los drivers con person_key, ¿cuántos tienen scout en lead_ledger?
WITH drivers_with_person_key AS (
    SELECT DISTINCT driver_id, person_key
    FROM ops.v_yango_cabinet_claims_for_collection
    WHERE person_key IS NOT NULL
)
SELECT 
    'TEST_2: Drivers con person_key vs scout en lead_ledger' AS test_name,
    COUNT(DISTINCT dwpk.driver_id) AS total_drivers_with_person_key,
    COUNT(DISTINCT dwpk.driver_id) FILTER (WHERE ll.attributed_scout_id IS NOT NULL) AS drivers_with_scout_in_ledger,
    COUNT(DISTINCT dwpk.driver_id) FILTER (WHERE ll.attributed_scout_id IS NULL) AS drivers_without_scout_in_ledger,
    ROUND(COUNT(DISTINCT dwpk.driver_id) FILTER (WHERE ll.attributed_scout_id IS NULL)::NUMERIC / NULLIF(COUNT(DISTINCT dwpk.driver_id), 0) * 100, 2) AS pct_without_scout_in_ledger
FROM drivers_with_person_key dwpk
LEFT JOIN observational.lead_ledger ll
    ON ll.person_key = dwpk.person_key;

-- TEST 3: ¿Cuántos drivers en v_yango_collection_with_scout tienen scout?
SELECT 
    'TEST_3: Cobertura de scout en v_yango_collection_with_scout' AS test_name,
    COUNT(DISTINCT driver_id) AS total_drivers,
    COUNT(DISTINCT driver_id) FILTER (WHERE scout_id IS NOT NULL) AS drivers_with_scout,
    COUNT(DISTINCT driver_id) FILTER (WHERE scout_id IS NULL) AS drivers_without_scout,
    ROUND(COUNT(DISTINCT driver_id) FILTER (WHERE scout_id IS NULL)::NUMERIC / NULLIF(COUNT(DISTINCT driver_id), 0) * 100, 2) AS pct_without_scout
FROM ops.v_yango_collection_with_scout;

-- TEST 4: Comparar drivers en v_cabinet_financial_14d vs v_yango_collection_with_scout
SELECT 
    'TEST_4: Comparación entre financial y collection_with_scout' AS test_name,
    (SELECT COUNT(DISTINCT driver_id) FROM ops.v_cabinet_financial_14d) AS drivers_in_financial,
    (SELECT COUNT(DISTINCT driver_id) FROM ops.v_yango_collection_with_scout) AS drivers_in_collection_with_scout,
    (SELECT COUNT(DISTINCT driver_id) FROM ops.v_yango_collection_with_scout WHERE scout_id IS NOT NULL) AS drivers_with_scout_in_collection_view;

-- TEST 5: Drivers con milestones pero sin scout - muestra de casos
SELECT 
    'TEST_5: Muestra de drivers con milestones pero sin scout' AS test_name,
    cf.driver_id,
    cf.lead_date,
    cf.reached_m1_14d,
    cf.reached_m5_14d,
    cf.reached_m25_14d,
    ycc.person_key,
    ll.attributed_scout_id AS scout_in_ledger,
    ysc.scout_id AS scout_in_collection_view
FROM ops.v_cabinet_financial_14d cf
LEFT JOIN ops.v_yango_cabinet_claims_for_collection ycc
    ON ycc.driver_id = cf.driver_id
LEFT JOIN observational.lead_ledger ll
    ON ll.person_key = ycc.person_key
LEFT JOIN ops.v_yango_collection_with_scout ysc
    ON ysc.driver_id = cf.driver_id
    AND ysc.scout_id IS NOT NULL
WHERE (cf.reached_m1_14d OR cf.reached_m5_14d OR cf.reached_m25_14d)
    AND ysc.scout_id IS NULL
LIMIT 10;
