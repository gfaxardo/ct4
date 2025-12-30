-- ============================================================================
-- Backfill de Identidad en ops.yango_payment_status_ledger
-- ============================================================================
-- Enriquece driver_id y person_key SIN reingestar pagos.
-- Umbral score = 0.85. Evita falsos positivos: si hay ambigüedad, NO asigna.
-- ============================================================================

-- ============================================================================
-- A1) Funciones de Normalización
-- ============================================================================

-- 1) ops.normalize_person_name(text) -> text
-- lower, unaccent, replace puntuación por espacio, colapsar espacios y trim
CREATE OR REPLACE FUNCTION ops.normalize_person_name(name_text TEXT)
RETURNS TEXT
LANGUAGE plpgsql
IMMUTABLE
AS $$
DECLARE
    normalized TEXT;
BEGIN
    IF name_text IS NULL OR TRIM(name_text) = '' THEN
        RETURN NULL;
    END IF;
    
    normalized := name_text;
    
    -- Convertir a minúsculas
    normalized := LOWER(normalized);
    
    -- Unaccent (quitar tildes)
    normalized := REGEXP_REPLACE(normalized, '[àáâãäå]', 'a', 'g');
    normalized := REGEXP_REPLACE(normalized, '[èéêë]', 'e', 'g');
    normalized := REGEXP_REPLACE(normalized, '[ìíîï]', 'i', 'g');
    normalized := REGEXP_REPLACE(normalized, '[òóôõö]', 'o', 'g');
    normalized := REGEXP_REPLACE(normalized, '[ùúûü]', 'u', 'g');
    normalized := REGEXP_REPLACE(normalized, '[ñ]', 'n', 'g');
    normalized := REGEXP_REPLACE(normalized, '[ç]', 'c', 'g');
    
    -- Replace puntuación por espacio (mantener letras/números)
    normalized := REGEXP_REPLACE(normalized, '[^a-z0-9]', ' ', 'g');
    
    -- Colapsar espacios múltiples
    normalized := REGEXP_REPLACE(normalized, '\s+', ' ', 'g');
    
    -- Trim
    normalized := TRIM(normalized);
    
    IF normalized = '' THEN
        RETURN NULL;
    END IF;
    
    RETURN normalized;
END;
$$;

COMMENT ON FUNCTION ops.normalize_person_name IS 
'Normaliza nombre: lower, unaccent, replace puntuación por espacio, colapsar espacios y trim. Mantiene solo letras y números.';

-- 2) ops.normalize_person_tokens_sorted(text) -> text
-- usar normalize_person_name, split por espacio, remover tokens vacíos, ordenar tokens, volver a juntar
CREATE OR REPLACE FUNCTION ops.normalize_person_tokens_sorted(name_text TEXT)
RETURNS TEXT
LANGUAGE plpgsql
IMMUTABLE
AS $$
DECLARE
    normalized TEXT;
    tokens TEXT[];
    filtered_tokens TEXT[];
    token TEXT;
BEGIN
    -- Usar normalize_person_name primero
    normalized := ops.normalize_person_name(name_text);
    
    IF normalized IS NULL OR TRIM(normalized) = '' THEN
        RETURN NULL;
    END IF;
    
    -- Split por espacio
    tokens := string_to_array(normalized, ' ');
    
    -- Remover tokens vacíos
    filtered_tokens := ARRAY[]::TEXT[];
    FOREACH token IN ARRAY tokens
    LOOP
        token := TRIM(token);
        IF token != '' THEN
            filtered_tokens := array_append(filtered_tokens, token);
        END IF;
    END LOOP;
    
    -- Si no quedan tokens, retornar NULL
    IF array_length(filtered_tokens, 1) IS NULL OR array_length(filtered_tokens, 1) = 0 THEN
        RETURN NULL;
    END IF;
    
    -- Ordenar tokens
    SELECT array_agg(token ORDER BY token)
    INTO filtered_tokens
    FROM unnest(filtered_tokens) AS token;
    
    -- Volver a juntar con espacio
    RETURN array_to_string(filtered_tokens, ' ');
END;
$$;

