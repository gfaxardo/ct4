-- ============================================================================
-- VISTA: ops.v_scout_attribution_raw
-- ============================================================================
-- Propósito: UNION ALL estandarizando campos de TODAS las fuentes de scout_id
-- Prioridad: 1=lead_ledger, 2=lead_events, 3=module_ct_migrations, 4=scouting_daily
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
    'observational.lead_ledger' AS source,
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
    le.source_table AS source,
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

-- PRIORITY 3: public.module_ct_migrations.scout_id
SELECT DISTINCT
    il.person_key,
    NULL::TEXT AS driver_id,
    NULL::TEXT AS driver_license,
    NULL::TEXT AS driver_phone,
    m.scout_id,
    'migration' AS origin_tag,
    NULL::TEXT AS acquisition_method,
    'public.module_ct_migrations' AS source,
    m.id::TEXT AS source_pk,
    COALESCE(m.created_at::DATE, il.snapshot_date::DATE) AS attribution_date,
    COALESCE(m.created_at, il.snapshot_date) AS created_at,
    3 AS priority
FROM public.module_ct_migrations m
INNER JOIN canon.identity_links il ON il.source_table = 'module_ct_migrations' 
    AND il.source_pk = m.id::TEXT
WHERE m.scout_id IS NOT NULL
    -- Excluir si ya está en lead_ledger o lead_events (prioridad 1 y 2)
    AND NOT EXISTS (
        SELECT 1 FROM observational.lead_ledger ll
        WHERE ll.person_key = il.person_key
            AND ll.attributed_scout_id IS NOT NULL
    )
    AND NOT EXISTS (
        SELECT 1 FROM observational.lead_events le
        WHERE le.person_key = il.person_key
            AND (le.scout_id IS NOT NULL OR (le.payload_json IS NOT NULL AND le.payload_json->>'scout_id' IS NOT NULL))
    )

UNION ALL

-- PRIORITY 4: public.module_ct_scouting_daily.scout_id
SELECT DISTINCT
    il.person_key,
    NULL::TEXT AS driver_id,
    sd.driver_license,
    sd.driver_phone,
    sd.scout_id,
    NULL::TEXT AS origin_tag,
    sd.acquisition_method,
    'public.module_ct_scouting_daily' AS source,
    sd.id::TEXT AS source_pk,
    COALESCE(sd.registration_date, il.snapshot_date::DATE) AS attribution_date,
    COALESCE(sd.created_at, il.snapshot_date) AS created_at,
    4 AS priority
FROM public.module_ct_scouting_daily sd
INNER JOIN canon.identity_links il ON il.source_table = 'module_ct_scouting_daily' 
    AND il.source_pk = sd.id::TEXT
WHERE sd.scout_id IS NOT NULL
    -- Excluir si ya está en fuentes de mayor prioridad (1, 2, 3)
    AND NOT EXISTS (
        SELECT 1 FROM observational.lead_ledger ll
        WHERE ll.person_key = il.person_key
            AND ll.attributed_scout_id IS NOT NULL
    )
    AND NOT EXISTS (
        SELECT 1 FROM observational.lead_events le
        WHERE le.person_key = il.person_key
            AND (le.scout_id IS NOT NULL OR (le.payload_json IS NOT NULL AND le.payload_json->>'scout_id' IS NOT NULL))
    )
    AND NOT EXISTS (
        SELECT 1 FROM public.module_ct_migrations m2
        INNER JOIN canon.identity_links il2 ON il2.source_table = 'module_ct_migrations' 
            AND il2.source_pk = m2.id::TEXT
        WHERE il2.person_key = il.person_key
            AND m2.scout_id IS NOT NULL
    );

COMMENT ON VIEW ops.v_scout_attribution_raw IS 
'UNION ALL de TODAS las fuentes de scout_id normalizadas. Prioridad: 1=lead_ledger, 2=lead_events, 3=migrations, 4=scouting_daily. Excluye duplicados por prioridad.';
