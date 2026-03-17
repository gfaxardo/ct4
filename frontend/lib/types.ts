/**
 * Type definitions for API responses
 * These types should match the backend Pydantic schemas
 */

// Cabinet Financial 14d Types
export interface CabinetFinancialRow {
  driver_id: string;
  driver_name?: string | null;
  lead_date?: string | null;
  iso_week?: string | null;
  week_start?: string | null;
  connected_flag: boolean;
  connected_date?: string | null;
  total_trips_14d: number;
  reached_m1_14d: boolean;
  reached_m5_14d: boolean;
  reached_m25_14d: boolean;
  expected_amount_m1: number;
  expected_amount_m5: number;
  expected_amount_m25: number;
  expected_total_yango: number;
  claim_m1_exists: boolean;
  claim_m1_paid: boolean;
  claim_m5_exists: boolean;
  claim_m5_paid: boolean;
  claim_m25_exists: boolean;
  claim_m25_paid: boolean;
  paid_amount_m1: number;
  paid_amount_m5: number;
  paid_amount_m25: number;
  total_paid_yango: number;
  amount_due_yango: number;
  scout_id?: number | null;
  scout_name?: string | null;
  scout_quality_bucket?: string | null;
  is_scout_resolved: boolean;
  scout_source_table?: string | null;
  scout_attribution_date?: string | null;
  scout_priority?: number | null;
  person_key?: string | null;
}

export interface CabinetFinancialSummary {
  total_drivers: number;
  drivers_with_expected: number;
  drivers_with_debt: number;
  total_expected_yango: number;
  total_paid_yango: number;
  total_debt_yango: number;
  collection_percentage: number;
  drivers_m1: number;
  drivers_m5: number;
  drivers_m25: number;
  drivers_with_scout: number;
  drivers_without_scout: number;
  pct_with_scout: number;
}

export interface CabinetFinancialSummaryTotal {
  total_drivers: number;
  drivers_with_expected: number;
  drivers_with_debt: number;
  total_expected_yango: number;
  total_paid_yango: number;
  total_debt_yango: number;
  collection_percentage: number;
  drivers_m1: number;
  drivers_m5: number;
  drivers_m25: number;
  drivers_with_scout: number;
  drivers_without_scout: number;
  pct_with_scout: number;
}

export interface CabinetFinancialMeta {
  limit: number;
  offset: number;
  returned: number;
  total: number;
}

export interface CabinetFinancialResponse {
  meta: CabinetFinancialMeta;
  summary?: CabinetFinancialSummary | null;
  summary_total?: CabinetFinancialSummaryTotal | null;
  data: CabinetFinancialRow[];
}

// Cabinet Limbo Types
export interface CabinetLimboRow {
  lead_id: number;
  lead_source_pk: string;
  lead_date: string;
  week_start: string;
  park_phone?: string | null;
  asset_plate_number?: string | null;
  lead_name?: string | null;
  person_key?: string | null;
  driver_id?: string | null;
  trips_14d: number;
  window_end_14d: string;
  reached_m1_14d: boolean;
  reached_m5_14d: boolean;
  reached_m25_14d: boolean;
  expected_amount_14d: number;
  has_claim_m1: boolean;
  has_claim_m5: boolean;
  has_claim_m25: boolean;
  limbo_stage: 'NO_IDENTITY' | 'NO_DRIVER' | 'NO_TRIPS_14D' | 'TRIPS_NO_CLAIM' | 'OK';
  limbo_reason_detail: string;
}

export interface CabinetLimboSummary {
  total_leads: number;
  limbo_no_identity: number;
  limbo_no_driver: number;
  limbo_no_trips_14d: number;
  limbo_trips_no_claim: number;
  limbo_ok: number;
}

export interface CabinetLimboMeta {
  limit: number;
  offset: number;
  returned: number;
  total: number;
}

export interface CabinetLimboResponse {
  meta: CabinetLimboMeta;
  summary: CabinetLimboSummary;
  data: CabinetLimboRow[];
}

