/**
 * Tipos TypeScript basados en FRONTEND_BACKEND_CONTRACT_v1.md
 * 
 * REGLA: NO inventar campos. Todos los tipos vienen del contrato.
 */

// ============================================================================
// Identity Types
// ============================================================================

export type ConfidenceLevel = 'HIGH' | 'MEDIUM' | 'LOW';

export interface IdentityStats {
  total_persons: number;
  total_unmatched: number;
  total_links: number;
  drivers_links: number;
  conversion_rate: number;
}

export interface PersonsBySourceResponse {
  total_persons: number;
  links_by_source: Record<string, number>;
  persons_with_cabinet_leads: number;
  persons_with_scouting_daily: number;
  persons_with_drivers: number;
  persons_only_drivers: number;
  persons_with_cabinet_or_scouting: number;
}

export interface DriversWithoutLeadsAnalysis {
  total_drivers_without_leads: number;
  by_match_rule: Record<string, number>;
  drivers_with_lead_events: number;
  drivers_without_lead_events: number;
  missing_links_by_source: Record<string, number>;
  sample_drivers: Array<{
    driver_id: string;
    match_rule: string;
    linked_at: string | null;
    phone: string | null;
    license: string | null;
    name: string | null;
    lead_events_count: number;
    evidence: Record<string, any> | null;
  }>;
}

export interface IdentityRegistry {
  person_key: string;
  confidence_level: ConfidenceLevel;
  primary_phone: string | null;
  primary_document: string | null;
  primary_license: string | null;
  primary_full_name: string | null;
  flags: Record<string, any> | null;
  created_at: string;
  updated_at: string;
}

export interface IdentityLink {
  id: number;
  person_key: string;
  source_table: string;
  source_pk: string;
  snapshot_date: string;
  match_rule: string;
  match_score: number;
  confidence_level: ConfidenceLevel;
  evidence: Record<string, any> | null;
  linked_at: string;
  run_id: number | null;
}

export interface PersonDetail {
  person: IdentityRegistry;
  links: IdentityLink[];
  driver_links: IdentityLink[];
  has_driver_conversion: boolean;
}

export interface IdentityUnmatched {
  id: number;
  source_table: string;
  source_pk: string;
  snapshot_date: string;
  reason_code: string;
  details: Record<string, any> | null;
  candidates_preview: Record<string, any> | null;
  status: 'OPEN' | 'RESOLVED';
  created_at: string;
  resolved_at: string | null;
  run_id: number | null;
}

export interface UnmatchedResolveRequest {
  person_key: string;
}

export interface UnmatchedResolveResponse {
  message: string;
  link_id: number;
}

// ============================================================================
// Metrics Types
// ============================================================================

export interface MetricsScope {
  run_id: number | null;
  source_table: string | null;
  event_date_from: string | null;
  event_date_to: string | null;
  mode: 'summary' | 'weekly' | 'breakdowns';
}

export interface MetricsTotals {
  total_processed: number;
  matched: number;
  unmatched: number;
  match_rate: number;
}

export interface WeeklyData {
  week_start: string;
  week_label: string;
  source_table: string;
  matched: number;
  unmatched: number;
  processed_total: number;
  match_rate: number;
  matched_by_rule: Record<string, number>;
  matched_by_confidence: Record<string, number>;
  unmatched_by_reason: Record<string, number>;
  top_missing_keys: Array<{ key: string; count: number }>;
}

export interface WeeklyTrend {
  week_label: string;
  source_table: string | null;
  delta_match_rate: number | null;
  delta_matched: number | null;
  delta_unmatched: number | null;
  current_match_rate: number;
  previous_match_rate: number | null;
}

export interface MetricsResponse {
  scope: MetricsScope;
  totals: MetricsTotals;
  weekly?: WeeklyData[];
  weekly_trend?: WeeklyTrend[];
  available_event_weeks?: string[];
  breakdowns?: {
    matched_by_rule: Record<string, number>;
    matched_by_confidence: Record<string, number>;
    unmatched_by_reason: Record<string, number>;
  };
}