COMMENT ON FUNCTION ops.normalize_person_tokens_sorted IS 
'Normaliza nombre tokenizando, ordenando tokens alfabéticamente y uniendo. Usa normalize_person_name primero.';

-- 3) ops.normalize_person_tokens_sorted_strip_particles(text) -> text
-- igual que tokens_sorted pero remover tokens: de, del, la, las, los, y
CREATE OR REPLACE FUNCTION ops.normalize_person_tokens_sorted_strip_particles(name_text TEXT)
RETURNS TEXT
LANGUAGE plpgsql
IMMUTABLE
AS $$
DECLARE
    normalized TEXT;
    tokens TEXT[];
    filtered_tokens TEXT[];
    token TEXT;
    particles TEXT[] := ARRAY['de', 'del', 'la', 'las', 'los', 'y'];
BEGIN
    -- Usar normalize_person_name primero
    normalized := ops.normalize_person_name(name_text);
    
    IF normalized IS NULL OR TRIM(normalized) = '' THEN
        RETURN NULL;
    END IF;
    
    -- Split por espacio
    tokens := string_to_array(normalized, ' ');
    
    -- Remover tokens vacíos y partículas
    filtered_tokens := ARRAY[]::TEXT[];
    FOREACH token IN ARRAY tokens
    LOOP
        token := TRIM(token);
        IF token != '' AND token != ALL(particles) THEN
            filtered_tokens := array_append(filtered_tokens, token);
        END IF;
    END LOOP;
    
    -- Si no quedan tokens, retornar NULL
    IF array_length(filtered_tokens, 1) IS NULL OR array_length(filtered_tokens, 1) = 0 THEN
        RETURN NULL;
    END IF;
    
    -- Ordenar tokens
    SELECT array_agg(token ORDER BY token)
    INTO filtered_tokens
    FROM unnest(filtered_tokens) AS token;
    
    -- Volver a juntar con espacio
    RETURN array_to_string(filtered_tokens, ' ');
END;
$$;

COMMENT ON FUNCTION ops.normalize_person_tokens_sorted_strip_particles IS 
'Normaliza nombre tokenizando, removiendo partículas (de, del, la, las, los, y), ordenando tokens y uniendo.';

-- ============================================================================
-- A2) Índice Canónico de Drivers
-- ============================================================================

-- Crear/ajustar vista ops.v_driver_name_index_extended
CREATE OR REPLACE VIEW ops.v_driver_name_index_extended AS
WITH driver_names AS (
    SELECT 
        d.driver_id,
        COALESCE(d.full_name, 
            TRIM(COALESCE(d.first_name, '') || ' ' || 
                 COALESCE(d.middle_name, '') || ' ' || 
                 COALESCE(d.last_name, ''))
        ) AS full_name_raw
    FROM public.drivers d
    WHERE d.driver_id IS NOT NULL
        AND (
            d.full_name IS NOT NULL 
            OR (d.first_name IS NOT NULL OR d.last_name IS NOT NULL)
        )
),
driver_with_person_key AS (
    SELECT 
        dn.driver_id,
        dn.full_name_raw,
        il.person_key
    FROM driver_names dn
    LEFT JOIN canon.identity_links il
        ON il.source_table = 'drivers'
        AND il.source_pk = dn.driver_id
    WHERE dn.full_name_raw IS NOT NULL
        AND TRIM(dn.full_name_raw) != ''
)
SELECT 
    dwp.driver_id,
    dwp.person_key,
    dwp.full_name_raw,
    ops.normalize_person_name(dwp.full_name_raw) AS full_name_norm,
    ops.normalize_person_tokens_sorted(dwp.full_name_raw) AS full_name_tokens,
    ops.normalize_person_tokens_sorted_strip_particles(dwp.full_name_raw) AS full_name_tokens_nop
FROM driver_with_person_key dwp
WHERE ops.normalize_person_name(dwp.full_name_raw) IS NOT NULL;

COMMENT ON VIEW ops.v_driver_name_index_extended IS 
'Índice canónico de drivers con múltiples normalizaciones: full_name_norm, full_name_tokens, full_name_tokens_nop. Usado para backfill de identidad en ledger.';