// Cabinet Claims Gap Types
export interface CabinetClaimsGapRow {
  lead_id: number;
  lead_source_pk: string;
  driver_id?: string | null;
  person_key?: string | null;
  lead_date: string;
  week_start: string;
  milestone_value: number;
  trips_14d: number;
  milestone_achieved: boolean;
  expected_amount: number;
  claim_expected: boolean;
  claim_exists: boolean;
  claim_status: 'MISSING' | 'EXISTS' | 'INVALID';
  gap_reason: string;
}

export interface CabinetClaimsGapSummary {
  total_gaps: number;
  gaps_milestone_achieved_no_claim: number;
  gaps_claim_exists: number;
  gaps_milestone_not_achieved: number;
  gaps_m1: number;
  gaps_m5: number;
  gaps_m25: number;
  total_expected_amount: number;
}

export interface CabinetClaimsGapMeta {
  limit: number;
  offset: number;
  returned: number;
  total: number;
}

export interface CabinetClaimsGapResponse {
  meta: CabinetClaimsGapMeta;
  summary: CabinetClaimsGapSummary;
  data: CabinetClaimsGapRow[];
}

// Dashboard Scout / Yango (scout summary, open items)
export interface ScoutTotals {
  payable_amount: number;
  payable_items: number;
  payable_drivers: number;
  payable_scouts: number;
  blocked_amount: number;
  blocked_items: number;
}

export interface ScoutByWeek {
  week_start_monday: string;
  iso_year_week: string;
  payable_amount: number;
  payable_items: number;
  blocked_amount: number;
  blocked_items: number;
}

export interface TopScout {
  acquisition_scout_id?: number | null;
  acquisition_scout_name?: string | null;
  amount: number;
  items: number;
  drivers: number;
}

export interface ScoutSummaryResponse {
  totals: ScoutTotals;
  by_week: ScoutByWeek[];
  top_scouts: TopScout[];
}

export interface ScoutOpenItem {
  payment_item_key: string;
  person_key: string;
  lead_origin?: string | null;
  scout_id?: number | null;
  acquisition_scout_id?: number | null;
  acquisition_scout_name?: string | null;
  attribution_confidence?: string | null;
  attribution_rule?: string | null;
  milestone_type?: string | null;
  milestone_value?: number | null;
  payable_date?: string | null;
  achieved_date?: string | null;
  amount: number;
  currency?: string | null;
  driver_id?: string | null;
}

export interface ScoutOpenItemsResponse {
  items: ScoutOpenItem[];
  total: number;
  limit: number;
  offset: number;
}

export interface YangoTotals {
  receivable_amount: number;
  receivable_items: number;
  receivable_drivers: number;
}

export interface YangoByWeek {
  week_start_monday: string;
  iso_year_week: string;
  amount: number;
  items: number;
  drivers: number;
}

export interface YangoSummaryResponse {
  totals: YangoTotals;
  by_week: YangoByWeek[];
}

export interface YangoReceivableItem {
  pay_week_start_monday: string;
  pay_iso_year_week: string;
  payable_date: string;
  achieved_date?: string | null;
  lead_date?: string | null;
  lead_origin?: string | null;
  payer: string;
  milestone_type?: string | null;
  milestone_value?: number | null;
  window_days?: number | null;
  trips_in_window?: number | null;
  person_key: string;
  driver_id?: string | null;
  amount: number;
  currency?: string | null;
  created_at_export?: string | null;
}

export interface YangoReceivableItemsResponse {
  items: YangoReceivableItem[];
  total: number;
  limit: number;
  offset: number;
}

// Payment Eligibility
export interface PaymentEligibilityRow {
  person_key?: string | null;
  origin_tag?: string | null;
  scout_id?: number | null;
  driver_id?: string | null;
  lead_date?: string | null;
  rule_id?: number | null;
  rule_scope?: string | null;
  milestone_trips?: number | null;
  window_days?: number | null;
  currency?: string | null;
  amount?: number | null;
  rule_valid_from?: string | null;
  rule_valid_to?: string | null;
  milestone_achieved?: boolean | null;
  achieved_date?: string | null;
  achieved_trips_in_window?: number | null;
  is_payable?: boolean | null;
  payable_date?: string | null;
  payment_scheme?: string | null;
}

