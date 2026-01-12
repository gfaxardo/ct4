-- ============================================================================
-- VISTA: ops.v_scout_attribution_raw (CANÓNICA MULTIFUENTE)
-- ============================================================================
-- Propósito: UNION ALL estandarizando campos de todas las fuentes de scout_id
-- Prioridad: 1=lead_ledger, 2=lead_events, 3=module_ct_migrations, 4=scouting_daily, 5=cabinet_payments
-- Ejecución: Idempotente (DROP + CREATE)
-- ============================================================================

DROP VIEW IF EXISTS ops.v_scout_attribution_raw CASCADE;
CREATE VIEW ops.v_scout_attribution_raw AS
-- PRIORITY 1: observational.lead_ledger.attributed_scout_id (source-of-truth)
SELECT DISTINCT
    ll.person_key,
    NULL::TEXT AS driver_id,
    NULL::TEXT AS driver_license,
    NULL::TEXT AS driver_phone,
    ll.attributed_scout_id AS scout_id,
    NULL::TEXT AS origin_tag,
    NULL::TEXT AS acquisition_method,
    'observational.lead_ledger' AS source_table,
    ll.person_key::TEXT AS source_pk,
    COALESCE(ll.updated_at, NOW())::DATE AS attribution_date,
    COALESCE(ll.updated_at, NOW()) AS created_at,
    1 AS priority
FROM observational.lead_ledger ll
WHERE ll.attributed_scout_id IS NOT NULL

UNION ALL

-- PRIORITY 2: observational.lead_events.scout_id o payload_json->>'scout_id'
SELECT DISTINCT
    le.person_key,
    NULL::TEXT AS driver_id,
    NULL::TEXT AS driver_license,
    NULL::TEXT AS driver_phone,
    COALESCE(le.scout_id, (le.payload_json->>'scout_id')::INTEGER) AS scout_id,
    NULL::TEXT AS origin_tag,
    NULL::TEXT AS acquisition_method,
    le.source_table,
    le.source_pk,
    COALESCE(le.event_date::DATE, le.created_at::DATE) AS attribution_date,
    le.created_at,
    2 AS priority
FROM observational.lead_events le
WHERE le.person_key IS NOT NULL
    AND (le.scout_id IS NOT NULL OR (le.payload_json IS NOT NULL AND le.payload_json->>'scout_id' IS NOT NULL))
    -- Excluir si ya está en lead_ledger (prioridad 1)
    AND NOT EXISTS (
        SELECT 1 FROM observational.lead_ledger ll
        WHERE ll.person_key = le.person_key
            AND ll.attributed_scout_id IS NOT NULL
    )

UNION ALL

-- PRIORITY 3: public.module_ct_migrations.scout_id (si existe)
SELECT DISTINCT
    COALESCE(il.person_key, NULL) AS person_key,
    m.driver_id::TEXT AS driver_id,
    NULL::TEXT AS driver_license,
    NULL::TEXT AS driver_phone,
    m.scout_id,
    'migration' AS origin_tag,
    NULL::TEXT AS acquisition_method,
    'public.module_ct_migrations' AS source_table,
    m.id::TEXT AS source_pk,
    COALESCE(m.hire_date, m.created_at::DATE) AS attribution_date,
    m.created_at,
    3 AS priority
FROM public.module_ct_migrations m
LEFT JOIN canon.identity_links il 
    ON il.source_table = 'module_ct_migrations'
    AND il.source_pk = m.id::TEXT
WHERE EXISTS (
    SELECT 1 FROM information_schema.tables 
    WHERE table_schema = 'public' AND table_name = 'module_ct_migrations'
)
    AND m.scout_id IS NOT NULL
    -- Excluir si ya está en prioridades 1 o 2
    AND NOT EXISTS (
        SELECT 1 FROM observational.lead_ledger ll
        WHERE ll.person_key = COALESCE(il.person_key, NULL::UUID)
            AND ll.attributed_scout_id IS NOT NULL
    )
    AND (il.person_key IS NULL OR NOT EXISTS (
        SELECT 1 FROM observational.lead_events le
        WHERE le.person_key = il.person_key
            AND (le.scout_id IS NOT NULL OR (le.payload_json IS NOT NULL AND le.payload_json->>'scout_id' IS NOT NULL))
    ))

UNION ALL

-- PRIORITY 4: public.module_ct_scouting_daily.scout_id
SELECT DISTINCT
    COALESCE(il.person_key, NULL) AS person_key,
    NULL::TEXT AS driver_id,
    sd.driver_license,
    sd.driver_phone,
    sd.scout_id,
    'scout_registration' AS origin_tag,
    sd.acquisition_method,
    'public.module_ct_scouting_daily' AS source_table,
    sd.id::TEXT AS source_pk,
    COALESCE(sd.registration_date, sd.created_at::DATE) AS attribution_date,
    sd.created_at,
    4 AS priority
