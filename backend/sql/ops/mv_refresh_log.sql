-- ============================================================================
-- Tabla de tracking para refresh de materialized views
-- ============================================================================
-- Registra cada intento de refresh de MV con status, duración y errores
-- ============================================================================

CREATE TABLE IF NOT EXISTS ops.mv_refresh_log (
  id bigserial primary key,
  refreshed_at timestamptz not null default now(),
  schema_name text not null,
  mv_name text not null,
  status text not null, -- 'SUCCESS' | 'FAILED'
  duration_ms int null,
  error_message text null
);

CREATE INDEX IF NOT EXISTS idx_mv_refresh_log_mv_time
  ON ops.mv_refresh_log (schema_name, mv_name, refreshed_at desc);

COMMENT ON TABLE ops.mv_refresh_log IS 
'Log de intentos de refresh de materialized views. Registra status, duración y errores.';

COMMENT ON COLUMN ops.mv_refresh_log.refreshed_at IS 
'Timestamp del intento de refresh.';

COMMENT ON COLUMN ops.mv_refresh_log.schema_name IS 
'Schema donde reside la MV (ej: public, ops).';

COMMENT ON COLUMN ops.mv_refresh_log.mv_name IS 
'Nombre de la materialized view.';

COMMENT ON COLUMN ops.mv_refresh_log.status IS 
'Estado del refresh: SUCCESS o FAILED.';

COMMENT ON COLUMN ops.mv_refresh_log.duration_ms IS 
'Duración del refresh en milisegundos.';

COMMENT ON COLUMN ops.mv_refresh_log.error_message IS 
'Mensaje de error si status=FAILED, NULL si status=SUCCESS.';