export interface PaymentEligibilityResponse {
  status: string;
  count: number;
  filters: Record<string, unknown>;
  rows: PaymentEligibilityRow[];
}

// Driver Matrix (Ops)
export interface DriverMatrixRow {
  driver_id?: string | null;
  person_key?: string | null;
  driver_name?: string | null;
  lead_date?: string | null;
  week_start?: string | null;
  origin_tag?: string | null;
  funnel_status?: string | null;
  highest_milestone?: number | null;
  connected_flag?: boolean | null;
  connected_date?: string | null;
  m1_achieved_flag?: boolean | null;
  m1_achieved_date?: string | null;
  m1_expected_amount_yango?: number | null;
  m1_yango_payment_status?: string | null;
  m1_window_status?: string | null;
  m1_overdue_days?: number | null;
  m5_achieved_flag?: boolean | null;
  m5_achieved_date?: string | null;
  m5_expected_amount_yango?: number | null;
  m5_yango_payment_status?: string | null;
  m5_window_status?: string | null;
  m5_overdue_days?: number | null;
  m25_achieved_flag?: boolean | null;
  m25_achieved_date?: string | null;
  m25_expected_amount_yango?: number | null;
  m25_yango_payment_status?: string | null;
  m25_window_status?: string | null;
  m25_overdue_days?: number | null;
  scout_due_flag?: boolean | null;
  scout_paid_flag?: boolean | null;
  scout_amount?: number | null;
  scout_id?: number | null;
  scout_name?: string | null;
  scout_quality_bucket?: string | null;
  is_scout_resolved: boolean;
  m5_without_m1_flag?: boolean | null;
  m25_without_m5_flag?: boolean | null;
  milestone_inconsistency_notes?: string | null;
  connection_within_14d_flag?: boolean | null;
  connection_date_within_14d?: string | null;
  trips_completed_14d_from_lead?: number | null;
  first_trip_date_within_14d?: string | null;
}

export interface OpsDriverMatrixMeta {
  limit: number;
  offset: number;
  returned: number;
  total: number;
}

export interface OpsDriverMatrixResponse {
  meta: OpsDriverMatrixMeta;
  data: DriverMatrixRow[];
}

// Driver Matrix (formato rows/meta/totals, usado por resumen-conductor)
export interface DriverMatrixTotals {
  drivers: number;
  expected_yango_sum: number;
  paid_sum: number;
  receivable_sum: number;
  expired_count: number;
  in_window_count: number;
  achieved_m1_count?: number;
  achieved_m5_count?: number;
  achieved_m25_count?: number;
  achieved_m1_without_claim_count?: number;
  achieved_m5_without_claim_count?: number;
  achieved_m25_without_claim_count?: number;
}

export interface DriverMatrixMeta {
  page: number;
  limit: number;
  total_rows: number;
}

export interface DriverMatrixResponse {
  rows: DriverMatrixRow[];
  meta: DriverMatrixMeta;
  totals: DriverMatrixTotals;
}

// Yango Reconciliation Summary
export interface YangoReconciliationSummaryRow {
  pay_week_start_monday: string;
  milestone_value: number;
  amount_expected_sum: number;
  amount_paid_confirmed_sum: number;
  amount_paid_enriched_sum: number;
  amount_paid_total_visible: number;
  amount_pending_active_sum: number;
  amount_pending_expired_sum: number;
  amount_diff: number;
  amount_diff_assumed: number;
  anomalies_total: number;
  count_expected: number;
  count_paid_confirmed: number;
  count_paid_enriched: number;
  count_paid: number;
  count_pending_active: number;
  count_pending_expired: number;
  count_drivers: number;
  amount_paid_sum?: number | null;
  amount_paid_assumed?: number | null;
}

export interface YangoReconciliationSummaryResponse {
  status: string;
  count: number;
  filters: Record<string, unknown>;
  rows: YangoReconciliationSummaryRow[];
}