// ============================================================================
// Run Report Types
// ============================================================================

export interface IngestionRun {
  id: number;
  status: 'RUNNING' | 'COMPLETED' | 'FAILED';
  started_at: string | null;
  completed_at: string | null;
  scope_date_from: string | null;
  scope_date_to: string | null;
  incremental: boolean;
}

// ============================================================================
// Identity Runs Types (Listado)
// ============================================================================

export type IngestionRunStatus = 'RUNNING' | 'COMPLETED' | 'FAILED';
export type IngestionJobType = 'identity_run' | 'drivers_index_refresh';

export interface IdentityRunStatsSource {
  processed: number | null;
  matched: number | null;
  unmatched: number | null;
  skipped: number | null;
}

export interface IdentityRunStats {
  cabinet_leads: IdentityRunStatsSource | null;
  scouting_daily: IdentityRunStatsSource | null;
  timings: Record<string, number> | null;
  raw: Record<string, any> | null;
}

export interface IdentityRunRow {
  id: number;
  started_at: string;
  completed_at: string | null;
  status: IngestionRunStatus;
  job_type: IngestionJobType;
  scope_date_from: string | null;
  scope_date_to: string | null;
  incremental: boolean;
  error_message: string | null;
  stats: IdentityRunStats | null;
}

export interface IdentityRunsResponse {
  items: IdentityRunRow[];
  total: number;
  limit: number;
  offset: number;
}

// ============================================================================
// Ops Alerts Types
// ============================================================================

export type AlertSeverity = 'info' | 'warning' | 'error';

export interface OpsAlertRow {
  id: number;
  created_at: string;
  alert_type: string;
  severity: AlertSeverity;
  message: string;
  week_label: string | null;
  details: Record<string, any> | null;
  run_id: number | null;
  acknowledged_at: string | null;
  acknowledged: boolean;
}

export interface OpsAlertsResponse {
  items: OpsAlertRow[];
  total: number;
  limit: number;
  offset: number;
}

// ============================================================================
// Ops Data Health Types
// ============================================================================

export interface IdentitySystemHealthRow {
  calculated_at: string;
  last_run_id: number | null;
  last_run_started_at: string | null;
  last_run_completed_at: string | null;
  last_run_status: string;
  last_run_error_message: string | null;
  minutes_since_last_completed_run: number | null;
  hours_since_last_completed_run: number | null;
  unmatched_open_count: number;
  unmatched_open_by_reason: Record<string, number>;
  active_alerts_count: number;
  active_alerts_by_severity: Record<string, number>;
  total_persons: number;
  total_links: number;
  links_by_source: Record<string, number>;
}

// ============================================================================
// Run Report Types
// ============================================================================

export interface RunReportResponse {
  run: IngestionRun;
  counts_by_source_table: Record<string, {
    total_processed: number;
    matched_count: number;
    unmatched_count: number;
    skipped_count: number;
  }>;
  matched_breakdown: {
    by_match_rule: Record<string, number>;
    by_confidence: Record<string, number>;
  };
  unmatched_breakdown: {
    by_reason_code: Record<string, number>;
    top_missing_keys: Array<{ key: string; count: number }>;
  };
  samples: {
    top_unmatched: Array<{
      id: number;
      source_table: string;
      source_pk: string;
      reason_code: string;
      details: Record<string, any>;
      candidates_preview: Record<string, any> | null;
    }>;
    top_matched: Array<{
      id: number;
      source_table: string;
      source_pk: string;
      match_rule: string;
      confidence_level: string;
      match_score: number;
    }>;
  };
  weekly?: WeeklyData[];
  weekly_trend?: WeeklyTrend[];
  available_event_weeks?: string[];
  scouting_kpis?: Array<{
    week_label: string;
    source_table: string;
    processed_scouting: number;
    candidates_detected: number;
    candidate_rate: number;
    high_confidence_candidates: number;
    avg_time_to_match_days: number | null;
  }>;
}

