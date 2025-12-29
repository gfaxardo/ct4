-- ============================================================================
-- Script de Ingest Idempotente: Pagos Yango al Ledger
-- ============================================================================
-- Inserta snapshots de pagos Yango desde ops.v_yango_payments_raw_current_aliases
-- a ops.yango_payment_status_ledger de forma idempotente.
--
-- Usa ON CONFLICT (payment_key, state_hash) DO NOTHING para garantizar
-- que solo se inserten nuevos registros cuando cambia el estado.
--
-- Cada corrida registra snapshot_at = NOW() para todos los registros insertados.
-- ============================================================================

-- Función que ejecuta el ingest y retorna el número de filas insertadas
CREATE OR REPLACE FUNCTION ops.ingest_yango_payments_snapshot()
RETURNS INTEGER
LANGUAGE plpgsql
AS $$
DECLARE
    rows_inserted INTEGER;
    snapshot_timestamp TIMESTAMPTZ;
BEGIN
    snapshot_timestamp := NOW();
    
    -- Insertar desde raw_current al ledger
    -- ON CONFLICT garantiza idempotencia: solo inserta si cambia el estado
    INSERT INTO ops.yango_payment_status_ledger (
        snapshot_at,
        source_table,
        source_pk,
        pay_date,
        pay_time,
        raw_driver_name,
        driver_name_normalized,
        milestone_type,
        milestone_value,
        is_paid,
        paid_flag_source,
        driver_id,
        person_key,
        match_rule,
        match_confidence,
        payment_key,
        state_hash
    )
    SELECT 
        snapshot_timestamp AS snapshot_at,
        'module_ct_cabinet_payments' AS source_table,
        source_pk,
        pay_date,
        pay_time,
        raw_driver_name,
        driver_name_normalized,
        milestone_type,
        milestone_value,
        is_paid,
        paid_flag_source,
        driver_id,
        person_key,
        match_rule,
        match_confidence,
        payment_key,
        state_hash
    FROM ops.v_yango_payments_raw_current_aliases
    ON CONFLICT (payment_key, state_hash) DO NOTHING;
    
    GET DIAGNOSTICS rows_inserted = ROW_COUNT;
    
    RETURN rows_inserted;
END;
$$;

COMMENT ON FUNCTION ops.ingest_yango_payments_snapshot() IS 
'Función que ejecuta ingest idempotente de pagos Yango al ledger. Inserta desde ops.v_yango_payments_raw_current_aliases a ops.yango_payment_status_ledger. Retorna el número de filas insertadas. Solo inserta nuevos registros cuando cambia el estado (por unique constraint en payment_key, state_hash).';

-- Script directo (alternativa sin función, para ejecución manual)
-- Ejecutar directamente si prefieres no usar función:
/*
INSERT INTO ops.yango_payment_status_ledger (
    snapshot_at,
    source_table,
    source_pk,
    pay_date,
    pay_time,
    raw_driver_name,
    driver_name_normalized,
    milestone_type,
    milestone_value,
    is_paid,
    paid_flag_source,
    driver_id,
    person_key,
    match_rule,
    match_confidence,
    payment_key,
    state_hash
)
SELECT 
    NOW() AS snapshot_at,
    'module_ct_cabinet_payments' AS source_table,
    source_pk,
    pay_date,
    pay_time,
    raw_driver_name,
    driver_name_normalized,
    milestone_type,
    milestone_value,
    is_paid,
    paid_flag_source,
    driver_id,
    person_key,
    match_rule,
    match_confidence,
    payment_key,
    state_hash
FROM ops.v_yango_payments_raw_current_aliases
ON CONFLICT (payment_key, state_hash) DO NOTHING;
*/