// Yango Reconciliation Items
export interface YangoReconciliationItemRow {
  driver_id?: string | null;
  person_key?: string | null;
  lead_date?: string | null;
  pay_week_start_monday?: string | null;
  milestone_value?: number | null;
  expected_amount?: number | null;
  currency?: string | null;
  due_date?: string | null;
  window_status?: string | null;
  paid_payment_key?: string | null;
  paid_payment_key_confirmed?: string | null;
  paid_payment_key_enriched?: string | null;
  paid_date?: string | null;
  paid_date_confirmed?: string | null;
  paid_date_enriched?: string | null;
  is_paid_effective?: boolean | null;
  match_method?: string | null;
  paid_status?: string | null;
  identity_status?: string | null;
  match_rule?: string | null;
  match_confidence?: string | null;
}

export interface YangoReconciliationItemsResponse {
  status: string;
  count: number;
  total: number;
  filters: Record<string, unknown>;
  rows: YangoReconciliationItemRow[];
}

export interface YangoLedgerUnmatchedRow {
  payment_key: string;
  pay_date?: string | null;
  is_paid?: boolean | null;
  milestone_value?: number | null;
  driver_id?: string | null;
  person_key?: string | null;
  raw_driver_name?: string | null;
  driver_name_normalized?: string | null;
  match_rule?: string | null;
  match_confidence?: string | null;
  latest_snapshot_at?: string | null;
  source_pk?: string | null;
  identity_source?: string | null;
  identity_enriched?: string | null;
  driver_id_final?: string | null;
  person_key_final?: string | null;
  identity_status?: string | null;
}

export interface YangoLedgerUnmatchedResponse {
  status: string;
  count: number;
  total: number;
  filters: Record<string, unknown>;
  rows: YangoLedgerUnmatchedRow[];
}

export interface YangoDriverDetailClaimRow {
  milestone_value?: number | null;
  expected_amount?: number | null;
  currency?: string | null;
  lead_date?: string | null;
  due_date?: string | null;
  pay_week_start_monday?: string | null;
  paid_status?: string | null;
  paid_payment_key?: string | null;
  paid_date?: string | null;
  is_paid_effective?: boolean | null;
  match_method?: string | null;
  identity_status?: string | null;
  match_rule?: string | null;
  match_confidence?: string | null;
}

export interface YangoDriverDetailResponse {
  status: string;
  driver_id: string;
  person_key?: string | null;
  claims: YangoDriverDetailClaimRow[];
  summary: Record<string, unknown>;
}

// Cabinet Milestones Reconciliation
export interface CabinetReconciliationRow {
  driver_id?: string | null;
  milestone_value?: number | null;
  achieved_flag?: boolean | null;
  achieved_person_key?: string | null;
  achieved_lead_date?: string | null;
  achieved_date?: string | null;
  achieved_trips_in_window?: number | null;
  window_days?: number | null;
  expected_amount?: number | null;
  achieved_currency?: string | null;
  rule_id?: number | null;
  paid_flag?: boolean | null;
  paid_person_key?: string | null;
  pay_date?: string | null;
  payment_key?: string | null;
  identity_status?: string | null;
  match_rule?: string | null;
  match_confidence?: string | null;
  latest_snapshot_at?: string | null;
  reconciliation_status?: string | null;
}

export interface CabinetReconciliationResponse {
  status: string;
  count: number;
  total: number;
  filters: Record<string, unknown>;
  rows: CabinetReconciliationRow[];
}

export interface FunnelGapMetrics {
  total_leads?: number;
  leads_with_identity?: number;
  leads_with_claims?: number;
  leads_without_identity?: number;
  leads_without_claims?: number;
  leads_without_both?: number;
  percentages?: Record<string, number>;
}

export interface CabinetLeadsDiagnostics {
  table_exists?: boolean;
  table_row_count?: number;
  max_lead_date_in_table?: string | null;
  max_event_date_in_lead_events?: string | null;
  max_snapshot_date_in_identity_links?: string | null;
  recommended_start_date?: string | null;
  processed_external_ids_count?: number;
}

