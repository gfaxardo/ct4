-- ============================================================================
-- Script Completo: Setup Materialized View de Drivers del Park (Todo en Uno)
-- ============================================================================
-- Este script ejecuta todos los pasos necesarios para crear la materialized
-- view de drivers del park optimizada para matching por nombre.
-- 
-- Ejecuta este script completo en pgAdmin para crear:
-- 1. Funciones de normalización (si no existen)
-- 2. Materialized view con índices
-- 3. Refrescar la materialized view inicialmente
-- ============================================================================

-- ============================================================================
-- PASO 1: Crear funciones de normalización
-- ============================================================================

-- Función: normalize_name_basic
CREATE OR REPLACE FUNCTION ops.normalize_name_basic(name_text TEXT)
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
    -- Convertir a mayúsculas
    normalized := UPPER(normalized);
    -- Quitar tildes
    normalized := REGEXP_REPLACE(normalized, '[ÀÁÂÃÄÅ]', 'A', 'g');
    normalized := REGEXP_REPLACE(normalized, '[ÈÉÊË]', 'E', 'g');
    normalized := REGEXP_REPLACE(normalized, '[ÌÍÎÏ]', 'I', 'g');
    normalized := REGEXP_REPLACE(normalized, '[ÒÓÔÕÖ]', 'O', 'g');
    normalized := REGEXP_REPLACE(normalized, '[ÙÚÛÜ]', 'U', 'g');
    normalized := REGEXP_REPLACE(normalized, '[Ñ]', 'N', 'g');
    normalized := REGEXP_REPLACE(normalized, '[Ç]', 'C', 'g');
    -- Quitar puntuación (excepto espacios y guiones que manejaremos después)
    normalized := REGEXP_REPLACE(normalized, '[.,;:!?]', ' ', 'g');
    -- Colapsar espacios múltiples
    normalized := REGEXP_REPLACE(normalized, '\s+', ' ', 'g');
    -- Trim
    normalized := TRIM(normalized);
    
    RETURN normalized;
END;
$$;

COMMENT ON FUNCTION ops.normalize_name_basic IS 
'Normalización básica de nombres: convierte a mayúsculas, quita tildes, puntuación, y colapsa espacios. Determinística.';

-- Función: normalize_name_tokens_sorted
CREATE OR REPLACE FUNCTION ops.normalize_name_tokens_sorted(name_text TEXT)
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
BEGIN
    IF name_text IS NULL OR TRIM(name_text) = '' THEN
        RETURN NULL;
    END IF;
    
    -- Primero normalizar básicamente
    normalized := ops.normalize_name_basic(name_text);
    
    IF normalized IS NULL OR TRIM(normalized) = '' THEN
        RETURN NULL;
    END IF;
    
    -- Tokenizar por espacios
    tokens := string_to_array(normalized, ' ');
    
    -- Filtrar tokens: remover vacíos, muy cortos (< 2 chars), y palabras comunes
    filtered_tokens := ARRAY[]::TEXT[];
    FOREACH token IN ARRAY tokens
    LOOP
        token := TRIM(token);
        -- Solo incluir si:
        -- - No está vacío
        -- - Tiene al menos 2 caracteres
        -- - No es una palabra común ("de", "del", "la", "los", "y", "el", "las", "le", "les")
        IF token != '' 
           AND LENGTH(token) >= 2
           AND LOWER(token) NOT IN ('de', 'del', 'la', 'las', 'los', 'lo', 'le', 'les', 'y', 'e', 'el', 'a', 'al', 'en', 'un', 'una', 'unos', 'unas')
        THEN
            filtered_tokens := array_append(filtered_tokens, token);
        END IF;
    END LOOP;
    
    -- Si no quedan tokens válidos, retornar NULL
    IF array_length(filtered_tokens, 1) IS NULL OR array_length(filtered_tokens, 1) = 0 THEN
        RETURN NULL;
    END IF;
    
    -- Ordenar tokens alfabéticamente
    SELECT array_agg(t ORDER BY t)
    INTO filtered_tokens
    FROM unnest(filtered_tokens) AS t;
    
    -- Volver a unir con espacio
    result := array_to_string(filtered_tokens, ' ');
    
    RETURN result;
END;
$$;

