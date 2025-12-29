-- ============================================================================
-- Funciones de Normalización de Nombres (Determinísticas)
-- ============================================================================
-- Funciones auxiliares para normalizar nombres de forma determinística,
-- permitiendo matching incluso cuando el orden de palabras varía
-- (ej: "Apellido Nombre" vs "Nombre Apellido").
-- ============================================================================

-- Función: normalize_name_basic
-- Normalización básica: lower, trim, quitar tildes, quitar puntuación,
-- colapsar espacios, remover tokens vacíos.
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
-- Tokeniza el nombre, remueve tokens cortos comunes ("de", "del", "la", "los", "y"),
-- ordena tokens alfabéticamente, y los vuelve a unir con espacio.
-- Esto permite matching cuando el orden varía (ej: "Luis Fabio Quispe" vs "Quispe Luis Fabio").
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
    SELECT array_agg(token ORDER BY token)
    INTO filtered_tokens
    FROM unnest(filtered_tokens) AS token;
    
    -- Volver a unir con espacio
    result := array_to_string(filtered_tokens, ' ');
    
    RETURN result;
END;
$$;

COMMENT ON FUNCTION ops.normalize_name_tokens_sorted IS 
'Normaliza nombre tokenizando, removiendo palabras comunes ("de", "del", etc.), ordenando tokens alfabéticamente, y uniendo. Permite matching cuando el orden varía (determinístico).';


-- Función auxiliar: Verificar que las funciones funcionan correctamente
-- (Ejemplo de uso, comentado)
/*
SELECT 
    ops.normalize_name_basic('Luis Fabio Quispe Anyosa') AS basic_1,
    ops.normalize_name_basic('Quispe Anyosa Luis Fabio') AS basic_2,
    ops.normalize_name_tokens_sorted('Luis Fabio Quispe Anyosa') AS sorted_1,
    ops.normalize_name_tokens_sorted('Quispe Anyosa Luis Fabio') AS sorted_2;
-- Debe mostrar que sorted_1 = sorted_2 pero basic_1 != basic_2
*/



