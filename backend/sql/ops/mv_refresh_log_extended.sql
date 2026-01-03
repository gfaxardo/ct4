-- ============================================================================
-- Extensión de ops.mv_refresh_log para soportar tracking detallado
-- ============================================================================
-- Agrega columnas para tracking de refresh con estados RUNNING/OK/ERROR
-- Mantiene compatibilidad con estructura existente (refreshed_at, status SUCCESS/FAILED)
-- ============================================================================

-- Agregar columnas nuevas si no existen
DO $$
BEGIN
    -- refresh_started_at: timestamp de inicio del refresh
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_schema = 'ops' 
        AND table_name = 'mv_refresh_log' 
        AND column_name = 'refresh_started_at'
    ) THEN
        ALTER TABLE ops.mv_refresh_log 
        ADD COLUMN refresh_started_at timestamptz;
        
        -- Migrar datos existentes: usar refreshed_at como refresh_started_at
        UPDATE ops.mv_refresh_log 
        SET refresh_started_at = refreshed_at 
        WHERE refresh_started_at IS NULL;
        
        -- Hacer NOT NULL después de migrar
        ALTER TABLE ops.mv_refresh_log 
        ALTER COLUMN refresh_started_at SET NOT NULL,
        ALTER COLUMN refresh_started_at SET DEFAULT now();
    END IF;

    -- refresh_finished_at: timestamp de fin del refresh (NULL si aún está RUNNING)
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_schema = 'ops' 
        AND table_name = 'mv_refresh_log' 
        AND column_name = 'refresh_finished_at'
    ) THEN
        ALTER TABLE ops.mv_refresh_log 
        ADD COLUMN refresh_finished_at timestamptz;
        
        -- Migrar datos existentes: usar refreshed_at como refresh_finished_at si status=SUCCESS
        UPDATE ops.mv_refresh_log 
        SET refresh_finished_at = refreshed_at 
        WHERE refresh_finished_at IS NULL AND status = 'SUCCESS';
    END IF;

    -- Actualizar status para soportar RUNNING/OK/ERROR (mantener SUCCESS/FAILED para compatibilidad)
    -- No cambiamos el tipo, solo documentamos que ahora también acepta RUNNING/OK/ERROR
    -- Los valores existentes SUCCESS/FAILED se mantienen

    -- rows_after_refresh: número de filas después del refresh
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_schema = 'ops' 
        AND table_name = 'mv_refresh_log' 
        AND column_name = 'rows_after_refresh'
    ) THEN
        ALTER TABLE ops.mv_refresh_log 
        ADD COLUMN rows_after_refresh bigint;
    END IF;

    -- host: hostname donde se ejecutó el refresh (opcional)
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_schema = 'ops' 
        AND table_name = 'mv_refresh_log' 
        AND column_name = 'host'
    ) THEN
        ALTER TABLE ops.mv_refresh_log 
        ADD COLUMN host text;
    END IF;

    -- meta: metadata adicional en JSONB (opcional)
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_schema = 'ops' 
        AND table_name = 'mv_refresh_log' 
        AND column_name = 'meta'
    ) THEN
        ALTER TABLE ops.mv_refresh_log 
        ADD COLUMN meta jsonb;
    END IF;
END $$;

-- Actualizar índice para incluir refresh_started_at si no existe
CREATE INDEX IF NOT EXISTS idx_mv_refresh_log_mv_started
  ON ops.mv_refresh_log (schema_name, mv_name, refresh_started_at DESC);

-- Comentarios
COMMENT ON COLUMN ops.mv_refresh_log.refresh_started_at IS 
'Timestamp de inicio del refresh. NOT NULL, default now().';

COMMENT ON COLUMN ops.mv_refresh_log.refresh_finished_at IS 
'Timestamp de fin del refresh. NULL si aún está RUNNING.';

COMMENT ON COLUMN ops.mv_refresh_log.status IS 
'Estado del refresh: RUNNING (en progreso), OK (completado exitosamente), ERROR (falló), SUCCESS (legacy), FAILED (legacy).';

COMMENT ON COLUMN ops.mv_refresh_log.rows_after_refresh IS 
'Número de filas en la MV después del refresh (NULL si no se pudo obtener o si falló).';

COMMENT ON COLUMN ops.mv_refresh_log.host IS 
'Hostname donde se ejecutó el refresh (opcional, para debugging distribuido).';

COMMENT ON COLUMN ops.mv_refresh_log.meta IS 
'Metadata adicional en JSONB (opcional, para información de contexto).';