// ============================================================================
// Dashboard Types
// ============================================================================

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
  acquisition_scout_id: number | null;
  acquisition_scout_name: string | null;
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
  lead_origin: string | null;
  scout_id: number | null;
  acquisition_scout_id: number | null;
  acquisition_scout_name: string | null;
  attribution_confidence: string | null;
  attribution_rule: string | null;
  milestone_type: string | null;
  milestone_value: number | null;
  payable_date: string | null;
  achieved_date: string | null;
  amount: number;
  currency: string | null;
  driver_id: string | null;
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
  achieved_date: string | null;
  lead_date: string | null;
  lead_origin: string | null;
  payer: string;
  milestone_type: string | null;
  milestone_value: number | null;
  window_days: number | null;
  trips_in_window: number | null;
  person_key: string;
  driver_id: string | null;
  amount: number;
  currency: string | null;
  created_at_export: string | null;
}

export interface YangoReceivableItemsResponse {
  items: YangoReceivableItem[];
  total: number;
  limit: number;
  offset: number;
}

// ============================================================================
// Payments Types
// ============================================================================

export interface PaymentEligibilityRow {
  person_key: string | null;
  origin_tag: string | null;
  scout_id: number | null;
  driver_id: string | null;
  lead_date: string | null;
  rule_id: number | null;
  rule_scope: string | null;
  milestone_trips: number | null;
  window_days: number | null;
  currency: string | null;
  amount: number | null;
  rule_valid_from: string | null;
  rule_valid_to: string | null;
  milestone_achieved: boolean | null;
  achieved_date: string | null;
  achieved_trips_in_window: number | null;
  is_payable: boolean | null;
  payable_date: string | null;
  payment_scheme: string | null;
}

export interface PaymentEligibilityResponse {
  status: string;
  count: number;
  filters: Record<string, any>;
  rows: PaymentEligibilityRow[];
}

// ============================================================================
// Yango Payments Reconciliation Types
// ============================================================================

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
  filters: Record<string, any>;
  rows: YangoReconciliationSummaryRow[];
}

export interface YangoReconciliationItemRow {
  driver_id: string | null;
  person_key: string | null;
  lead_date: string | null;
  pay_week_start_monday: string | null;
  milestone_value: number | null;
  expected_amount: number | null;
  currency: string | null;
  due_date: string | null;
  window_status: string | null;
  paid_payment_key: string | null;
  paid_payment_key_confirmed: string | null;
  paid_payment_key_enriched: string | null;
  paid_date: string | null;
  paid_date_confirmed: string | null;
  paid_date_enriched: string | null;
  is_paid_effective: boolean | null;
  match_method: string | null;
  paid_status: string | null;
  identity_status: string | null;
  match_rule: string | null;
  match_confidence: string | null;
}

export interface YangoReconciliationItemsResponse {
  status: string;
  count: number;
  total: number;
  filters: Record<string, any>;
  rows: YangoReconciliationItemRow[];
}

export interface YangoLedgerUnmatchedRow {
  payment_key: string;
  pay_date: string | null;
  is_paid: boolean | null;
  milestone_value: number | null;
  driver_id: string | null;
  person_key: string | null;
  raw_driver_name: string | null;
  driver_name_normalized: string | null;
  match_rule: string | null;
  match_confidence: string | null;
  // ... otros campos según contrato
}

export interface YangoLedgerUnmatchedResponse {
  status: string;
  count: number;
  total: number;
  filters: Record<string, any>;
  rows: YangoLedgerUnmatchedRow[];
}

