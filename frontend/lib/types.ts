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

// Re-export other types that might be imported from here
export type {
  IdentityStats,
  IdentityRunsResponse,
  IngestionRunStatus,
  IngestionJobType,
  IdentityRegistry,
  PersonDetail,
  IdentityUnmatched,
  UnmatchedResolveRequest,
  UnmatchedResolveResponse,
  MetricsResponse,
  RunReportResponse,
  OpsAlertsResponse,
  OpsAlertRow,
  AlertSeverity,
  IdentitySystemHealthRow,
  RawDataHealthStatusResponse,
  RawDataFreshnessStatusResponse,
  RawDataIngestionDailyResponse,
  HealthChecksResponse,
  HealthGlobalResponse,
  MvHealthResponse,
  PersonsBySourceResponse,
  DriversWithoutLeadsAnalysis,
  OrphanDriver,
  OrphansListResponse,
  OrphansMetricsResponse,
  RunFixResponse,
  CabinetLeadsDiagnostics,
  FunnelGapMetrics,
  ScoutAttributionMetricsResponse,
  WeeklyKpisResponse,
  IdentityGapResponse,
  IdentityGapAlertsResponse,
  OpsDriverMatrixResponse,
} from './api';