COMMENT ON COLUMN ops.v_driver_name_index_extended.full_name_norm IS 
'Normalización básica: lower, unaccent, sin puntuación, espacios colapsados.';

COMMENT ON COLUMN ops.v_driver_name_index_extended.full_name_tokens IS 
'Tokens ordenados alfabéticamente: permite matching cuando el orden varía.';

COMMENT ON COLUMN ops.v_driver_name_index_extended.full_name_tokens_nop IS 
'Tokens ordenados sin partículas (de, del, la, las, los, y): matching más flexible.';

-- ============================================================================
-- A3) Función de Backfill
-- ============================================================================

CREATE OR REPLACE FUNCTION ops.backfill_ledger_identity(
    min_score_threshold NUMERIC DEFAULT 0.85,
    dry_run BOOLEAN DEFAULT false
)
RETURNS TABLE(
    payment_key TEXT,
    raw_driver_name TEXT,
    candidate_driver_id TEXT,
    candidate_person_key UUID,
    candidate_full_name TEXT,
    match_rule TEXT,
    match_score NUMERIC,
    match_confidence TEXT,
    action_taken TEXT,
    reason TEXT
)
LANGUAGE plpgsql
AS $$
DECLARE
    updated_count INTEGER := 0;
BEGIN
    RETURN QUERY
    WITH ledger_candidates AS (
        SELECT 
            l.id,
            l.payment_key,
            l.raw_driver_name,
            ops.normalize_person_tokens_sorted(l.raw_driver_name) AS ledger_tokens,
            ops.normalize_person_name(l.raw_driver_name) AS ledger_norm,
            ops.normalize_person_tokens_sorted_strip_particles(l.raw_driver_name) AS ledger_tokens_nop
        FROM ops.yango_payment_status_ledger l
        WHERE l.driver_id IS NULL
            AND l.person_key IS NULL
            AND l.raw_driver_name IS NOT NULL
            AND TRIM(l.raw_driver_name) != ''
    ),
    -- R1: exact tokens (score 0.95)
    r1_candidates AS (
        SELECT 
            lc.*,
            dni.driver_id AS candidate_driver_id,
            dni.person_key AS candidate_person_key,
            dni.full_name_raw AS candidate_full_name,
            0.95 AS match_score,
            'r1_tokens_unique' AS match_rule,
            'high' AS match_confidence
        FROM ledger_candidates lc
        INNER JOIN ops.v_driver_name_index_extended dni
            ON lc.ledger_tokens = dni.full_name_tokens
            AND lc.ledger_tokens IS NOT NULL
    ),
    -- R2: exact norm (score 0.85)
    r2_candidates AS (
        SELECT 
            lc.*,
            dni.driver_id AS candidate_driver_id,
            dni.person_key AS candidate_person_key,
            dni.full_name_raw AS candidate_full_name,
            0.85 AS match_score,
            'r2_norm_unique' AS match_rule,
            'medium' AS match_confidence
        FROM ledger_candidates lc
        INNER JOIN ops.v_driver_name_index_extended dni
            ON lc.ledger_norm = dni.full_name_norm
            AND lc.ledger_norm IS NOT NULL
            -- Excluir si ya tiene match en R1
            AND NOT EXISTS (
                SELECT 1 FROM r1_candidates r1 
                WHERE r1.payment_key = lc.payment_key
            )
    ),
    -- R3: exact tokens_nop (score 0.85)
    r3_candidates AS (
        SELECT 
            lc.*,
            dni.driver_id AS candidate_driver_id,
            dni.person_key AS candidate_person_key,
            dni.full_name_raw AS candidate_full_name,
            0.85 AS match_score,
            'r3_tokens_nop_unique' AS match_rule,
            'medium' AS match_confidence
        FROM ledger_candidates lc
        INNER JOIN ops.v_driver_name_index_extended dni
            ON lc.ledger_tokens_nop = dni.full_name_tokens_nop
            AND lc.ledger_tokens_nop IS NOT NULL
            -- Excluir si ya tiene match en R1 o R2
            AND NOT EXISTS (
                SELECT 1 FROM r1_candidates r1 
                WHERE r1.payment_key = lc.payment_key
            )
            AND NOT EXISTS (
                SELECT 1 FROM r2_candidates r2 
                WHERE r2.payment_key = lc.payment_key
            )
    ),
    -- Unir todos los candidatos
    all_candidates AS (
        SELECT * FROM r1_candidates
        UNION ALL
        SELECT * FROM r2_candidates
        UNION ALL
        SELECT * FROM r3_candidates
    ),
    -- Verificar unicidad por payment_key y regla
    candidates_with_uniqueness AS (
        SELECT 
            ac.*,
            COUNT(*) OVER (PARTITION BY ac.payment_key, ac.match_rule) AS candidate_count_per_rule
        FROM all_candidates ac
    ),
    -- Filtrar solo candidatos únicos con score suficiente
    valid_candidates AS (
        SELECT 
            cwu.*
        FROM candidates_with_uniqueness cwu
        WHERE cwu.candidate_count_per_rule = 1
            AND cwu.match_score >= min_score_threshold
    ),
    -- Para cada payment_key, elegir el mejor candidato (mayor score)
    best_candidates AS (
        SELECT DISTINCT ON (vc.payment_key)
            vc.*
        FROM valid_candidates vc
        ORDER BY vc.payment_key, vc.match_score DESC
    )
    SELECT 
        bc.payment_key,
        bc.raw_driver_name,
        bc.candidate_driver_id::TEXT,
        bc.candidate_person_key,
        bc.candidate_full_name,
        bc.match_rule,
        bc.match_score,
        bc.match_confidence,
        CASE 
            WHEN dry_run THEN 'DRY_RUN_SKIP'
            ELSE 'UPDATED'
        END AS action_taken,
        CASE 
            WHEN dry_run THEN 'Dry run mode: no actualización realizada'
            ELSE 'Candidato único con score suficiente'
        END AS reason
    FROM best_candidates bc
    ORDER BY bc.match_score DESC, bc.payment_key;
    
    -- Si no es dry_run, realizar actualizaciones
    IF NOT dry_run THEN
        WITH ledger_candidates AS (
            SELECT 
                l.id,
                l.payment_key,
                l.raw_driver_name,
                ops.normalize_person_tokens_sorted(l.raw_driver_name) AS ledger_tokens,
                ops.normalize_person_name(l.raw_driver_name) AS ledger_norm,
                ops.normalize_person_tokens_sorted_strip_particles(l.raw_driver_name) AS ledger_tokens_nop
            FROM ops.yango_payment_status_ledger l
            WHERE l.driver_id IS NULL
                AND l.person_key IS NULL
                AND l.raw_driver_name IS NOT NULL
                AND TRIM(l.raw_driver_name) != ''
        ),
        r1_candidates AS (
            SELECT 
                lc.*,
                dni.driver_id AS candidate_driver_id,
                dni.person_key AS candidate_person_key,
                0.95 AS match_score,
                'r1_tokens_unique' AS match_rule,
                'high' AS match_confidence
            FROM ledger_candidates lc
            INNER JOIN ops.v_driver_name_index_extended dni
                ON lc.ledger_tokens = dni.full_name_tokens
                AND lc.ledger_tokens IS NOT NULL
        ),
        r2_candidates AS (
            SELECT 
                lc.*,
                dni.driver_id AS candidate_driver_id,
                dni.person_key AS candidate_person_key,
                0.85 AS match_score,
                'r2_norm_unique' AS match_rule,
                'medium' AS match_confidence
            FROM ledger_candidates lc
            INNER JOIN ops.v_driver_name_index_extended dni
                ON lc.ledger_norm = dni.full_name_norm
                AND lc.ledger_norm IS NOT NULL
                AND NOT EXISTS (
                    SELECT 1 FROM r1_candidates r1 
                    WHERE r1.payment_key = lc.payment_key
                )
        ),
        r3_candidates AS (
            SELECT 
                lc.*,
                dni.driver_id AS candidate_driver_id,
                dni.person_key AS candidate_person_key,
                0.85 AS match_score,
                'r3_tokens_nop_unique' AS match_rule,
                'medium' AS match_confidence
            FROM ledger_candidates lc
            INNER JOIN ops.v_driver_name_index_extended dni
                ON lc.ledger_tokens_nop = dni.full_name_tokens_nop
                AND lc.ledger_tokens_nop IS NOT NULL
                AND NOT EXISTS (
                    SELECT 1 FROM r1_candidates r1 
                    WHERE r1.payment_key = lc.payment_key
                )
                AND NOT EXISTS (
                    SELECT 1 FROM r2_candidates r2 
                    WHERE r2.payment_key = lc.payment_key
                )
        ),
        all_candidates AS (
            SELECT * FROM r1_candidates
            UNION ALL
            SELECT * FROM r2_candidates
            UNION ALL
            SELECT * FROM r3_candidates
        ),
        candidates_with_uniqueness AS (
            SELECT 
                ac.*,
                COUNT(*) OVER (PARTITION BY ac.payment_key, ac.match_rule) AS candidate_count_per_rule
            FROM all_candidates ac
        ),
        valid_candidates AS (
            SELECT 
                cwu.*
            FROM candidates_with_uniqueness cwu
            WHERE cwu.candidate_count_per_rule = 1
                AND cwu.match_score >= min_score_threshold
        ),
        best_candidates AS (
            SELECT DISTINCT ON (vc.payment_key)
                vc.id,
                vc.candidate_driver_id,
                vc.candidate_person_key,
                vc.match_rule,
                vc.match_confidence
            FROM valid_candidates vc
            ORDER BY vc.payment_key, vc.match_score DESC
        )
        UPDATE ops.yango_payment_status_ledger l
        SET 
            driver_id = bc.candidate_driver_id,
            person_key = bc.candidate_person_key,
            match_rule = bc.match_rule,
            match_confidence = bc.match_confidence
        FROM best_candidates bc
        WHERE l.id = bc.id
            AND l.driver_id IS NULL
            AND l.person_key IS NULL;
        
        GET DIAGNOSTICS updated_count = ROW_COUNT;
    END IF;
    
    RETURN;