export interface ClaimDetailRow {
  milestone_value: number | null;
  expected_amount: number | null;
  currency: string | null;
  lead_date: string | null;
  due_date: string | null;
  pay_week_start_monday: string | null;
  paid_status: string | null;
  paid_payment_key: string | null;
  paid_date: string | null;
  is_paid_effective: boolean | null;
  match_method: string | null;
  identity_status: string | null;
  match_rule: string | null;
  match_confidence: string | null;
}

// ============================================================================
// Yango Cabinet Claims Types
// ============================================================================

export interface YangoCabinetClaimRow {
  claim_key: string | null;
  person_key: string | null;
  driver_id: string | null;
  driver_name: string | null;
  milestone_value: number | null;
  lead_date: string | null;
  expected_amount: number | null;
  yango_due_date: string | null;
  days_overdue_yango: number | null;
  overdue_bucket_yango: string | null;
  yango_payment_status: string | null;
  reason_code: string | null;
  identity_status: string | null;
  match_rule: string | null;
  match_confidence: string | null;
  is_reconcilable_enriched: boolean | null;
  payment_key: string | null;
  pay_date: string | null;
  suggested_driver_id: string | null;
}

export interface YangoCabinetClaimsResponse {
  status: string;
  count: number;
  total: number;
  filters: Record<string, any>;
  rows: YangoCabinetClaimRow[];
}

export interface LeadCabinetInfo {
  source_pk: string | null;
  match_rule: string | null;
  match_score: number | null;
  confidence_level: string | null;
  linked_at: string | null;
}

export interface PaymentInfo {
  payment_key: string | null;
  pay_date: string | null;
  milestone_value: number | null;
  identity_status: string | null;
  match_rule: string | null;
}

export interface ReconciliationInfo {
  reconciliation_status: string | null;
  expected_amount: number | null;
  paid_payment_key: string | null;
  paid_date: string | null;
  match_method: string | null;
}

export interface YangoCabinetClaimDrilldownResponse {
  status: string;
  claim: YangoCabinetClaimRow | null;
  lead_cabinet: LeadCabinetInfo | null;
  payment_exact: PaymentInfo | null;
  payments_other_milestones: PaymentInfo[];
  reconciliation: ReconciliationInfo | null;
  misapplied_explanation: string | null;
}

// ============================================================================
// Cabinet Milestones Reconciliation Types
// ============================================================================

export interface CabinetReconciliationRow {
  driver_id: string | null;
  milestone_value: number | null;
  
  // ACHIEVED fields
  achieved_flag: boolean | null;
  achieved_person_key: string | null;
  achieved_lead_date: string | null;
  achieved_date: string | null;
  achieved_trips_in_window: number | null;
  window_days: number | null;
  expected_amount: number | null;
  achieved_currency: string | null;
  rule_id: number | null;
  
  // PAID fields
  paid_flag: boolean | null;
  paid_person_key: string | null;
  pay_date: string | null;
  payment_key: string | null;
  identity_status: string | null;
  match_rule: string | null;
  match_confidence: string | null;
  latest_snapshot_at: string | null;
  
  // Reconciliation
  reconciliation_status: string | null; // OK, ACHIEVED_NOT_PAID, PAID_WITHOUT_ACHIEVEMENT, NOT_APPLICABLE
}

export interface CabinetReconciliationResponse {
  status: string;
  count: number;
  total: number;
  filters: Record<string, any>;
  rows: CabinetReconciliationRow[];
}

// ============================================================================
// Driver Matrix Types (Ops)
// ============================================================================

