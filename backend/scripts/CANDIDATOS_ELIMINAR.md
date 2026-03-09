# Scripts eliminados (no utilizados en el sistema)

Se eliminaron los siguientes scripts que **no** estaban referenciados en docs, runbooks, cron ni por otros scripts:

## Eliminados

| Script | Motivo |
|--------|--------|
| `final_root_cause_analysis.py` | Análisis one-off, sin referencias |
| `final_explanation_selection.py` | One-off, sin referencias |
| `trace_driver_milestones.py` | Debug puntual, sin referencias |
| `get_driver_matrix_payload.py` | Solo debug, sin referencias |
| `debug_recovery_kpi_mismatch.py` | Debug puntual, sin referencias |
| `analyze_m5_without_m1_root_cause.py` | Análisis puntual, sin referencias |
| `analyze_receivable_payable_detail.py` | Análisis puntual, sin referencias |
| `analyze_unmatched_post_05.py` | Análisis puntual, sin referencias |
| `deep_investigation_drivers_without_leads.py` | Investigación puntual, sin referencias |
| `apply_driver_matrix_simple.py` | Duplicado, no referenciado en docs |
| `apply_driver_matrix_view.py` | Duplicado, no referenciado en docs |
| `fix_alembic_version.py` | Parche puntual Alembic, sin referencias |
| `fix_alembic_version_direct.py` | Parche puntual Alembic, sin referencias |
| `investigate_selection_criteria.py` | Investigación puntual, sin referencias |
| `investigate_why_only_902_drivers.py` | Investigación puntual, sin referencias |
| `investigate_drivers_without_leads.py` | Investigación puntual, sin referencias |
| `investigate_integrity_issue.py` | Investigación puntual, sin referencias |
| `analyze_limbo_root_cause.py` | Análisis puntual, sin referencias |
| `analyze_manual_review_cases.py` | Análisis puntual, sin referencias |
| `analyze_matching_logic_drivers.py` | Análisis puntual, sin referencias |
| `analyze_plate_matching_issues.py` | Análisis puntual, sin referencias |
| `analyze_no_identity_leads.py` | Análisis puntual, sin referencias |
| **apply_*** (one-off, no en runbooks ni por otros scripts) | |
| `apply_claims_gap_fix.py` | Fix one-off claims gap, sin referencias |
| `apply_claims_fix.py` | Fix one-off, sin referencias |
| `apply_final_fix.py` | Fix one-off reconcilable, sin referencias |
| `apply_identity_fields_fix.py` | Fix one-off identity, sin referencias |
| `apply_reconcilable_fix.py` | Fix one-off reconcilable, sin referencias |
| `apply_health_checks_view.py` | Aplicar vista one-off, sin referencias |
| `apply_health_global_view.py` | Aplicar vista one-off, sin referencias |
| `apply_mv_refresh_log_table.py` | Crear tabla one-off, sin referencias |
| `apply_mv_refresh_log_extended.py` | Extender tabla one-off, sin referencias |
| `apply_fix_missing_drivers.py` | Fix one-off drivers, sin referencias |
| `apply_yango_cabinet_claims_mv_health.py` | MV health one-off, sin referencias |
| `complete_fix_and_refresh.py` | Pipeline fix one-off, sin referencias |
| `check_reconcilable_results.py` | Chequeo one-off, sin referencias |
| `check_index_and_force_usage.py` | Chequeo one-off índices, sin referencias |
| `test_performance.py` | Test puntual, sin referencias |
| `test_index_performance.py` | Test puntual índices, sin referencias |

## Conservados (sí se usan)

- **`exhaustive_search_leads_for_drivers.py`** – Lo usa `create_additional_missing_links.py`.
- **`diagnose_post_05_leads.py`** – Lo referencian `fix_post_05_leads_matching.py` y `execute_matching_post_05.py`.
- **`verificar_metricas_finales.py`** – Refactorizado y en uso.
- **`investigate_category_d.py`**, **`investigate_scouting_daily_no_attribution.py`** – Refactorizados, en uso.
- **`analyze_missing_scout.py`**, **`analyze_scouting_daily_coverage.py`** – Refactorizados o referenciados en docs.

Si necesitas recuperar algún script eliminado, usa `git checkout -- backend/scripts/nombre_script.py`.
