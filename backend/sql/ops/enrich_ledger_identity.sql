-- ============================================================================
-- Sistema de Enriquecimiento de Identidad para Ledger de Pagos Yango
-- ============================================================================
-- Enriquece ops.yango_payment_status_ledger con driver_id/person_key
-- SIN reingestar pagos, usando reglas + scoring auditables.
--
-- RESTRICCIONES:
-- - Solo actualiza cuando score >= umbral Y candidato único
-- - Prohibido asignar identidad si hay ambigüedad
-- - Todo cambio debe ser explicable (evidence)
-- ============================================================================

-- ============================================================================
-- A1) Función de Normalización Mejorada
-- ============================================================================
-- Función única ops.normalize_person_name(text) con:
-- - lower, unaccent
-- - remover puntuación
-- - colapsar espacios
-- - tokenizar y ordenar
-- - remover partículas (de, del, la, los) bajo flag
-- ============================================================================

CREATE OR REPLACE FUNCTION ops.normalize_person_name(
    name_text TEXT,
    remove_particles BOOLEAN DEFAULT true
)
RETURNS TEXT
LANGUAGE plpgsql
IMMUTABLE
AS $$
DECLARE
    normalized TEXT;
    tokens TEXT[];
    filtered_tokens TEXT[];
    token TEXT;
    result TEXT;
    particles TEXT[] := ARRAY['de', 'del', 'la', 'las', 'los', 'lo', 'le', 'les', 'y', 'e', 'el', 'a', 'al', 'en', 'un', 'una', 'unos', 'unas', 'da', 'das', 'do', 'dos'];
BEGIN
    IF name_text IS NULL OR TRIM(name_text) = '' THEN
        RETURN NULL;
    END IF;
    
    -- Paso 1: Convertir a minúsculas
    normalized := LOWER(name_text);
    
    -- Paso 2: Quitar tildes (unaccent)
    normalized := REGEXP_REPLACE(normalized, '[àáâãäå]', 'a', 'g');
    normalized := REGEXP_REPLACE(normalized, '[èéêë]', 'e', 'g');
    normalized := REGEXP_REPLACE(normalized, '[ìíîï]', 'i', 'g');
    normalized := REGEXP_REPLACE(normalized, '[òóôõö]', 'o', 'g');
    normalized := REGEXP_REPLACE(normalized, '[ùúûü]', 'u', 'g');
    normalized := REGEXP_REPLACE(normalized, '[ñ]', 'n', 'g');
    normalized := REGEXP_REPLACE(normalized, '[ç]', 'c', 'g');
    
    -- Paso 3: Remover puntuación (excepto espacios y guiones)
    normalized := REGEXP_REPLACE(normalized, '[.,;:!?''"()\[\]{}]', ' ', 'g');
    
    -- Paso 4: Colapsar espacios múltiples
    normalized := REGEXP_REPLACE(normalized, '\s+', ' ', 'g');
    
    -- Paso 5: Trim
    normalized := TRIM(normalized);
    
    IF normalized IS NULL OR TRIM(normalized) = '' THEN
        RETURN NULL;
    END IF;
    
    -- Paso 6: Tokenizar
    tokens := string_to_array(normalized, ' ');
    
    -- Paso 7: Filtrar tokens
    filtered_tokens := ARRAY[]::TEXT[];
    FOREACH token IN ARRAY tokens
    LOOP
        token := TRIM(token);
        -- Remover guiones y caracteres especiales restantes
        token := REGEXP_REPLACE(token, '[^a-z0-9]', '', 'g');
        
        -- Solo incluir si:
        -- - No está vacío
        -- - Tiene al menos 2 caracteres
        -- - (Opcional) No es partícula
        IF token != '' 
           AND LENGTH(token) >= 2
           AND (NOT remove_particles OR LOWER(token) != ALL(particles))
        THEN
            filtered_tokens := array_append(filtered_tokens, token);
        END IF;
    END LOOP;
    
    -- Si no quedan tokens válidos, retornar NULL
    IF array_length(filtered_tokens, 1) IS NULL OR array_length(filtered_tokens, 1) = 0 THEN
        RETURN NULL;
    END IF;
    
    -- Paso 8: Ordenar tokens alfabéticamente
    SELECT array_agg(token ORDER BY token)
    INTO filtered_tokens
    FROM unnest(filtered_tokens) AS token;
    
    -- Paso 9: Volver a unir con espacio
    result := array_to_string(filtered_tokens, ' ');
    
    RETURN result;
END;
$$;

COMMENT ON FUNCTION ops.normalize_person_name IS 
'Normalización robusta de nombres de personas: lower, unaccent, remover puntuación, colapsar espacios, tokenizar, ordenar alfabéticamente, y opcionalmente remover partículas. Determinística y permite matching cuando el orden varía.';