// Yango Cabinet Claims
export interface YangoCabinetClaimRow {
  claim_key?: string | null;
  person_key?: string | null;
  driver_id?: string | null;
  driver_name?: string | null;
  milestone_value?: number | null;
  lead_date?: string | null;
  expected_amount?: number | null;
  yango_due_date?: string | null;
  days_overdue_yango?: number | null;
  overdue_bucket_yango?: string | null;
  yango_payment_status?: string | null;
  reason_code?: string | null;
  identity_status?: string | null;
  match_rule?: string | null;
  match_confidence?: string | null;
  is_reconcilable_enriched?: boolean | null;
  payment_key?: string | null;
  pay_date?: string | null;
  suggested_driver_id?: string | null;
}

export interface YangoCabinetClaimsResponse {
  status: string;
  count: number;
  total: number;
  filters: Record<string, unknown>;
  rows: YangoCabinetClaimRow[];
}

export interface CabinetRecoveryImpactTotals {
  total_leads: number;
  unidentified_count: number;
  identified_no_origin_count: number;
  recovered_within_14d_count: number;
  recovered_late_count: number;
  recovered_within_14d_and_claim_count: number;
  still_unidentified_count: number;
  identified_but_missing_origin_count: number;
  identified_origin_no_claim_count: number;
}

export interface CabinetRecoveryImpactSeriesItem {
  date?: string;
  event_date?: string;
  unidentified?: number;
  recovered_within_14d?: number;
  recovered_late?: number;
  claims?: number;
}

export interface CabinetRecoveryImpactResponse {
  totals: CabinetRecoveryImpactTotals;
  series?: CabinetRecoveryImpactSeriesItem[] | null;
  top_reasons?: Record<string, number> | null;
}

export interface LeadCabinetInfo {
  source_pk?: string | null;
  match_rule?: string | null;
  match_score?: number | null;
  confidence_level?: string | null;
  linked_at?: string | null;
}

export interface PaymentInfo {
  payment_key?: string | null;
  pay_date?: string | null;
  milestone_value?: number | null;
  identity_status?: string | null;
  match_rule?: string | null;
}

export interface ReconciliationInfo {
  reconciliation_status?: string | null;
  expected_amount?: number | null;
  paid_payment_key?: string | null;
  paid_date?: string | null;
  match_method?: string | null;
}

export interface YangoCabinetClaimDrilldownResponse {
  status: string;
  claim?: YangoCabinetClaimRow | null;
  lead_cabinet?: LeadCabinetInfo | null;
  payment_exact?: PaymentInfo | null;
  payments_other_milestones?: PaymentInfo[];
  reconciliation?: ReconciliationInfo | null;
  misapplied_explanation?: string | null;
}

// Identity runs (auditoría)
export type IngestionRunStatus = 'RUNNING' | 'COMPLETED' | 'FAILED';
export type IngestionJobType = 'identity_run' | 'drivers_index_refresh';

export interface IdentityRunStatsSource {
  processed?: number | null;
  matched?: number | null;
  unmatched?: number | null;
  skipped?: number | null;
}

export interface IdentityRunStats {
  cabinet_leads?: IdentityRunStatsSource | null;
  scouting_daily?: IdentityRunStatsSource | null;
  timings?: Record<string, number> | null;
  raw?: Record<string, unknown> | null;
}

export interface IdentityRunRow {
  id: number;
  started_at: string;
  completed_at?: string | null;
  status: IngestionRunStatus;
  job_type: IngestionJobType;
  scope_date_from?: string | null;
  scope_date_to?: string | null;
  incremental: boolean;
  error_message?: string | null;
  stats?: IdentityRunStats | null;
}

export interface IdentityRunsResponse {
  items: IdentityRunRow[];
  total: number;
  limit: number;
  offset: number;
}

// Scout Attribution (health, backlog, job status)
export interface ScoutAttributionMetrics {
  total_persons?: number | null;
  persons_with_scout_satisfactory?: number | null;
  pct_scout_satisfactory?: number | null;
  persons_missing_scout?: number | null;
  conflicts_count?: number | null;
  backlog?: {
    a_events_without_scout?: number | null;
    d_scout_in_events_not_in_ledger?: number | null;
    c_legacy?: number | null;
  } | null;
  last_job?: {
    status?: string | null;
    ended_at?: string | null;
    started_at?: string | null;
    duration_seconds?: number | null;
    summary?: string | null;
    error?: string | null;
  } | null;
  snapshot_timestamp?: string | null;
}