FROM public.module_ct_scouting_daily sd
LEFT JOIN canon.identity_links il 
    ON il.source_table = 'module_ct_scouting_daily'
    AND il.source_pk = sd.id::TEXT
WHERE EXISTS (
    SELECT 1 FROM information_schema.tables 
    WHERE table_schema = 'public' AND table_name = 'module_ct_scouting_daily'
)
    AND sd.scout_id IS NOT NULL
    -- Excluir si ya está en prioridades 1, 2 o 3
    AND NOT EXISTS (
        SELECT 1 FROM observational.lead_ledger ll
        WHERE ll.person_key = COALESCE(il.person_key, NULL::UUID)
            AND ll.attributed_scout_id IS NOT NULL
    )
    AND (il.person_key IS NULL OR NOT EXISTS (
        SELECT 1 FROM observational.lead_events le
        WHERE le.person_key = il.person_key
            AND (le.scout_id IS NOT NULL OR (le.payload_json IS NOT NULL AND le.payload_json->>'scout_id' IS NOT NULL))
    ))
    AND (il.person_key IS NULL OR NOT EXISTS (
        SELECT 1 FROM public.module_ct_migrations m2
        JOIN canon.identity_links il2 ON il2.source_table = 'module_ct_migrations' AND il2.source_pk = m2.id::TEXT
        WHERE il2.person_key = il.person_key
            AND m2.scout_id IS NOT NULL
    ))

UNION ALL

-- PRIORITY 5: public.module_ct_cabinet_payments.scout_id
SELECT DISTINCT
    cp.person_key,
    cp.driver_id::TEXT AS driver_id,
    NULL::TEXT AS driver_license,
    NULL::TEXT AS driver_phone,
    cp.scout_id,
    'cabinet_payment' AS origin_tag,
    NULL::TEXT AS acquisition_method,
    'public.module_ct_cabinet_payments' AS source_table,
    cp.id::TEXT AS source_pk,
    COALESCE(cp.date, cp.created_at::DATE) AS attribution_date,
    cp.created_at,
    5 AS priority
FROM public.module_ct_cabinet_payments cp
WHERE EXISTS (
    SELECT 1 FROM information_schema.tables 
    WHERE table_schema = 'public' AND table_name = 'module_ct_cabinet_payments'
)
    AND cp.scout_id IS NOT NULL
    -- Excluir si ya está en prioridades 1-4 (por person_key o driver_id)
    AND (cp.person_key IS NULL OR NOT EXISTS (
        SELECT 1 FROM observational.lead_ledger ll
        WHERE ll.person_key = cp.person_key
            AND ll.attributed_scout_id IS NOT NULL
    ))
    AND (cp.person_key IS NULL OR NOT EXISTS (
        SELECT 1 FROM observational.lead_events le
        WHERE le.person_key = cp.person_key
            AND (le.scout_id IS NOT NULL OR (le.payload_json IS NOT NULL AND le.payload_json->>'scout_id' IS NOT NULL))
    ))
    AND (cp.person_key IS NULL OR NOT EXISTS (
        SELECT 1 FROM public.module_ct_migrations m3
        JOIN canon.identity_links il3 ON il3.source_table = 'module_ct_migrations' AND il3.source_pk = m3.id::TEXT
        WHERE il3.person_key = cp.person_key
            AND m3.scout_id IS NOT NULL
    ))
    AND (cp.person_key IS NULL OR NOT EXISTS (
        SELECT 1 FROM public.module_ct_scouting_daily sd3
        JOIN canon.identity_links il3 ON il3.source_table = 'module_ct_scouting_daily' AND il3.source_pk = sd3.id::TEXT
        WHERE il3.person_key = cp.person_key
            AND sd3.scout_id IS NOT NULL
    ))
    -- También por driver_id si person_key es NULL
    AND (cp.driver_id IS NULL OR NOT EXISTS (
        SELECT 1 FROM public.module_ct_migrations m4
        WHERE m4.driver_id = cp.driver_id
            AND m4.scout_id IS NOT NULL
    ));

COMMENT ON VIEW ops.v_scout_attribution_raw IS 
'Vista RAW de atribución scout desde todas las fuentes. UNION ALL estandarizando campos: person_key, driver_id, driver_license, driver_phone, scout_id, origin_tag, source_table, source_pk, attribution_date, priority. Prioridad: 1=lead_ledger, 2=lead_events, 3=migrations, 4=scouting_daily, 5=cabinet_payments.';

COMMENT ON COLUMN ops.v_scout_attribution_raw.priority IS 
'Prioridad de la fuente: 1=lead_ledger (source-of-truth), 2=lead_events, 3=module_ct_migrations, 4=scouting_daily, 5=cabinet_payments.';
