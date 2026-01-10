# Scout Attribution Fix - Reporte de Ejecución

**Fecha de ejecución**: 2026-01-09 21:27:52

## Estadísticas Antes del Fix

- **total_persons**: 2033
- **persons_with_scout**: 357
- **scouting_daily_with_links**: 609
- **scouting_daily_with_ledger_scout**: 367
- **conflicts**: 5

## Estadísticas Después del Fix

- **total_persons**: 2033
- **persons_with_scout**: 357
- **scouting_daily_with_links**: 609
- **scouting_daily_with_ledger_scout**: 367
- **conflicts**: 5

## Mejoras

- **Personas con scout satisfactorio**: +0
- **scouting_daily con lead_ledger scout**: +0

## Log de Ejecución

- **00_inventory_scout_sources**: OK - OK
- **10_create_v_scout_attribution_raw.sql**: OK - OK
- **11_create_v_scout_attribution.sql**: OK - OK
- **12_create_v_scout_attribution_conflicts.sql**: OK - OK
- **01_diagnose_scout_attribution**: OK - OK
- **22_create_backfill_audit_tables**: OK - OK
- **backfill_identity_links_scouting_daily**: OK - 
- **20_backfill_lead_ledger_attributed_scout**: OK - OK
- **21_backfill_lead_events_scout_from_cabinet_leads**: OK - OK
- **04_yango_collection_with_scout.sql**: OK - OK
- **13_create_v_scout_daily_expected_base.sql**: OK - OK
- **02_categorize_persons_without_scout.sql**: OK - OK
- **03_verify_scout_attribution_views**: OK - OK

## Warnings

- Ninguno

