-- ============================================================================
-- Vistas Enriquecidas de Liquidación con Atribución
-- ============================================================================
-- Vistas de liquidación enriquecidas con información de atribución de scouts
-- desde ops.v_attribution_canonical
-- ============================================================================

-- ============================================================================
-- 1) Vista: ops.v_scout_liquidation_open_items_enriched
-- ============================================================================
-- Vista enriquecida de items abiertos con información de atribución
-- Usa la vista base para evitar duplicados de columnas
CREATE OR REPLACE VIEW ops.v_scout_liquidation_open_items_enriched AS
SELECT
    base.payment_item_key,
    base.rule_id,
    base.scout_id,
    base.person_key,
    base.driver_id,
    base.lead_origin,
    base.milestone_type,
    base.milestone_value,
    base.payable_date,
    base.achieved_date,
    base.amount,
    base.currency,
    -- Columnas de atribución
    a.acquisition_scout_id,
    a.acquisition_scout_name,
    a.attribution_confidence,
    a.attribution_rule
FROM ops.v_scout_payable_items_base base
LEFT JOIN ops.scout_liquidation_ledger ledger
    ON ledger.payment_item_key = base.payment_item_key
LEFT JOIN ops.v_attribution_canonical a
    ON a.person_key = base.person_key
WHERE ledger.payment_item_key IS NULL
ORDER BY base.payable_date DESC, base.scout_id, base.person_key;

COMMENT ON VIEW ops.v_scout_liquidation_open_items_enriched IS 
'Vista enriquecida de items scout abiertos con información de atribución. Incluye acquisition_scout_id, acquisition_scout_name, attribution_confidence y attribution_rule desde ops.v_attribution_canonical.';

-- ============================================================================
-- 2) Vista: ops.v_scout_liquidation_open_items_payable_policy
-- ============================================================================
-- Vista de items abiertos filtrados por política de atribución (high/medium confidence)
CREATE OR REPLACE VIEW ops.v_scout_liquidation_open_items_payable_policy AS
SELECT *
FROM ops.v_scout_liquidation_open_items_enriched
WHERE attribution_confidence IN ('high', 'medium');

COMMENT ON VIEW ops.v_scout_liquidation_open_items_payable_policy IS 
'Vista de items scout abiertos filtrados por política de atribución. Solo incluye items con attribution_confidence IN (high, medium). Excluye items con confidence unknown.';

-- ============================================================================
-- 3) Vista: ops.v_scout_liquidation_payable_detail_enriched
-- ============================================================================
-- Vista enriquecida de detalle de liquidación payable con información de atribución
CREATE OR REPLACE VIEW ops.v_scout_liquidation_payable_detail_enriched AS
SELECT
    d.*,
    a.acquisition_scout_id,
    a.acquisition_scout_name,
    a.attribution_confidence,
    a.attribution_rule
FROM ops.v_scout_liquidation_payable_detail d
LEFT JOIN ops.v_attribution_canonical a
    ON a.person_key = d.person_key;

COMMENT ON VIEW ops.v_scout_liquidation_payable_detail_enriched IS 
'Vista enriquecida de detalle de liquidación scout payable con información de atribución. Incluye acquisition_scout_id, acquisition_scout_name, attribution_confidence y attribution_rule desde ops.v_attribution_canonical.';

