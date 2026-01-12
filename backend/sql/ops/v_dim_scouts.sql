-- ============================================================================
-- VISTA: ops.v_dim_scouts
-- ============================================================================
-- Propósito: Dimensión de scouts para enriquecer atribuciones con nombres
-- Fuente: public.module_ct_scouts_list (si existe) o tabla equivalente
-- Ejecución: Idempotente (DROP + CREATE)
-- ============================================================================

DROP VIEW IF EXISTS ops.v_dim_scouts CASCADE;

-- Verificar si existe la tabla module_ct_scouts_list
DO $$
BEGIN
    IF EXISTS (
        SELECT 1 FROM information_schema.tables 
        WHERE table_schema = 'public' 
        AND table_name = 'module_ct_scouts_list'
    ) THEN
        -- Crear vista desde module_ct_scouts_list
        EXECUTE '
        CREATE VIEW ops.v_dim_scouts AS
        SELECT DISTINCT
            scout_id,
            COALESCE(raw_name, name, ''Scout '' || scout_id::TEXT) AS raw_name,
            COALESCE(name, raw_name, ''Scout '' || scout_id::TEXT) AS scout_name_normalized,
            COALESCE(is_active, true) AS is_active,
            created_at,
            updated_at
        FROM public.module_ct_scouts_list
        WHERE scout_id IS NOT NULL;
        ';
    ELSE
        -- Crear vista vacía si no existe la tabla
        EXECUTE '
        CREATE VIEW ops.v_dim_scouts AS
        SELECT 
            NULL::INTEGER AS scout_id,
            NULL::TEXT AS raw_name,
            NULL::TEXT AS scout_name_normalized,
            NULL::BOOLEAN AS is_active,
            NULL::TIMESTAMP AS created_at,
            NULL::TIMESTAMP AS updated_at
        WHERE false;
        ';
    END IF;
END $$;

COMMENT ON VIEW ops.v_dim_scouts IS 
'Vista dimensión de scouts para enriquecer atribuciones con nombres. Fuente: public.module_ct_scouts_list (si existe). Si la tabla no existe, retorna vista vacía.';

COMMENT ON COLUMN ops.v_dim_scouts.scout_id IS 
'ID del scout (PK).';

COMMENT ON COLUMN ops.v_dim_scouts.raw_name IS 
'Nombre crudo del scout desde la tabla fuente.';

COMMENT ON COLUMN ops.v_dim_scouts.scout_name_normalized IS 
'Nombre normalizado del scout (para display).';