-- ============================================================================
-- A2) Función de Scoring y Matching
-- ============================================================================
-- Calcula score de matching entre nombre del ledger y candidato del índice
-- ============================================================================

CREATE OR REPLACE FUNCTION ops.calculate_name_match_score(
    ledger_name TEXT,
    candidate_name TEXT
)
RETURNS NUMERIC
LANGUAGE plpgsql
IMMUTABLE
AS $$
DECLARE
    ledger_norm TEXT;
    candidate_norm TEXT;
    score NUMERIC := 0;
    exact_match BOOLEAN := false;
    tokens_match BOOLEAN := false;
BEGIN
    IF ledger_name IS NULL OR candidate_name IS NULL THEN
        RETURN 0;
    END IF;
    
    -- Normalizar ambos nombres
    ledger_norm := ops.normalize_person_name(ledger_name, true);
    candidate_norm := ops.normalize_person_name(candidate_name, true);
    
    IF ledger_norm IS NULL OR candidate_norm IS NULL THEN
        RETURN 0;
    END IF;
    
    -- Score 100: Match exacto (después de normalización)
    IF ledger_norm = candidate_norm THEN
        exact_match := true;
        score := 100;
    ELSE
        -- Score 85: Match por tokens ordenados (mismos tokens, orden diferente)
        -- Verificar si todos los tokens coinciden
        tokens_match := (
            SELECT COUNT(*) = (
                SELECT COUNT(*) 
                FROM unnest(string_to_array(ledger_norm, ' ')) AS t1
            )
            FROM unnest(string_to_array(ledger_norm, ' ')) AS t1
            WHERE t1 = ANY(string_to_array(candidate_norm, ' '))
        );
        
        IF tokens_match THEN
            score := 85;
        ELSE
            -- Score parcial: porcentaje de tokens que coinciden
            WITH ledger_tokens AS (
                SELECT unnest(string_to_array(ledger_norm, ' ')) AS token
            ),
            candidate_tokens AS (
                SELECT unnest(string_to_array(candidate_norm, ' ')) AS token
            ),
            matched_tokens AS (
                SELECT COUNT(*) AS matched
                FROM ledger_tokens lt
                WHERE EXISTS (
                    SELECT 1 FROM candidate_tokens ct WHERE ct.token = lt.token
                )
            ),
            total_tokens AS (
                SELECT GREATEST(
                    (SELECT COUNT(*) FROM ledger_tokens),
                    (SELECT COUNT(*) FROM candidate_tokens)
                ) AS total
            )
            SELECT 
                CASE 
                    WHEN total > 0 THEN (matched::NUMERIC / total::NUMERIC) * 70
                    ELSE 0
                END
            INTO score
            FROM matched_tokens, total_tokens;
        END IF;
    END IF;
    
    RETURN score;
END;
$$;

COMMENT ON FUNCTION ops.calculate_name_match_score IS 
'Calcula score de matching entre dos nombres (0-100). Score 100: match exacto. Score 85: mismos tokens, orden diferente. Score <85: porcentaje de tokens coincidentes * 70.';

-- ============================================================================
-- A3) Función Principal de Enriquecimiento
-- ============================================================================
-- Enriquece identidad en ops.yango_payment_status_ledger
-- Solo actualiza cuando score >= umbral Y candidato único
-- ============================================================================

CREATE OR REPLACE FUNCTION ops.enrich_ledger_identity(
    min_score_threshold NUMERIC DEFAULT 85,
    dry_run BOOLEAN DEFAULT false
)
RETURNS TABLE(
    payment_key TEXT,
    raw_driver_name TEXT,
    candidate_driver_id TEXT,
    candidate_person_key UUID,
    candidate_full_name TEXT,
    match_score NUMERIC,
    match_rule TEXT,
    match_confidence TEXT,
    action_taken TEXT,
    reason TEXT
)
LANGUAGE plpgsql
AS $$
DECLARE
    updated_count INTEGER := 0;