END;
$$;

COMMENT ON FUNCTION ops.backfill_ledger_identity IS 
'Backfill de identidad en ledger usando 3 reglas (R1: tokens 0.95, R2: norm 0.85, R3: tokens_nop 0.85). Solo actualiza si score >= umbral y candidato único. Parámetros: min_score_threshold (default 0.85), dry_run (default false).';

-- ============================================================================
-- A4) Queries de Verificación
-- ============================================================================

-- Query 1: total, enriched, still_null
CREATE OR REPLACE VIEW ops.v_ledger_backfill_stats AS
SELECT 
    COUNT(*) AS total,
    COUNT(*) FILTER (WHERE driver_id IS NOT NULL OR person_key IS NOT NULL) AS enriched,
    COUNT(*) FILTER (WHERE driver_id IS NULL AND person_key IS NULL) AS still_null,
    ROUND(
        100.0 * COUNT(*) FILTER (WHERE driver_id IS NOT NULL OR person_key IS NOT NULL) / 
        NULLIF(COUNT(*), 0),
        2
    ) AS enrichment_percentage
FROM ops.yango_payment_status_ledger;

COMMENT ON VIEW ops.v_ledger_backfill_stats IS 
'Estadísticas de backfill: total, enriched, still_null, enrichment_percentage.';