export interface DriverMatrixRow {
  driver_id: string | null;
  person_key: string | null;
  driver_name: string | null;
  lead_date: string | null;
  week_start: string | null;
  origin_tag: string | null;
  connected_flag: boolean | null;
  connected_date: string | null;
  // Milestone M1
  m1_achieved_flag: boolean | null;
  m1_achieved_date: string | null;
  m1_expected_amount_yango: number | null;
  m1_yango_payment_status: string | null;
  m1_window_status: string | null;
  m1_overdue_days: number | null;
  // Milestone M5
  m5_achieved_flag: boolean | null;
  m5_achieved_date: string | null;
  m5_expected_amount_yango: number | null;
  m5_yango_payment_status: string | null;
  m5_window_status: string | null;
  m5_overdue_days: number | null;
  // Milestone M25
  m25_achieved_flag: boolean | null;
  m25_achieved_date: string | null;
  m25_expected_amount_yango: number | null;
  m25_yango_payment_status: string | null;
  m25_window_status: string | null;
  m25_overdue_days: number | null;
  // Scout
  scout_due_flag: boolean | null;
  scout_paid_flag: boolean | null;
  scout_amount: number | null;
  // Flags de inconsistencia de milestones
  m5_without_m1_flag: boolean | null;
  m25_without_m5_flag: boolean | null;
  milestone_inconsistency_notes: string | null;
  // Columnas operativas de sanity check (ventana de 14 días)
  connection_within_14d_flag: boolean | null;
  connection_date_within_14d: string | null;
  trips_completed_14d_from_lead: number | null;
  first_trip_date_within_14d: string | null;
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

export interface DriverMatrixTotals {
  // KPIs de Claims (C3/C4): Basados en claims/pagos
  drivers: number;
  expected_yango_sum: number;  // Suma de expected_amount_yango donde existe claim
  paid_sum: number;  // Suma donde status=PAID/PAID_MISAPPLIED
  receivable_sum: number;  // Expected - Paid
  expired_count: number;  // Conteo por window_status='expired' de claims
  in_window_count: number;  // Conteo por window_status='in_window' de claims
  // KPIs de Actividad (C1): Basados en milestones achieved (trips)
  achieved_m1_count?: number;  // Conteo de drivers con m1_achieved_flag = true
  achieved_m5_count?: number;  // Conteo de drivers con m5_achieved_flag = true
  achieved_m25_count?: number;  // Conteo de drivers con m25_achieved_flag = true
  achieved_m1_without_claim_count?: number;  // Conteo de drivers con m1_achieved_flag = true y m1_yango_payment_status = null
  achieved_m5_without_claim_count?: number;  // Conteo de drivers con m5_achieved_flag = true y m5_yango_payment_status = null
  achieved_m25_without_claim_count?: number;  // Conteo de drivers con m25_achieved_flag = true y m25_yango_payment_status = null
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

// Cabinet Financial 14d Types
export interface CabinetFinancialRow {
  driver_id: string;
  driver_name: string | null;
  lead_date: string | null;
  iso_week: string | null;
  connected_flag: boolean;
  connected_date: string | null;
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
}

export interface CabinetFinancialMeta {
  limit: number;
  offset: number;
  returned: number;
  total: number;
}

export interface CabinetFinancialResponse {
  meta: CabinetFinancialMeta;
  summary: CabinetFinancialSummary | null;
  summary_total: CabinetFinancialSummaryTotal | null;
  data: CabinetFinancialRow[];
}

export interface YangoDriverDetailResponse {
  status: string;
  driver_id: string;
  person_key: string | null;
  claims: ClaimDetailRow[];
  summary: {
    total_expected: number;
    total_paid: number;
    count_paid: number;
    count_pending_active: number;
    count_pending_expired: number;
  };
}

// ============================================================================
// Ops RAW Health Types
// ============================================================================

export interface RawDataHealthStatusRow {
  source_name: string;
  source_type: string | null;
  max_business_date: string | null;
  business_days_lag: number | null;
  max_ingestion_ts: string | null;
  ingestion_lag_interval: string | null;
  rows_business_yesterday: number | null;
  rows_business_today: number | null;
  rows_ingested_yesterday: number | null;
  rows_ingested_today: number | null;
  health_status: string | null;
}

export interface RawDataHealthStatusResponse {
  items: RawDataHealthStatusRow[];
  total: number;
  limit: number;
  offset: number;
}

export interface RawDataFreshnessStatusRow {
  source_name: string;
  max_business_date: string | null;
  business_days_lag: number | null;
  max_ingestion_ts: string | null;
  ingestion_lag_interval: string | null;
  rows_business_yesterday: number | null;
  rows_business_today: number | null;
  rows_ingested_yesterday: number | null;
  rows_ingested_today: number | null;
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

// ============================================================================
// Ops Health Checks Types
// ============================================================================

export interface HealthCheckRow {
  check_key: string;
  severity: 'error' | 'warning' | 'info';
  status: 'OK' | 'WARN' | 'ERROR';
  message: string;
  drilldown_url?: string | null;
  last_evaluated_at: string; // datetime -> string
}

export interface HealthChecksResponse {
  items: HealthCheckRow[];
}

export interface HealthGlobalResponse {
  global_status: 'OK' | 'WARN' | 'ERROR';
  error_count: number;
  warn_count: number;
  ok_count: number;
  calculated_at: string; // datetime -> string
}

// ============================================================================
// Ops MV Health Types
// ============================================================================

export interface MvHealthRow {
  schema_name: string;
  mv_name: string;
  is_populated: boolean | null;
  size_mb: number;
  last_refresh_at: string | null; // datetime -> string
  minutes_since_refresh: number | null;
  last_refresh_status: 'SUCCESS' | 'FAILED' | null;
  last_refresh_error: string | null;
  calculated_at: string; // datetime -> string
}

export interface MvHealthResponse {
  items: MvHealthRow[];
  total: number;
  limit: number;
  offset: number;
}

// ============================================================================
// Identity Origin Audit Types
// ============================================================================

export type OriginTag = 'cabinet_lead' | 'scout_registration' | 'migration' | 'legacy_external';
export type OriginResolutionStatus = 'pending_review' | 'resolved_auto' | 'resolved_manual' | 'marked_legacy' | 'discarded';
export type ViolationReason = 'missing_origin' | 'multiple_origins' | 'late_origin_link' | 'orphan_lead' | 'legacy_driver_unclassified';
export type RecommendedAction = 'auto_link' | 'manual_review' | 'mark_legacy' | 'discard';
export type AlertType = 'missing_origin' | 'multiple_origins' | 'legacy_unclassified' | 'orphan_lead';
export type AlertSeverity = 'low' | 'medium' | 'high';
export type AlertImpact = 'export' | 'collection' | 'reporting' | 'none';

export interface OriginAuditRow {
  person_key: string;
  driver_id: string | null;
  origin_tag: string | null;
  origin_source_id: string | null;
  origin_confidence: number | null;
  origin_created_at: string | null;
  ruleset_version: string | null;
  origin_evidence: Record<string, any> | null;
  decided_by: string | null;
  decided_at: string | null;
  resolution_status: string | null;
  notes: string | null;
  first_seen_at: string | null;
  driver_linked_at: string | null;
  has_lead_links: boolean;
  links_summary: Array<Record<string, any>> | null;
  violation_flag: boolean;
  violation_reason: string | null;
  recommended_action: string | null;
}

export interface OriginAlertRow {
  alert_id: number;
  person_key: string;
  driver_id: string | null;
  alert_type: string;
  violation_reason: string | null;
  recommended_action: string | null;
  severity: string;
  impact: string;
  origin_tag: string | null;
  origin_confidence: number | null;
  first_seen_at: string | null;
  first_detected_at: string | null;
  last_detected_at: string | null;
  resolved_at: string | null;
  resolved_by: string | null;
  muted_until: string | null;
  alert_notes: string | null;
  is_resolved_or_muted: boolean;
  resolution_status: string | null;
}

export interface OriginAuditListResponse {
  items: OriginAuditRow[];
  total: number;
  skip: number;
  limit: number;
}

export interface OriginAlertListResponse {
  items: OriginAlertRow[];
  total: number;
  skip: number;
  limit: number;
}

export interface OriginAuditStats {
  total_persons: number;
  persons_with_violations: number;
  violations_by_reason: Record<string, number>;
  violations_by_severity: Record<string, number>;
  resolution_status_distribution: Record<string, number>;
  alerts_by_type: Record<string, number>;
  alerts_by_severity: Record<string, number>;
}

// ============================================================================
// Scout Attribution Types
// ============================================================================

export interface ScoutAttributionMetrics {
  total_persons: number;
  persons_with_scout_satisfactory: number;
  pct_scout_satisfactory: number;
  persons_missing_scout: number;
  conflicts_count: number;
  backlog: {
    a_events_without_scout: number;
    d_scout_in_events_not_in_ledger: number;
    c_legacy: number;
  };
  last_job: {
    status: string | null;
    ended_at: string | null;
    started_at: string | null;
    duration_seconds: number | null;
    summary: any;
    error: string | null;
  };
  snapshot_timestamp: string | null;
}

export interface ScoutAttributionMetricsDaily {
  daily_metrics: Array<{
    date: string;
    total_persons: number;
    satisfactory_count: number;
    pct_satisfactory: number;
    missing_count: number;
    by_source: {
      scouting_daily: number;
      cabinet_leads: number;
      lead_ledger: number;
    };
  }>;
}

export interface ScoutAttributionConflict {
  person_key: string;
  distinct_scout_count: number;
  scout_ids: number[];
  sources: string[];
  origin_tags: string[] | null;
  first_event_date: string | null;
  last_event_date: string | null;
  total_sources: number;
}

export interface ScoutAttributionConflictsResponse {
  conflicts: ScoutAttributionConflict[];
  pagination: {
    page: number;
    page_size: number;
    total: number;
    total_pages: number;
  };
}

export interface ScoutAttributionBacklogItem {
  person_key: string;
  category: string;
  category_label: string;
  scout_id: number | null;
  source_tables: string[];
  origin_tags: string[] | null;
  first_event_date: string | null;
  last_event_date: string | null;
  event_count: number;
}

export interface ScoutAttributionBacklogResponse {
  backlog: ScoutAttributionBacklogItem[];
  pagination: {
    page: number;
    page_size: number;
    total: number;
    total_pages: number;
  };
}

export interface ScoutAttributionJobStatus {
  last_run: {
    run_id: number;
    status: string;
    started_at: string;
    ended_at: string | null;
    duration_seconds: number | null;
    summary: any;
    error: string | null;
  } | null;
  status: string;
}

export interface ScoutLiquidationBaseItem {
  person_key: string | null;
  driver_id: string | null;
  scout_id: number;
  origin_tag: string | null;
  milestone_reached: number;
  milestone_date: string | null;
  eligible_7d: boolean;
  amount_payable: number;
  payment_status: string;
  block_reason: string | null;
}

export interface ScoutLiquidationBaseResponse {
  items: ScoutLiquidationBaseItem[];
  pagination: {
    page: number;
    page_size: number;
  };
}

export interface YangoCollectionWithScoutItem {
  driver_id: string;
  person_key: string | null;
  driver_name: string | null;
  milestone_value: number;
  lead_date: string | null;
  expected_amount: number;
  yango_due_date: string | null;
  days_overdue_yango: number | null;
  overdue_bucket_yango: string | null;
  yango_payment_status: string | null;
  payment_key: string | null;
  pay_date: string | null;
  reason_code: string | null;
  match_rule: string | null;
  match_confidence: string | null;
  identity_status: string | null;
  scout_id: number | null;
  scout_name: string | null;
  scout_type: string | null;
  scout_quality_bucket: string | null;
  is_scout_resolved: boolean;
}

export interface YangoCollectionWithScoutResponse {
  items: YangoCollectionWithScoutItem[];
  pagination: {
    page: number;
    page_size: number;
    total: number;
    total_pages: number;
  };
}