BEGIN
    -- CTE común: Candidatos para enriquecimiento (solo registros sin identidad)
    RETURN QUERY
    WITH ledger_candidates AS (
        SELECT 
            l.id,
            l.payment_key,
            l.raw_driver_name,
            l.driver_name_normalized
        FROM ops.yango_payment_status_ledger l
        WHERE l.driver_id IS NULL
            AND l.person_key IS NULL
            AND l.raw_driver_name IS NOT NULL
            AND TRIM(l.raw_driver_name) != ''
    ),
    -- CTE: Matching contra índice de drivers
    candidates_with_scores AS (
        SELECT 
            lc.*,
            dni.driver_id AS candidate_driver_id,
            dni.person_key AS candidate_person_key,
            dni.full_name_raw AS candidate_full_name,
            ops.calculate_name_match_score(lc.raw_driver_name, dni.full_name_raw) AS match_score
        FROM ledger_candidates lc
        INNER JOIN ops.v_driver_name_index_extended dni
            ON (
                -- Match por normalización (básica o tokens ordenados)
                ops.normalize_person_name(lc.raw_driver_name, true) = 
                ops.normalize_person_name(dni.full_name_raw, true)
            )
    ),
    -- CTE: Verificar unicidad por payment_key
    candidates_with_uniqueness AS (
        SELECT 
            cws.*,
            COUNT(*) OVER (PARTITION BY cws.payment_key) AS candidate_count
        FROM candidates_with_scores cws
    ),
    -- CTE: Filtrar solo candidatos únicos con score suficiente y determinar regla/confianza
    valid_candidates AS (
        SELECT 
            cwu.id,
            cwu.payment_key,
            cwu.raw_driver_name,
            cwu.candidate_driver_id,
            cwu.candidate_person_key,
            cwu.candidate_full_name,
            cwu.match_score,
            CASE 
                WHEN cwu.match_score >= 100 THEN 'name_exact_match'
                WHEN cwu.match_score >= 85 THEN 'name_tokens_match'
                ELSE 'name_partial_match'
            END AS match_rule,
            CASE 
                WHEN cwu.match_score >= 100 THEN 'high'
                WHEN cwu.match_score >= 85 THEN 'medium'
                ELSE 'low'
            END AS match_confidence
        FROM candidates_with_uniqueness cwu
        WHERE cwu.candidate_count = 1
            AND cwu.match_score >= min_score_threshold
    )
    SELECT 
        vc.payment_key,
        vc.raw_driver_name,
        vc.candidate_driver_id::TEXT,
        vc.candidate_person_key,
        vc.candidate_full_name,
        vc.match_score,
        vc.match_rule,
        vc.match_confidence,
        CASE 
            WHEN dry_run THEN 'DRY_RUN_SKIP'
            ELSE 'UPDATED'
        END AS action_taken,
        CASE 
            WHEN dry_run THEN 'Dry run mode: no actualización realizada'
            ELSE 'Candidato único con score suficiente'
        END AS reason
    FROM valid_candidates vc
    ORDER BY vc.match_score DESC, vc.payment_key;
    
    -- Si no es dry_run, realizar actualizaciones usando la misma lógica
    IF NOT dry_run THEN
        WITH ledger_candidates AS (
            SELECT 
                l.id,
                l.payment_key,
                l.raw_driver_name
            FROM ops.yango_payment_status_ledger l
            WHERE l.driver_id IS NULL
                AND l.person_key IS NULL
                AND l.raw_driver_name IS NOT NULL
                AND TRIM(l.raw_driver_name) != ''
        ),
        candidates_with_scores AS (
            SELECT 
                lc.*,
                dni.driver_id AS candidate_driver_id,
                dni.person_key AS candidate_person_key,
                ops.calculate_name_match_score(lc.raw_driver_name, dni.full_name_raw) AS match_score
            FROM ledger_candidates lc
            INNER JOIN ops.v_driver_name_index_extended dni
                ON (
                    ops.normalize_person_name(lc.raw_driver_name, true) = 
                    ops.normalize_person_name(dni.full_name_raw, true)
                )
        ),
        candidates_with_uniqueness AS (
            SELECT 
                cws.*,
                COUNT(*) OVER (PARTITION BY cws.payment_key) AS candidate_count
            FROM candidates_with_scores cws
        ),
        valid_candidates AS (
            SELECT 
                cwu.id,
                cwu.candidate_driver_id,
                cwu.candidate_person_key,
                CASE 
                    WHEN cwu.match_score >= 100 THEN 'name_exact_match'
                    WHEN cwu.match_score >= 85 THEN 'name_tokens_match'
                    ELSE 'name_partial_match'
                END AS match_rule,
                CASE 
                    WHEN cwu.match_score >= 100 THEN 'high'
                    WHEN cwu.match_score >= 85 THEN 'medium'
                    ELSE 'low'
                END AS match_confidence
            FROM candidates_with_uniqueness cwu
            WHERE cwu.candidate_count = 1
                AND cwu.match_score >= min_score_threshold
        )
        UPDATE ops.yango_payment_status_ledger l
        SET 
            driver_id = vc.candidate_driver_id,
            person_key = vc.candidate_person_key,
            match_rule = vc.match_rule,
            match_confidence = vc.match_confidence
        FROM valid_candidates vc
        WHERE l.id = vc.id
            AND l.driver_id IS NULL
            AND l.person_key IS NULL;
        
        GET DIAGNOSTICS updated_count = ROW_COUNT;
    END IF;
    
    RETURN;
