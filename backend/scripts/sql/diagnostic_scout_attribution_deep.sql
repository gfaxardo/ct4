-- ============================================================================
-- DIAGNÓSTICO PROFUNDO: Verificar si el problema está en la vista o en los datos
-- ============================================================================

-- TEST 1: Verificar si v_yango_collection_with_scout tiene scouts
SELECT 
    'TEST_1: Cobertura en v_yango_collection_with_scout' AS test_name,
    COUNT(*) AS total_rows,
    COUNT(*) FILTER (WHERE scout_id IS NOT NULL) AS rows_with_scout,
    COUNT(*) FILTER (WHERE scout_id IS NULL) AS rows_without_scout,
    ROUND(COUNT(*) FILTER (WHERE scout_id IS NOT NULL)::NUMERIC / NULLIF(COUNT(*), 0) * 100, 2) AS pct_with_scout
FROM ops.v_yango_collection_with_scout;

-- TEST 2: Verificar si lead_ledger tiene scouts atribuidos
SELECT 
    'TEST_2: Cobertura en lead_ledger' AS test_name,
    COUNT(DISTINCT person_key) AS total_person_keys,
    COUNT(DISTINCT person_key) FILTER (WHERE attributed_scout_id IS NOT NULL) AS person_keys_with_scout,
    COUNT(DISTINCT person_key) FILTER (WHERE attributed_scout_id IS NULL) AS person_keys_without_scout,
    ROUND(COUNT(DISTINCT person_key) FILTER (WHERE attributed_scout_id IS NOT NULL)::NUMERIC / NULLIF(COUNT(DISTINCT person_key), 0) * 100, 2) AS pct_with_scout
FROM observational.lead_ledger;

-- TEST 3: Verificar si hay drivers en v_cabinet_financial_14d que tienen person_key pero sin scout
WITH drivers_with_person_key AS (
    SELECT DISTINCT
        cf.driver_id,
        ycc.person_key
    FROM ops.v_cabinet_financial_14d cf
    LEFT JOIN ops.v_yango_cabinet_claims_for_collection ycc
        ON ycc.driver_id = cf.driver_id
    WHERE (cf.reached_m1_14d OR cf.reached_m5_14d OR cf.reached_m25_14d)
        AND ycc.person_key IS NOT NULL
    LIMIT 200
),
scout_status AS (
    SELECT 
        dwpk.driver_id,
        dwpk.person_key,
        ll.attributed_scout_id AS scout_in_ledger,
        ysc.scout_id AS scout_in_collection_view
    FROM drivers_with_person_key dwpk
    LEFT JOIN observational.lead_ledger ll
        ON ll.person_key = dwpk.person_key
        AND ll.attributed_scout_id IS NOT NULL
    LEFT JOIN ops.v_yango_collection_with_scout ysc
        ON ysc.driver_id = dwpk.driver_id
        AND ysc.scout_id IS NOT NULL
)
SELECT 
    'TEST_3: Drivers con person_key y su scout status' AS test_name,
    COUNT(*) AS total_drivers_with_person_key,
    COUNT(*) FILTER (WHERE scout_in_ledger IS NOT NULL) AS drivers_with_scout_in_ledger,
    COUNT(*) FILTER (WHERE scout_in_collection_view IS NOT NULL) AS drivers_with_scout_in_collection_view,
    COUNT(*) FILTER (WHERE scout_in_ledger IS NOT NULL AND scout_in_collection_view IS NULL) AS drivers_with_scout_in_ledger_but_not_in_collection_view,
    COUNT(*) FILTER (WHERE scout_in_ledger IS NULL AND scout_in_collection_view IS NULL) AS drivers_without_scout_anywhere
FROM scout_status;

-- TEST 4: Verificar si el join en v_yango_collection_with_scout funciona correctamente
SELECT 
    'TEST_4: Join lead_ledger vs v_yango_cabinet_claims_for_collection' AS test_name,
    COUNT(DISTINCT ycc.driver_id) AS total_drivers_in_claims,
    COUNT(DISTINCT ycc.driver_id) FILTER (WHERE ll.attributed_scout_id IS NOT NULL) AS drivers_with_scout_via_join,
    COUNT(DISTINCT ycc.driver_id) FILTER (WHERE ll.attributed_scout_id IS NULL) AS drivers_without_scout_via_join
FROM ops.v_yango_cabinet_claims_for_collection ycc
LEFT JOIN observational.lead_ledger ll
    ON ll.person_key = ycc.person_key
    AND ll.attributed_scout_id IS NOT NULL
WHERE ycc.person_key IS NOT NULL;