COMMENT ON FUNCTION ops.normalize_name_tokens_sorted IS 
'Normaliza nombre tokenizando, removiendo palabras comunes ("de", "del", etc.), ordenando tokens alfabéticamente, y uniendo. Permite matching cuando el orden varía (determinístico).';

-- ============================================================================
-- PASO 2: Crear Materialized View
-- ============================================================================

DROP MATERIALIZED VIEW IF EXISTS ops.mv_drivers_park_08e20910d81d42658d4334d3f6d10ac0 CASCADE;

CREATE MATERIALIZED VIEW ops.mv_drivers_park_08e20910d81d42658d4334d3f6d10ac0 AS
SELECT
    d.driver_id,
    d.park_id,
    COALESCE(d.full_name::TEXT, 
        TRIM(COALESCE(d.first_name::TEXT, '') || ' ' || 
             COALESCE(d.middle_name::TEXT, '') || ' ' || 
             COALESCE(d.last_name::TEXT, ''))) AS driver_name,
    ops.normalize_name_basic(COALESCE(d.full_name::TEXT, 
        TRIM(COALESCE(d.first_name::TEXT, '') || ' ' || 
             COALESCE(d.middle_name::TEXT, '') || ' ' || 
             COALESCE(d.last_name::TEXT, '')))) AS driver_full_norm,
    ops.normalize_name_tokens_sorted(COALESCE(d.full_name::TEXT,
        TRIM(COALESCE(d.first_name::TEXT, '') || ' ' || 
             COALESCE(d.middle_name::TEXT, '') || ' ' || 
             COALESCE(d.last_name::TEXT, '')))) AS driver_tokens_sorted
FROM public.drivers d
WHERE d.park_id = '08e20910d81d42658d4334d3f6d10ac0'
    AND d.driver_id IS NOT NULL
    AND (d.full_name IS NOT NULL 
         OR d.first_name IS NOT NULL 
         OR d.last_name IS NOT NULL);

-- ============================================================================
-- PASO 3: Crear Índices
-- ============================================================================

CREATE UNIQUE INDEX idx_mv_drivers_park_08e20910d81d42658d4334d3f6d10ac0_driver_id 
    ON ops.mv_drivers_park_08e20910d81d42658d4334d3f6d10ac0 (driver_id);

CREATE INDEX idx_mv_drivers_park_08e20910d81d42658d4334d3f6d10ac0_full_norm 
    ON ops.mv_drivers_park_08e20910d81d42658d4334d3f6d10ac0 (driver_full_norm)
    WHERE driver_full_norm IS NOT NULL;

CREATE INDEX idx_mv_drivers_park_tokens_sorted 
    ON ops.mv_drivers_park_08e20910d81d42658d4334d3f6d10ac0 (driver_tokens_sorted)
    WHERE driver_tokens_sorted IS NOT NULL;

-- ============================================================================
-- PASO 4: Comentarios
-- ============================================================================

COMMENT ON MATERIALIZED VIEW ops.mv_drivers_park_08e20910d81d42658d4334d3f6d10ac0 IS 
'Materialized view de drivers del park_id 08e20910d81d42658d4334d3f6d10ac0 con nombres normalizados. Usada por v_yango_payments_ledger_latest_enriched para reducir el universo de matching y mejorar performance. Debe refrescarse periódicamente cuando se agreguen nuevos drivers al park.';

COMMENT ON COLUMN ops.mv_drivers_park_08e20910d81d42658d4334d3f6d10ac0.driver_full_norm IS 
'Nombre completo normalizado usando ops.normalize_name_basic(). Usado para matching por nombre completo.';

COMMENT ON COLUMN ops.mv_drivers_park_08e20910d81d42658d4334d3f6d10ac0.driver_tokens_sorted IS 
'Tokens del nombre ordenados usando ops.normalize_name_tokens_sorted(). Usado para matching por tokens (permite orden invertido).';

-- ============================================================================
-- PASO 5: Refrescar Materialized View Inicialmente
-- ============================================================================

-- La materialized view ya está poblada al crearse, pero podemos verificar:
SELECT 
    COUNT(*) AS total_drivers,
    COUNT(DISTINCT driver_id) AS distinct_driver_ids
FROM ops.mv_drivers_park_08e20910d81d42658d4334d3f6d10ac0;

-- ============================================================================
-- FIN: Setup completo
-- ============================================================================

