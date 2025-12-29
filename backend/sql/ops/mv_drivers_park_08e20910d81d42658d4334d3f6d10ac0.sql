-- ============================================================================
-- Materialized View: Drivers del Park 08e20910d81d42658d4334d3f6d10ac0
-- ============================================================================
-- Materialized view optimizada para matching por nombre, limitada a drivers
-- del park_id específico. Reduce significativamente el universo de matching
-- y mejora el performance de v_yango_payments_ledger_latest_enriched.
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

-- Índices para optimizar los JOINs en v_yango_payments_ledger_latest_enriched
CREATE UNIQUE INDEX idx_mv_drivers_park_08e20910d81d42658d4334d3f6d10ac0_driver_id 
    ON ops.mv_drivers_park_08e20910d81d42658d4334d3f6d10ac0 (driver_id);

CREATE INDEX idx_mv_drivers_park_08e20910d81d42658d4334d3f6d10ac0_full_norm 
    ON ops.mv_drivers_park_08e20910d81d42658d4334d3f6d10ac0 (driver_full_norm)
    WHERE driver_full_norm IS NOT NULL;

CREATE INDEX idx_mv_drivers_park_tokens_sorted 
    ON ops.mv_drivers_park_08e20910d81d42658d4334d3f6d10ac0 (driver_tokens_sorted)
    WHERE driver_tokens_sorted IS NOT NULL;

COMMENT ON MATERIALIZED VIEW ops.mv_drivers_park_08e20910d81d42658d4334d3f6d10ac0 IS 
'Materialized view de drivers del park_id 08e20910d81d42658d4334d3f6d10ac0 con nombres normalizados. Usada por v_yango_payments_ledger_latest_enriched para reducir el universo de matching y mejorar performance. Debe refrescarse periódicamente cuando se agreguen nuevos drivers al park.';

COMMENT ON COLUMN ops.mv_drivers_park_08e20910d81d42658d4334d3f6d10ac0.driver_full_norm IS 
'Nombre completo normalizado usando ops.normalize_name_basic(). Usado para matching por nombre completo.';

COMMENT ON COLUMN ops.mv_drivers_park_08e20910d81d42658d4334d3f6d10ac0.driver_tokens_sorted IS 
'Tokens del nombre ordenados usando ops.normalize_name_tokens_sorted(). Usado para matching por tokens (permite orden invertido).';