END;
$$;

COMMENT ON FUNCTION ops.enrich_ledger_identity IS 
'Enriquece identidad en ops.yango_payment_status_ledger usando matching por nombre. Solo actualiza cuando score >= umbral Y candidato único. Retorna tabla con resultados y acciones tomadas. Parámetros: min_score_threshold (default 85), dry_run (default false).';

-- ============================================================================
-- A4) Queries de Verificación
-- ============================================================================

-- Query 1: % enriquecido
CREATE OR REPLACE VIEW ops.v_ledger_enrichment_stats AS
SELECT 
    COUNT(*) AS total_rows,
    COUNT(*) FILTER (WHERE driver_id IS NOT NULL OR person_key IS NOT NULL) AS enriched_rows,
    COUNT(*) FILTER (WHERE driver_id IS NULL AND person_key IS NULL) AS unenriched_rows,
    ROUND(
        100.0 * COUNT(*) FILTER (WHERE driver_id IS NOT NULL OR person_key IS NOT NULL) / 
        NULLIF(COUNT(*), 0),
        2
    ) AS enrichment_percentage,
    COUNT(*) FILTER (WHERE match_rule = 'none') AS match_none_count,
    COUNT(*) FILTER (WHERE match_confidence = 'unknown') AS confidence_unknown_count,
    COUNT(*) FILTER (WHERE match_rule != 'none' AND match_confidence != 'unknown') AS successfully_matched_count
FROM ops.yango_payment_status_ledger;

COMMENT ON VIEW ops.v_ledger_enrichment_stats IS 
'Estadísticas de enriquecimiento del ledger: total, enriquecidos, no enriquecidos, porcentaje, y distribución por regla/confianza.';

-- Query 2: # ambiguos (no actualizados)
CREATE OR REPLACE VIEW ops.v_ledger_ambiguous_candidates AS
WITH ledger_candidates AS (
    SELECT 
        l.payment_key,
        l.raw_driver_name,
        l.driver_name_normalized
    FROM ops.yango_payment_status_ledger l
    WHERE l.driver_id IS NULL
        AND l.person_key IS NULL
        AND l.raw_driver_name IS NOT NULL
        AND TRIM(l.raw_driver_name) != ''
),
candidates_with_scores AS (
    SELECT 
        lc.*,
        dni.driver_id AS candidate_driver_id,
        dni.person_key AS candidate_person_key,
        dni.full_name_raw AS candidate_full_name,
        ops.calculate_name_match_score(lc.raw_driver_name, dni.full_name_raw) AS match_score
    FROM ledger_candidates lc
    INNER JOIN ops.v_driver_name_index_extended dni
        ON (
            ops.normalize_person_name(lc.raw_driver_name, true) = 
            ops.normalize_person_name(dni.full_name_raw, true)
        )
        OR (
            ops.normalize_person_name(lc.raw_driver_name, true) IS NOT NULL
            AND ops.normalize_person_name(dni.full_name_raw, true) IS NOT NULL
            AND ops.normalize_person_name(lc.raw_driver_name, true) = 
                ops.normalize_person_name(dni.full_name_raw, true)
        )
),
candidates_with_uniqueness AS (
    SELECT 
        cws.*,
        COUNT(*) OVER (PARTITION BY cws.payment_key) AS candidate_count,
        MAX(cws.match_score) OVER (PARTITION BY cws.payment_key) AS max_score
    FROM candidates_with_scores cws
)
SELECT 
    payment_key,
    raw_driver_name,
    candidate_count,
    max_score,
    'AMBIGUOUS' AS reason
FROM candidates_with_uniqueness
WHERE candidate_count > 1
GROUP BY payment_key, raw_driver_name, candidate_count, max_score
ORDER BY candidate_count DESC, max_score DESC;

COMMENT ON VIEW ops.v_ledger_ambiguous_candidates IS 
'Candidatos ambiguos (múltiples matches) que NO fueron actualizados por seguridad. Muestra payment_key, nombre, cantidad de candidatos, y score máximo.';

-- Query 3: Distribución por regla/confianza
CREATE OR REPLACE VIEW ops.v_ledger_match_distribution AS
SELECT 
    match_rule,
    match_confidence,
    COUNT(*) AS row_count,
    ROUND(100.0 * COUNT(*) / NULLIF((SELECT COUNT(*) FROM ops.yango_payment_status_ledger), 0), 2) AS percentage
FROM ops.yango_payment_status_ledger
GROUP BY match_rule, match_confidence
ORDER BY match_confidence DESC, match_rule;

COMMENT ON VIEW ops.v_ledger_match_distribution IS 
'Distribución de matches en el ledger por regla y confianza. Muestra conteo y porcentaje de cada combinación.';