-- Query 2: distribución por match_rule
CREATE OR REPLACE VIEW ops.v_ledger_match_rule_distribution AS
SELECT 
    COALESCE(match_rule, 'none') AS match_rule,
    COUNT(*) AS row_count,
    ROUND(100.0 * COUNT(*) / NULLIF((SELECT COUNT(*) FROM ops.yango_payment_status_ledger), 0), 2) AS percentage
FROM ops.yango_payment_status_ledger
GROUP BY match_rule
ORDER BY 
    CASE match_rule
        WHEN 'r1_tokens_unique' THEN 1
        WHEN 'r2_norm_unique' THEN 2
        WHEN 'r3_tokens_nop_unique' THEN 3
        WHEN 'none' THEN 4
        ELSE 5
    END;

COMMENT ON VIEW ops.v_ledger_match_rule_distribution IS 
'Distribución de matches por regla: r1_tokens_unique, r2_norm_unique, r3_tokens_nop_unique, none.';

-- Query 3: lista de ambiguos (candidates>1) para revisión manual
CREATE OR REPLACE VIEW ops.v_ledger_ambiguous_candidates AS
WITH ledger_candidates AS (
    SELECT 
        l.payment_key,
        l.raw_driver_name,
        ops.normalize_person_tokens_sorted(l.raw_driver_name) AS ledger_tokens,
        ops.normalize_person_name(l.raw_driver_name) AS ledger_norm,
        ops.normalize_person_tokens_sorted_strip_particles(l.raw_driver_name) AS ledger_tokens_nop
    FROM ops.yango_payment_status_ledger l
    WHERE l.driver_id IS NULL
        AND l.person_key IS NULL
        AND l.raw_driver_name IS NOT NULL
        AND TRIM(l.raw_driver_name) != ''
),
r1_candidates AS (
    SELECT 
        lc.payment_key,
        lc.raw_driver_name,
        dni.driver_id,
        dni.person_key,
        dni.full_name_raw,
        0.95 AS match_score,
        'r1_tokens_unique' AS match_rule
    FROM ledger_candidates lc
    INNER JOIN ops.v_driver_name_index_extended dni
        ON lc.ledger_tokens = dni.full_name_tokens
        AND lc.ledger_tokens IS NOT NULL
),
r2_candidates AS (
    SELECT 
        lc.payment_key,
        lc.raw_driver_name,
        dni.driver_id,
        dni.person_key,
        dni.full_name_raw,
        0.85 AS match_score,
        'r2_norm_unique' AS match_rule
    FROM ledger_candidates lc
    INNER JOIN ops.v_driver_name_index_extended dni
        ON lc.ledger_norm = dni.full_name_norm
        AND lc.ledger_norm IS NOT NULL
        AND NOT EXISTS (
            SELECT 1 FROM r1_candidates r1 
            WHERE r1.payment_key = lc.payment_key
        )
),
r3_candidates AS (
    SELECT 
        lc.payment_key,
        lc.raw_driver_name,
        dni.driver_id,
        dni.person_key,
        dni.full_name_raw,
        0.85 AS match_score,
        'r3_tokens_nop_unique' AS match_rule
    FROM ledger_candidates lc
    INNER JOIN ops.v_driver_name_index_extended dni
        ON lc.ledger_tokens_nop = dni.full_name_tokens_nop
        AND lc.ledger_tokens_nop IS NOT NULL
        AND NOT EXISTS (
            SELECT 1 FROM r1_candidates r1 
            WHERE r1.payment_key = lc.payment_key
        )
        AND NOT EXISTS (
            SELECT 1 FROM r2_candidates r2 
            WHERE r2.payment_key = lc.payment_key
        )
),
all_candidates AS (
    SELECT * FROM r1_candidates
    UNION ALL
    SELECT * FROM r2_candidates
    UNION ALL
    SELECT * FROM r3_candidates
),
candidates_with_uniqueness AS (
    SELECT 
        ac.*,
        COUNT(*) OVER (PARTITION BY ac.payment_key, ac.match_rule) AS candidate_count_per_rule
    FROM all_candidates ac
)
SELECT 
    payment_key,
    raw_driver_name,
    match_rule,
    candidate_count_per_rule,
    MAX(match_score) AS max_score,
    'AMBIGUOUS' AS reason
FROM candidates_with_uniqueness
WHERE candidate_count_per_rule > 1
GROUP BY payment_key, raw_driver_name, match_rule, candidate_count_per_rule
ORDER BY candidate_count_per_rule DESC, max_score DESC;

COMMENT ON VIEW ops.v_ledger_ambiguous_candidates IS 
'Candidatos ambiguos (múltiples matches por regla) que NO fueron actualizados por seguridad. Para revisión manual.';