export interface ScoutAttributionMetricsDaily {
  daily_metrics?: Array<{
    date?: string | null;
    total_persons?: number | null;
    satisfactory_count?: number | null;
    pct_satisfactory?: number | null;
    missing_count?: number | null;
    by_source?: Record<string, unknown> | null;
  }> | null;
}

export interface ScoutAttributionBacklogResponse {
  backlog?: Array<{
    person_key?: string | null;
    category?: string | null;
    category_label?: string | null;
    scout_id?: number | null;
    source_tables?: string | string[] | null;
    origin_tags?: string | null;
    first_event_date?: string | null;
    last_event_date?: string | null;
    event_count?: number | null;
  }> | null;
  pagination?: {
    page?: number;
    page_size?: number;
    total?: number;
    total_pages?: number;
  } | null;
}

export interface ScoutAttributionJobStatus {
  last_run?: {
    run_id?: number | null;
    status?: string | null;
    started_at?: string | null;
    ended_at?: string | null;
    duration_seconds?: number | null;
    summary?: unknown;
    error?: string | null;
  } | null;
  status?: string | null;
}

export interface ScoutLiquidationBaseResponse {
  items?: unknown[];
  pagination?: { page?: number; page_size?: number; total?: number; total_pages?: number } | null;
}

export interface YangoCollectionWithScoutResponse {
  items?: unknown[];
  pagination?: { page?: number; page_size?: number; total?: number; total_pages?: number } | null;
}

export interface HealthCheckRow {
  check_key: string;
  severity: string;
  status: string;
  message: string;
  drilldown_url?: string | null;
  last_evaluated_at?: string | null;
}

export interface HealthChecksResponse {
  items: HealthCheckRow[];
}

export interface MvHealthRow {
  schema_name: string;
  mv_name: string;
  is_populated?: boolean | null;
  size_mb: number;
  last_refresh_at?: string | null;
  minutes_since_refresh?: number | null;
  last_refresh_status?: string | null;
  last_refresh_error?: string | null;
  calculated_at?: string | null;
}

export interface MvHealthResponse {
  items: MvHealthRow[];
  total: number;
  limit: number;
  offset: number;
}

export interface RawDataHealthStatusRow {
  source_name: string;
  source_type?: string | null;
  max_business_date?: string | null;
  business_days_lag?: number | null;
  max_ingestion_ts?: string | null;
  ingestion_lag_interval?: string | null;
  rows_business_yesterday?: number | null;
  rows_business_today?: number | null;
  rows_ingested_yesterday?: number | null;
  rows_ingested_today?: number | null;
  health_status?: string | null;
}

export interface RawDataHealthStatusResponse {
  items: RawDataHealthStatusRow[];
  total: number;
  limit: number;
  offset: number;
}

export interface RawDataFreshnessStatusRow {
  source_name: string;
  max_business_date?: string | null;
  business_days_lag?: number | null;
  max_ingestion_ts?: string | null;
  ingestion_lag_interval?: string | null;
  rows_business_yesterday?: number | null;
  rows_business_today?: number | null;
  rows_ingested_yesterday?: number | null;
  rows_ingested_today?: number | null;
}

export interface RawDataFreshnessStatusResponse {
  items: RawDataFreshnessStatusRow[];
  total: number;
  limit: number;
  offset: number;
}

export interface RawDataIngestionDailyRow {
  source_name: string;
  metric_type: string;
  metric_date: string;
  rows_count: number;
}

export interface RawDataIngestionDailyResponse {
  items: RawDataIngestionDailyRow[];
  total: number;
  limit: number;
  offset: number;
}

export interface ScoutAttributionConflictsResponse {
  conflicts?: Array<{
    person_key?: string | null;
    distinct_scout_count?: number | null;
    scout_ids?: unknown;
    sources?: unknown;
    origin_tags?: string | null;
    first_event_date?: string | null;
    last_event_date?: string | null;
    total_sources?: number | null;
  }> | null;
  pagination?: {
    page?: number;
    page_size?: number;
    total?: number;
    total_pages?: number;
  } | null;
}

