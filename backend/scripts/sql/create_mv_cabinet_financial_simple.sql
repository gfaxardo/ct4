-- Crear vista materializada de forma simple (sin índices primero)

-- Verificar si ya existe
DO $$
BEGIN
    IF EXISTS (
        SELECT 1 FROM pg_matviews 
        WHERE schemaname = 'ops' 
        AND matviewname = 'mv_cabinet_financial_14d'
    ) THEN
        RAISE NOTICE 'Vista materializada ya existe, saltando creación';
    ELSE
        -- Crear sin índices primero para evitar timeout
        EXECUTE 'CREATE MATERIALIZED VIEW ops.mv_cabinet_financial_14d AS SELECT * FROM ops.v_cabinet_financial_14d';
        RAISE NOTICE 'Vista materializada creada exitosamente';
    END IF;
END $$;