// Types defined in api.ts - re-export from api for consumers that import from types
export type {
  IdentityGapResponse,
  IdentityGapAlertsResponse,
} from './api';

// Placeholder types (api imports from types; define here to avoid circular re-export)
export interface IdentityStats {
  total_persons?: number;
  total_unmatched?: number;
  conversion_rate?: number;
}
export type IdentityRegistry = Record<string, unknown>;
export interface IdentityLinkRow {
  id: number;
  person_key: string;
  source_table: string;
  source_pk: string;
  snapshot_date: string;
  match_rule: string;
  match_score: number;
  confidence_level: string;
  evidence?: Record<string, unknown> | null;
  linked_at: string;
  run_id?: number | null;
}
export interface PersonDetail {
  person?: IdentityRegistry;
  links: IdentityLinkRow[];
  driver_links?: IdentityLinkRow[] | null;
  has_driver_conversion?: boolean;
}
export type IdentityUnmatched = Record<string, unknown>;
export type UnmatchedResolveRequest = Record<string, unknown>;
export type UnmatchedResolveResponse = Record<string, unknown>;
export interface MetricsResponse {
  breakdowns?: {
    matched_by_rule?: Record<string, number>;
    unmatched_by_reason?: Record<string, number>;
  };
  weekly?: Array<{ week_label?: string; source_table?: string; matched?: number; unmatched?: number; match_rate?: number }>;
}
export type RunReportResponse = Record<string, unknown>;
export interface OpsAlertRow {
  id: number;
  created_at: string;
  alert_type: string;
  severity: string;
  message: string;
  week_label?: string | null;
  details?: Record<string, unknown> | null;
  run_id?: number | null;
  acknowledged_at?: string | null;
  acknowledged?: boolean;
}
export interface OpsAlertsResponse {
  items: OpsAlertRow[];
  total: number;
  limit: number;
  offset: number;
}
export type AlertSeverity = string;
export type IdentitySystemHealthRow = Record<string, unknown>;
export type HealthGlobalResponse = Record<string, unknown>;
export interface PersonsBySourceResponse {
  links_by_source?: Record<string, number> | null;
  persons_with_cabinet_leads?: number | null;
  persons_with_scouting_daily?: number | null;
  persons_with_drivers?: number | null;
  persons_only_drivers?: number | null;
  persons_with_cabinet_or_scouting?: number | null;
  total_persons?: number | null;
}
export interface DriversWithoutLeadsAnalysis {
  total_drivers_without_leads?: number;
  drivers_quarantined_count?: number;
  drivers_without_leads_operativos?: number;
  drivers_with_lead_events?: number;
  quarantine_breakdown?: Record<string, number> | null;
}
export type OrphanDriver = Record<string, unknown>;
export type OrphansListResponse = Record<string, unknown>;
export type OrphansMetricsResponse = Record<string, unknown>;
export type RunFixResponse = Record<string, unknown>;
/** Métricas de atribución scout del endpoint cobranza-yango (drivers, no persons). */
export interface CobranzaScoutAttributionMetrics {
  total_drivers?: number;
  drivers_with_scout?: number;
  drivers_without_scout?: number;
  pct_with_scout?: number;
  breakdown_by_quality?: Record<string, number>;
  breakdown_by_source?: Record<string, number>;
  drivers_without_scout_by_reason?: Record<string, number>;
  top_missing_examples?: unknown[];
}
export interface ScoutAttributionMetricsResponse {
  status?: string;
  metrics: CobranzaScoutAttributionMetrics;
  filters?: Record<string, unknown>;
}
export interface WeeklyKpiRow {
  week_start: string;
  total_rows: number;
  debt_sum?: number;
  with_scout?: number;
  pct_with_scout?: number;
  reached_m1?: number;
  reached_m5?: number;
  reached_m25?: number;
  paid_sum?: number;
  unpaid_sum?: number;
}
export interface WeeklyKpisResponse {
  status?: string;
  weeks: WeeklyKpiRow[];
  filters?: Record<string, unknown>;
}
