/**
 * API Client basado en FRONTEND_BACKEND_CONTRACT_v1.md
 * 
 * REGLA: Todos los fetch pasan por este módulo.
 * baseURL desde NEXT_PUBLIC_API_BASE_URL
 */

const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL || 'http://localhost:8000';

export class ApiError extends Error {
  constructor(
    public status: number,
    public statusText: string,
    public detail?: string
  ) {
    super(detail || statusText);
    this.name = 'ApiError';
  }
}

async function fetchApi<T>(
  path: string,
  options?: RequestInit
): Promise<T> {
  const url = `${API_BASE_URL}${path}`;
  
  const response = await fetch(url, {
    ...options,
    headers: {
      'Content-Type': 'application/json',
      ...options?.headers,
    },
  });

  if (!response.ok) {
    let detail: string | undefined;
    try {
      const errorData = await response.json();
      detail = errorData.detail || errorData.message;
    } catch {
      detail = response.statusText;
    }
    throw new ApiError(response.status, response.statusText, detail);
  }

  // Handle empty responses
  const contentType = response.headers.get('content-type');
  if (!contentType || !contentType.includes('application/json')) {
    return {} as T;
  }

  return response.json();
}

async function fetchApiFormData<T>(
  path: string,
  formData: FormData
): Promise<T> {
  const url = `${API_BASE_URL}${path}`;
  
  const response = await fetch(url, {
    method: 'POST',
    body: formData,
    // No incluir Content-Type header, el browser lo setea automáticamente con boundary
  });

  if (!response.ok) {
    let detail: string | undefined;
    try {
      const errorData = await response.json();
      detail = errorData.detail || errorData.message;
    } catch {
      detail = response.statusText;
    }
    throw new ApiError(response.status, response.statusText, detail);
  }

  return response.json();
}

// ============================================================================
// Identity API
// ============================================================================

import type {
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
} from './types';

export async function getIdentityStats(): Promise<IdentityStats> {
  return fetchApi<IdentityStats>('/api/v1/identity/stats');
}

export async function getPersonsBySource(): Promise<PersonsBySourceResponse> {
  return fetchApi<PersonsBySourceResponse>('/api/v1/identity/stats/persons-by-source');
}

export async function getDriversWithoutLeadsAnalysis(): Promise<DriversWithoutLeadsAnalysis> {
  return fetchApi<DriversWithoutLeadsAnalysis>('/api/v1/identity/stats/drivers-without-leads');
}

// ============================================================================
// Orphans / Cuarentena API
// ============================================================================

export async function getOrphans(params?: {
  page?: number;
  page_size?: number;
  status?: string;
  detected_reason?: string;
  driver_id?: string;
}): Promise<OrphansListResponse> {
  const searchParams = new URLSearchParams();
  if (params?.page !== undefined) searchParams.set('page', params.page.toString());
  if (params?.page_size !== undefined) searchParams.set('page_size', params.page_size.toString());
  if (params?.status) searchParams.set('status', params.status);
  if (params?.detected_reason) searchParams.set('detected_reason', params.detected_reason);
  if (params?.driver_id) searchParams.set('driver_id', params.driver_id);
  
  const query = searchParams.toString();
  return fetchApi<OrphansListResponse>(`/api/v1/identity/orphans${query ? `?${query}` : ''}`);
}

export async function getOrphansMetrics(): Promise<OrphansMetricsResponse> {
  return fetchApi<OrphansMetricsResponse>('/api/v1/identity/orphans/metrics');
}

export async function runOrphansFix(params?: {
  execute?: boolean;
  limit?: number;
  output_dir?: string;
}): Promise<RunFixResponse> {
  const searchParams = new URLSearchParams();
  if (params?.execute !== undefined) searchParams.set('execute', params.execute.toString());
  if (params?.limit !== undefined) searchParams.set('limit', params.limit.toString());
  if (params?.output_dir) searchParams.set('output_dir', params.output_dir);
  
  const query = searchParams.toString();
  return fetchApi<RunFixResponse>(`/api/v1/identity/orphans/run-fix${query ? `?${query}` : ''}`, {
    method: 'POST',
  });
}

export async function getPersons(params?: {
  phone?: string;
  document?: string;
  license?: string;
  name?: string;
  confidence_level?: string;
  skip?: number;
  limit?: number;
}): Promise<IdentityRegistry[]> {
  const searchParams = new URLSearchParams();
  if (params?.phone) searchParams.set('phone', params.phone);
  if (params?.document) searchParams.set('document', params.document);
  if (params?.license) searchParams.set('license', params.license);
  if (params?.name) searchParams.set('name', params.name);
  if (params?.confidence_level) searchParams.set('confidence_level', params.confidence_level);
  if (params?.skip !== undefined) searchParams.set('skip', params.skip.toString());
  if (params?.limit !== undefined) searchParams.set('limit', params.limit.toString());
  
  const query = searchParams.toString();
  return fetchApi<IdentityRegistry[]>(`/api/v1/identity/persons${query ? `?${query}` : ''}`);
}

export async function getPerson(personKey: string): Promise<PersonDetail> {
  return fetchApi<PersonDetail>(`/api/v1/identity/persons/${personKey}`);
}

export async function getUnmatched(params?: {
  reason_code?: string;
  status?: string;
  skip?: number;
  limit?: number;
}): Promise<IdentityUnmatched[]> {
  const searchParams = new URLSearchParams();
  if (params?.reason_code) searchParams.set('reason_code', params.reason_code);
  if (params?.status) searchParams.set('status', params.status);
  if (params?.skip !== undefined) searchParams.set('skip', params.skip.toString());
  if (params?.limit !== undefined) searchParams.set('limit', params.limit.toString());
  
  const query = searchParams.toString();
  return fetchApi<IdentityUnmatched[]>(`/api/v1/identity/unmatched${query ? `?${query}` : ''}`);
}

export async function resolveUnmatched(
  id: number,
  request: UnmatchedResolveRequest
): Promise<UnmatchedResolveResponse> {
  return fetchApi<UnmatchedResolveResponse>(`/api/v1/identity/unmatched/${id}/resolve`, {
    method: 'POST',
    body: JSON.stringify(request),
  });
}

export async function getGlobalMetrics(params?: {
  mode?: 'summary' | 'weekly' | 'breakdowns';
  source_table?: string;
  event_date_from?: string;
  event_date_to?: string;
}): Promise<MetricsResponse> {
  const searchParams = new URLSearchParams();
  if (params?.mode) searchParams.set('mode', params.mode);
  if (params?.source_table) searchParams.set('source_table', params.source_table);
  if (params?.event_date_from) searchParams.set('event_date_from', params.event_date_from);
  if (params?.event_date_to) searchParams.set('event_date_to', params.event_date_to);
  
  const query = searchParams.toString();
  return fetchApi<MetricsResponse>(`/api/v1/identity/metrics/global${query ? `?${query}` : ''}`);
}

export async function getRunMetrics(
  runId: number,
  params?: {
    mode?: 'summary' | 'weekly' | 'breakdowns';
    source_table?: string;
    event_date_from?: string;
    event_date_to?: string;
  }
): Promise<MetricsResponse> {
  const searchParams = new URLSearchParams();
  if (params?.mode) searchParams.set('mode', params.mode);
  if (params?.source_table) searchParams.set('source_table', params.source_table);
  if (params?.event_date_from) searchParams.set('event_date_from', params.event_date_from);
  if (params?.event_date_to) searchParams.set('event_date_to', params.event_date_to);
  
  const query = searchParams.toString();
  return fetchApi<MetricsResponse>(`/api/v1/identity/metrics/run/${runId}${query ? `?${query}` : ''}`);
}

export async function getIdentityRuns(params?: {
  limit?: number;
  offset?: number;
  status?: IngestionRunStatus;
  job_type?: IngestionJobType;
}): Promise<IdentityRunsResponse> {
  const searchParams = new URLSearchParams();
  if (params?.limit !== undefined) searchParams.set('limit', params.limit.toString());
  if (params?.offset !== undefined) searchParams.set('offset', params.offset.toString());
  if (params?.status) searchParams.set('status', params.status);
  if (params?.job_type) searchParams.set('job_type', params.job_type);
  
  const query = searchParams.toString();
  return fetchApi<IdentityRunsResponse>(`/api/v1/identity/runs${query ? `?${query}` : ''}`);
}

export async function getRunReport(
  runId: number,
  params?: {
    group_by?: string;
    source_table?: string;
    event_week?: string;
    event_date_from?: string;
    event_date_to?: string;
    include_weekly?: boolean;
  }
): Promise<RunReportResponse> {
  const searchParams = new URLSearchParams();
  if (params?.group_by) searchParams.set('group_by', params.group_by);
  if (params?.source_table) searchParams.set('source_table', params.source_table);
  if (params?.event_week) searchParams.set('event_week', params.event_week);
  if (params?.event_date_from) searchParams.set('event_date_from', params.event_date_from);
  if (params?.event_date_to) searchParams.set('event_date_to', params.event_date_to);
  if (params?.include_weekly !== undefined) searchParams.set('include_weekly', params.include_weekly.toString());
  
  const query = searchParams.toString();
  return fetchApi<RunReportResponse>(`/api/v1/identity/runs/${runId}/report${query ? `?${query}` : ''}`);
}

// ============================================================================
// Dashboard API
// ============================================================================

import type {
  ScoutSummaryResponse,
  ScoutOpenItemsResponse,
  YangoSummaryResponse,
  YangoReceivableItemsResponse,
  ScoutAttributionMetricsResponse,
  WeeklyKpisResponse,
} from './types';

export async function getScoutSummary(params?: {
  week_start?: string;
  week_end?: string;
  scout_id?: number;
  lead_origin?: string;
}): Promise<ScoutSummaryResponse> {
  const searchParams = new URLSearchParams();
  if (params?.week_start) searchParams.set('week_start', params.week_start);
  if (params?.week_end) searchParams.set('week_end', params.week_end);
  if (params?.scout_id !== undefined) searchParams.set('scout_id', params.scout_id.toString());
  if (params?.lead_origin) searchParams.set('lead_origin', params.lead_origin);
  
  const query = searchParams.toString();
  return fetchApi<ScoutSummaryResponse>(`/api/v1/dashboard/scout/summary${query ? `?${query}` : ''}`);
}

export async function getScoutOpenItems(params?: {
  week_start_monday?: string;
  scout_id?: number;
  confidence?: string;
  limit?: number;
  offset?: number;
}): Promise<ScoutOpenItemsResponse> {
  const searchParams = new URLSearchParams();
  if (params?.week_start_monday) searchParams.set('week_start_monday', params.week_start_monday);
  if (params?.scout_id !== undefined) searchParams.set('scout_id', params.scout_id.toString());
  if (params?.confidence) searchParams.set('confidence', params.confidence);
  if (params?.limit !== undefined) searchParams.set('limit', params.limit.toString());
  if (params?.offset !== undefined) searchParams.set('offset', params.offset.toString());
  
  const query = searchParams.toString();
  return fetchApi<ScoutOpenItemsResponse>(`/api/v1/dashboard/scout/open_items${query ? `?${query}` : ''}`);
}

export async function getYangoSummary(params?: {
  week_start?: string;
  week_end?: string;
}): Promise<YangoSummaryResponse> {
  const searchParams = new URLSearchParams();
  if (params?.week_start) searchParams.set('week_start', params.week_start);
  if (params?.week_end) searchParams.set('week_end', params.week_end);
  
  const query = searchParams.toString();
  return fetchApi<YangoSummaryResponse>(`/api/v1/dashboard/yango/summary${query ? `?${query}` : ''}`);
}

export async function getYangoReceivableItems(params?: {
  week_start_monday?: string;
  limit?: number;
  offset?: number;
}): Promise<YangoReceivableItemsResponse> {
  const searchParams = new URLSearchParams();
  if (params?.week_start_monday) searchParams.set('week_start_monday', params.week_start_monday);
  if (params?.limit !== undefined) searchParams.set('limit', params.limit.toString());
  if (params?.offset !== undefined) searchParams.set('offset', params.offset.toString());
  
  const query = searchParams.toString();
  return fetchApi<YangoReceivableItemsResponse>(`/api/v1/dashboard/yango/receivable_items${query ? `?${query}` : ''}`);
}

// ============================================================================
// Payments API
// ============================================================================

import type {
  PaymentEligibilityResponse,
} from './types';

export async function getPaymentEligibility(params?: {
  origin_tag?: string;
  rule_scope?: string;
  is_payable?: boolean;
  scout_id?: number;
  driver_id?: string;
  payable_from?: string;
  payable_to?: string;
  limit?: number;
  offset?: number;
  order_by?: 'payable_date' | 'lead_date' | 'amount';
  order_dir?: 'asc' | 'desc';
}): Promise<PaymentEligibilityResponse> {
  const searchParams = new URLSearchParams();
  if (params?.origin_tag) searchParams.set('origin_tag', params.origin_tag);
  if (params?.rule_scope) searchParams.set('rule_scope', params.rule_scope);
  if (params?.is_payable !== undefined) searchParams.set('is_payable', params.is_payable.toString());
  if (params?.scout_id !== undefined) searchParams.set('scout_id', params.scout_id.toString());
  if (params?.driver_id) searchParams.set('driver_id', params.driver_id);
  if (params?.payable_from) searchParams.set('payable_from', params.payable_from);
  if (params?.payable_to) searchParams.set('payable_to', params.payable_to);
  if (params?.limit !== undefined) searchParams.set('limit', params.limit.toString());
  if (params?.offset !== undefined) searchParams.set('offset', params.offset.toString());
  if (params?.order_by) searchParams.set('order_by', params.order_by);
  if (params?.order_dir) searchParams.set('order_dir', params.order_dir);
  
  const query = searchParams.toString();
  return fetchApi<PaymentEligibilityResponse>(`/api/v1/payments/eligibility${query ? `?${query}` : ''}`);
}

import type {
  DriverMatrixResponse,
} from './types';

export async function getDriverMatrix(params?: {
  week_from?: string;
  week_to?: string;
  search?: string;
  only_pending?: boolean;
  page?: number;
  limit?: number;
}): Promise<DriverMatrixResponse> {
  const searchParams = new URLSearchParams();
  if (params?.week_from) searchParams.set('week_from', params.week_from);
  if (params?.week_to) searchParams.set('week_to', params.week_to);
  if (params?.search) searchParams.set('search', params.search);
  if (params?.only_pending !== undefined) searchParams.set('only_pending', params.only_pending.toString());
  if (params?.page !== undefined) searchParams.set('page', params.page.toString());
  if (params?.limit !== undefined) searchParams.set('limit', params.limit.toString());
  
  const query = searchParams.toString();
  return fetchApi<DriverMatrixResponse>(`/api/v1/payments/driver-matrix${query ? `?${query}` : ''}`);
}

export async function exportDriverMatrix(params?: {
  week_from?: string;
  week_to?: string;
  search?: string;
  only_pending?: boolean;
}): Promise<Blob> {
  const searchParams = new URLSearchParams();
  if (params?.week_from) searchParams.set('week_from', params.week_from);
  if (params?.week_to) searchParams.set('week_to', params.week_to);
  if (params?.search) searchParams.set('search', params.search);
  if (params?.only_pending !== undefined) searchParams.set('only_pending', params.only_pending.toString());
  
  const query = searchParams.toString();
  const url = `${API_BASE_URL}/api/v1/payments/driver-matrix/export${query ? `?${query}` : ''}`;
  
  const response = await fetch(url);
  if (!response.ok) {
    let detail: string | undefined;
    try {
      const errorData = await response.json();
      detail = errorData.detail || errorData.message;
    } catch {
      detail = response.statusText;
    }
    throw new ApiError(response.status, response.statusText, detail);
  }
  
  return response.blob();
}

// ============================================================================
// Yango Payments Reconciliation API
// ============================================================================

import type {
  YangoReconciliationSummaryResponse,
  YangoReconciliationItemsResponse,
  YangoLedgerUnmatchedResponse,
  YangoDriverDetailResponse,
} from './types';

export async function getYangoReconciliationSummary(params?: {
  week_start?: string;
  milestone_value?: number;
  mode?: 'real' | 'assumed';
  limit?: number;
}): Promise<YangoReconciliationSummaryResponse> {
  const searchParams = new URLSearchParams();
  if (params?.week_start) searchParams.set('week_start', params.week_start);
  if (params?.milestone_value !== undefined) searchParams.set('milestone_value', params.milestone_value.toString());
  if (params?.mode) searchParams.set('mode', params.mode);
  if (params?.limit !== undefined) searchParams.set('limit', params.limit.toString());
  
  const query = searchParams.toString();
  return fetchApi<YangoReconciliationSummaryResponse>(`/api/v1/yango/payments/reconciliation/summary${query ? `?${query}` : ''}`);
}

export async function getYangoReconciliationItems(params?: {
  week_start?: string;
  milestone_value?: number;
  driver_id?: string;
  paid_status?: string;
  limit?: number;
  offset?: number;
}): Promise<YangoReconciliationItemsResponse> {
  const searchParams = new URLSearchParams();
  if (params?.week_start) searchParams.set('week_start', params.week_start);
  if (params?.milestone_value !== undefined) searchParams.set('milestone_value', params.milestone_value.toString());
  if (params?.driver_id) searchParams.set('driver_id', params.driver_id);
  if (params?.paid_status) searchParams.set('paid_status', params.paid_status);
  if (params?.limit !== undefined) searchParams.set('limit', params.limit.toString());
  if (params?.offset !== undefined) searchParams.set('offset', params.offset.toString());
  
  const query = searchParams.toString();
  return fetchApi<YangoReconciliationItemsResponse>(`/api/v1/yango/payments/reconciliation/items${query ? `?${query}` : ''}`);
}

export async function getYangoLedgerUnmatched(params?: {
  is_paid?: boolean;
  driver_id?: string;
  identity_status?: string;
  limit?: number;
  offset?: number;
}): Promise<YangoLedgerUnmatchedResponse> {
  const searchParams = new URLSearchParams();
  if (params?.is_paid !== undefined) searchParams.set('is_paid', params.is_paid.toString());
  if (params?.driver_id) searchParams.set('driver_id', params.driver_id);
  if (params?.identity_status) searchParams.set('identity_status', params.identity_status);
  if (params?.limit !== undefined) searchParams.set('limit', params.limit.toString());
  if (params?.offset !== undefined) searchParams.set('offset', params.offset.toString());
  
  const query = searchParams.toString();
  return fetchApi<YangoLedgerUnmatchedResponse>(`/api/v1/yango/payments/reconciliation/ledger/unmatched${query ? `?${query}` : ''}`);
}

export async function getYangoLedgerMatched(params?: {
  is_paid?: boolean;
  driver_id?: string;
  limit?: number;
  offset?: number;
}): Promise<YangoLedgerUnmatchedResponse> {
  const searchParams = new URLSearchParams();
  if (params?.is_paid !== undefined) searchParams.set('is_paid', params.is_paid.toString());
  if (params?.driver_id) searchParams.set('driver_id', params.driver_id);
  if (params?.limit !== undefined) searchParams.set('limit', params.limit.toString());
  if (params?.offset !== undefined) searchParams.set('offset', params.offset.toString());
  
  const query = searchParams.toString();
  return fetchApi<YangoLedgerUnmatchedResponse>(`/api/v1/yango/payments/reconciliation/ledger/matched${query ? `?${query}` : ''}`);
}

export async function getYangoDriverDetail(driverId: string): Promise<YangoDriverDetailResponse> {
  return fetchApi<YangoDriverDetailResponse>(`/api/v1/yango/payments/reconciliation/driver/${driverId}`);
}

// ============================================================================
// Yango Cabinet Claims API
// ============================================================================

import type {
  YangoCabinetClaimsResponse,
  YangoCabinetClaimDrilldownResponse,
  CabinetReconciliationResponse,
} from './types';

export async function getYangoCabinetClaimsToCollect(params?: {
  date_from?: string;
  date_to?: string;
  milestone_value?: number;
  search?: string;
  limit?: number;
  offset?: number;
}): Promise<YangoCabinetClaimsResponse> {
  const searchParams = new URLSearchParams();
  if (params?.date_from) searchParams.set('date_from', params.date_from);
  if (params?.date_to) searchParams.set('date_to', params.date_to);
  if (params?.milestone_value !== undefined) searchParams.set('milestone_value', params.milestone_value.toString());
  if (params?.search) searchParams.set('search', params.search);
  if (params?.limit !== undefined) searchParams.set('limit', params.limit.toString());
  if (params?.offset !== undefined) searchParams.set('offset', params.offset.toString());
  
  const query = searchParams.toString();
  return fetchApi<YangoCabinetClaimsResponse>(`/api/v1/yango/cabinet/claims-to-collect${query ? `?${query}` : ''}`);
}

export async function getYangoCabinetClaimDrilldown(
  driverId: string,
  milestoneValue: number,
  leadDate?: string
): Promise<YangoCabinetClaimDrilldownResponse> {
  const searchParams = new URLSearchParams();
  if (leadDate) searchParams.set('lead_date', leadDate);
  
  const query = searchParams.toString();
  return fetchApi<YangoCabinetClaimDrilldownResponse>(
    `/api/v1/yango/cabinet/claims/${driverId}/${milestoneValue}/drilldown${query ? `?${query}` : ''}`
  );
}

export async function getCabinetReconciliation(params?: {
  driver_id?: string;
  reconciliation_status?: string;
  milestone_value?: number;
  date_from?: string;
  date_to?: string;
  limit?: number;
  offset?: number;
}): Promise<CabinetReconciliationResponse> {
  const searchParams = new URLSearchParams();
  if (params?.driver_id) searchParams.set('driver_id', params.driver_id);
  if (params?.reconciliation_status) searchParams.set('reconciliation_status', params.reconciliation_status);
  if (params?.milestone_value !== undefined) searchParams.set('milestone_value', params.milestone_value.toString());
  if (params?.date_from) searchParams.set('date_from', params.date_from);
  if (params?.date_to) searchParams.set('date_to', params.date_to);
  if (params?.limit !== undefined) searchParams.set('limit', params.limit.toString());
  if (params?.offset !== undefined) searchParams.set('offset', params.offset.toString());
  
  const query = searchParams.toString();
  return fetchApi<CabinetReconciliationResponse>(`/api/v1/yango/payments/cabinet/reconciliation${query ? `?${query}` : ''}`);
}

export async function getCabinetIdentityRecoveryImpact14d(params?: {
  include_series?: boolean;
}): Promise<CabinetRecoveryImpactResponse> {
  const searchParams = new URLSearchParams();
  if (params?.include_series !== undefined) searchParams.set('include_series', params.include_series.toString());
  
  const query = searchParams.toString();
  return fetchApi<CabinetRecoveryImpactResponse>(`/api/v1/yango/cabinet/identity-recovery-impact-14d${query ? `?${query}` : ''}`);
}

// ============================================================================
// Ops Payments API
// ============================================================================

import type {
  OpsDriverMatrixResponse,
  CabinetFinancialResponse,
} from './types';

export async function getOpsDriverMatrix(params?: {
  week_start_from?: string;
  week_start_to?: string;
  origin_tag?: 'cabinet' | 'fleet_migration' | 'unknown' | string;
  funnel_status?: 'registered_incomplete' | 'registered_complete' | 'connected_no_trips' | 'reached_m1' | 'reached_m5' | 'reached_m25' | string;
  only_pending?: boolean;
  limit?: number;
  offset?: number;
  order?: 'week_start_desc' | 'week_start_asc' | 'lead_date_desc' | 'lead_date_asc';
}): Promise<OpsDriverMatrixResponse> {
  const searchParams = new URLSearchParams();
  if (params?.week_start_from) searchParams.set('week_start_from', params.week_start_from);
  if (params?.week_start_to) searchParams.set('week_start_to', params.week_start_to);
  // Validar origin_tag antes de agregarlo
  if (params?.origin_tag && (params.origin_tag === 'cabinet' || params.origin_tag === 'fleet_migration' || params.origin_tag === 'unknown')) {
    searchParams.set('origin_tag', params.origin_tag);
  }
  if (params?.funnel_status) {
    searchParams.set('funnel_status', params.funnel_status);
  }
  if (params?.only_pending !== undefined) searchParams.set('only_pending', params.only_pending.toString());
  if (params?.limit !== undefined) searchParams.set('limit', params.limit.toString());
  if (params?.offset !== undefined) searchParams.set('offset', params.offset.toString());
  if (params?.order) searchParams.set('order', params.order);
  
  const query = searchParams.toString();
  return fetchApi<OpsDriverMatrixResponse>(`/api/v1/ops/payments/driver-matrix${query ? `?${query}` : ''}`);
}

export async function getCabinetFinancial14d(params?: {
  only_with_debt?: boolean;
  min_debt?: number;
  reached_milestone?: 'm1' | 'm5' | 'm25';
  scout_id?: number;
  limit?: number;
  offset?: number;
  include_summary?: boolean;
  use_materialized?: boolean;
}): Promise<CabinetFinancialResponse> {
  const searchParams = new URLSearchParams();
  if (params?.only_with_debt !== undefined) searchParams.set('only_with_debt', params.only_with_debt.toString());
  if (params?.min_debt !== undefined) searchParams.set('min_debt', params.min_debt.toString());
  if (params?.reached_milestone) searchParams.set('reached_milestone', params.reached_milestone);
  if (params?.scout_id !== undefined) searchParams.set('scout_id', params.scout_id.toString());
  if (params?.limit !== undefined) searchParams.set('limit', params.limit.toString());
  if (params?.offset !== undefined) searchParams.set('offset', params.offset.toString());
  if (params?.include_summary !== undefined) searchParams.set('include_summary', params.include_summary.toString());
  if (params?.use_materialized !== undefined) searchParams.set('use_materialized', params.use_materialized.toString());
  
  const query = searchParams.toString();
  return fetchApi<CabinetFinancialResponse>(`/api/v1/ops/payments/cabinet-financial-14d${query ? `?${query}` : ''}`);
}

export async function getFunnelGapMetrics(): Promise<FunnelGapMetrics> {
  return fetchApi<FunnelGapMetrics>('/api/v1/ops/payments/cabinet-financial-14d/funnel-gap');
}

export type { FunnelGapMetrics };

export async function getCobranzaYangoScoutAttributionMetrics(params?: {
  only_with_debt?: boolean;
  min_debt?: number;
  reached_milestone?: 'm1' | 'm5' | 'm25';
  scout_id?: number;
  use_materialized?: boolean;
}): Promise<ScoutAttributionMetricsResponse> {
  const searchParams = new URLSearchParams();
  if (params?.only_with_debt !== undefined) searchParams.set('only_with_debt', params.only_with_debt.toString());
  if (params?.min_debt !== undefined) searchParams.set('min_debt', params.min_debt.toString());
  if (params?.reached_milestone) searchParams.set('reached_milestone', params.reached_milestone);
  if (params?.scout_id !== undefined) searchParams.set('scout_id', params.scout_id.toString());
  if (params?.use_materialized !== undefined) searchParams.set('use_materialized', params.use_materialized.toString());
  
  const query = searchParams.toString();
  return fetchApi<ScoutAttributionMetricsResponse>(`/api/v1/payments/yango/cabinet/cobranza-yango/scout-attribution-metrics${query ? `?${query}` : ''}`);
}

export async function getCobranzaYangoWeeklyKpis(params?: {
  only_with_debt?: boolean;
  min_debt?: number;
  reached_milestone?: 'm1' | 'm5' | 'm25';
  scout_id?: number;
  scout_quality_bucket?: string;
  week_start_from?: string;
  week_start_to?: string;
  limit_weeks?: number;
  use_materialized?: boolean;
}): Promise<WeeklyKpisResponse> {
  const searchParams = new URLSearchParams();
  if (params?.only_with_debt !== undefined) searchParams.set('only_with_debt', params.only_with_debt.toString());
  if (params?.min_debt !== undefined) searchParams.set('min_debt', params.min_debt.toString());
  if (params?.reached_milestone) searchParams.set('reached_milestone', params.reached_milestone);
  if (params?.scout_id !== undefined) searchParams.set('scout_id', params.scout_id.toString());
  if (params?.scout_quality_bucket) searchParams.set('scout_quality_bucket', params.scout_quality_bucket);
  if (params?.week_start_from) searchParams.set('week_start_from', params.week_start_from);
  if (params?.week_start_to) searchParams.set('week_start_to', params.week_start_to);
  if (params?.limit_weeks !== undefined) searchParams.set('limit_weeks', params.limit_weeks.toString());
  if (params?.use_materialized !== undefined) searchParams.set('use_materialized', params.use_materialized.toString());
  
  const query = searchParams.toString();
  return fetchApi<WeeklyKpisResponse>(`/api/v1/payments/yango/cabinet/cobranza-yango/weekly-kpis${query ? `?${query}` : ''}`);
}

export async function exportCabinetFinancial14dCSV(params?: {
  only_with_debt?: boolean;
  min_debt?: number;
  reached_milestone?: 'm1' | 'm5' | 'm25';
  week_start?: string;
  use_materialized?: boolean;
}): Promise<Blob> {
  const searchParams = new URLSearchParams();
  if (params?.only_with_debt !== undefined) searchParams.set('only_with_debt', params.only_with_debt.toString());
  if (params?.min_debt !== undefined) searchParams.set('min_debt', params.min_debt.toString());
  if (params?.reached_milestone) searchParams.set('reached_milestone', params.reached_milestone);
  if (params?.use_materialized !== undefined) searchParams.set('use_materialized', params.use_materialized.toString());
  
  const query = searchParams.toString();
  const url = `${API_BASE_URL}/api/v1/ops/payments/cabinet-financial-14d/export${query ? `?${query}` : ''}`;
  
  const response = await fetch(url);
  if (!response.ok) {
    let detail: string | undefined;
    try {
      const errorData = await response.json();
      detail = errorData.detail || errorData.message;
    } catch {
      detail = response.statusText;
    }
    throw new ApiError(response.status, response.statusText, detail);
  }
  
  return response.blob();
}

// ============================================================================
// Ops API
// ============================================================================

import { opsDataHealth, opsRawHealthStatus, opsRawHealthFreshness, opsRawHealthIngestionDaily, ENDPOINTS } from './endpoints';

export async function getOpsAlerts(params?: {
  limit?: number;
  offset?: number;
  severity?: AlertSeverity;
  acknowledged?: boolean;
  week_label?: string;
}): Promise<OpsAlertsResponse> {
  const searchParams = new URLSearchParams();
  if (params?.limit !== undefined) searchParams.set('limit', params.limit.toString());
  if (params?.offset !== undefined) searchParams.set('offset', params.offset.toString());
  if (params?.severity) searchParams.set('severity', params.severity);
  if (params?.acknowledged !== undefined) searchParams.set('acknowledged', params.acknowledged.toString());
  if (params?.week_label) searchParams.set('week_label', params.week_label);
  
  const query = searchParams.toString();
  return fetchApi<OpsAlertsResponse>(`/api/v1/ops/alerts${query ? `?${query}` : ''}`);
}

export async function acknowledgeAlert(alertId: number): Promise<OpsAlertRow> {
  return fetchApi<OpsAlertRow>(`/api/v1/ops/alerts/${alertId}/acknowledge`, {
    method: 'POST',
  });
}

export async function getOpsDataHealth(): Promise<IdentitySystemHealthRow> {
  return fetchApi<IdentitySystemHealthRow>(opsDataHealth());
}

export async function getOpsRawHealthStatus(params?: {
  limit?: number;
  offset?: number;
  source?: string;
}): Promise<RawDataHealthStatusResponse> {
  return fetchApi<RawDataHealthStatusResponse>(opsRawHealthStatus(params));
}

export async function getOpsRawHealthFreshness(params?: {
  limit?: number;
  offset?: number;
  source?: string;
}): Promise<RawDataFreshnessStatusResponse> {
  return fetchApi<RawDataFreshnessStatusResponse>(opsRawHealthFreshness(params));
}

export async function getOpsRawHealthIngestionDaily(params?: {
  limit?: number;
  offset?: number;
  source?: string;
  date_from?: string;
  date_to?: string;
}): Promise<RawDataIngestionDailyResponse> {
  return fetchApi<RawDataIngestionDailyResponse>(opsRawHealthIngestionDaily(params));
}

export async function getOpsHealthChecks(): Promise<HealthChecksResponse> {
  return fetchApi<HealthChecksResponse>(ENDPOINTS.OPS_HEALTH_CHECKS);
}

export async function getOpsHealthGlobal(): Promise<HealthGlobalResponse> {
  return fetchApi<HealthGlobalResponse>(ENDPOINTS.OPS_HEALTH_GLOBAL);
}

export async function getOpsMvHealth(params?: {
  limit?: number;
  offset?: number;
  schema_name?: string;
  stale_only?: boolean;
}): Promise<MvHealthResponse> {
  const searchParams = new URLSearchParams();
  if (params?.limit !== undefined) searchParams.set('limit', params.limit.toString());
  if (params?.offset !== undefined) searchParams.set('offset', params.offset.toString());
  if (params?.schema_name) searchParams.set('schema_name', params.schema_name);
  if (params?.stale_only !== undefined) searchParams.set('stale_only', params.stale_only.toString());
  
  const query = searchParams.toString();
  return fetchApi<MvHealthResponse>(`/api/v1/ops/mv-health${query ? `?${query}` : ''}`);
}

// ============================================================================
// Cabinet Leads Upload
// ============================================================================

export interface CabinetLeadsUploadResponse {
  status: string;
  message: string;
  stats: {
    total_inserted: number;
    total_ignored: number;
    total_rows: number;
    errors_count: number;
    auto_process: boolean;
    skipped_by_date?: number;
    date_cutoff_used?: string | null;
  };
  errors: string[];
  run_id: number | null;
}

export async function uploadCabinetLeadsCSV(
  file: File,
  autoProcess: boolean = true,
  skipAlreadyProcessed: boolean = true
): Promise<CabinetLeadsUploadResponse> {
  const formData = new FormData();
  formData.append('file', file);
  formData.append('auto_process', autoProcess.toString());
  
  // skip_already_processed es un query parameter, no form data
  const searchParams = new URLSearchParams();
  searchParams.set('skip_already_processed', skipAlreadyProcessed.toString());
  
  const url = `${API_BASE_URL}/api/v1/cabinet-leads/upload-csv?${searchParams.toString()}`;
  
  const response = await fetch(url, {
    method: 'POST',
    body: formData,
    // No incluir Content-Type header, el browser lo setea automáticamente con boundary
  });

  if (!response.ok) {
    let detail: string | undefined;
    try {
      const errorData = await response.json();
      detail = errorData.detail || errorData.message;
    } catch {
      detail = response.statusText;
    }
    throw new ApiError(response.status, response.statusText, detail);
  }

  return response.json();
}

export async function getCabinetLeadsDiagnostics(): Promise<CabinetLeadsDiagnostics> {
  return fetchApi<CabinetLeadsDiagnostics>('/api/v1/cabinet-leads/diagnostics');
}

export type { CabinetLeadsDiagnostics };

// ============================================================================
// Identity Origin Audit API
// ============================================================================

import type {
  OriginAuditRow,
  OriginAlertRow,
  OriginAuditListResponse,
  OriginAlertListResponse,
  OriginAuditStats,
} from './types';

export async function getOriginAudit(params?: {
  violation_flag?: boolean;
  violation_reason?: string;
  resolution_status?: string;
  origin_tag?: string;
  skip?: number;
  limit?: number;
}): Promise<OriginAuditListResponse> {
  const searchParams = new URLSearchParams();
  if (params?.violation_flag !== undefined) searchParams.set('violation_flag', params.violation_flag.toString());
  if (params?.violation_reason) searchParams.set('violation_reason', params.violation_reason);
  if (params?.resolution_status) searchParams.set('resolution_status', params.resolution_status);
  if (params?.origin_tag) searchParams.set('origin_tag', params.origin_tag);
  if (params?.skip !== undefined) searchParams.set('skip', params.skip.toString());
  if (params?.limit !== undefined) searchParams.set('limit', params.limit.toString());
  
  const query = searchParams.toString();
  return fetchApi<OriginAuditListResponse>(`/api/v1/identity/audit/origin${query ? `?${query}` : ''}`);
}

export async function getOriginAuditDetail(personKey: string): Promise<OriginAuditRow> {
  return fetchApi<OriginAuditRow>(`/api/v1/identity/audit/origin/${personKey}`);
}

export async function resolveOriginViolation(
  personKey: string,
  request: {
    resolution_status: string;
    origin_tag?: string;
    origin_source_id?: string;
    origin_confidence?: number;
    notes?: string;
  }
): Promise<{ message: string; person_key: string }> {
  return fetchApi<{ message: string; person_key: string }>(
    `/api/v1/identity/audit/origin/${personKey}/resolve`,
    {
      method: 'POST',
      body: JSON.stringify(request),
    }
  );
}

export async function markAsLegacy(
  personKey: string,
  request: { notes?: string }
): Promise<{ message: string; person_key: string }> {
  return fetchApi<{ message: string; person_key: string }>(
    `/api/v1/identity/audit/origin/${personKey}/mark-legacy`,
    {
      method: 'POST',
      body: JSON.stringify(request),
    }
  );
}

export async function getOriginAlerts(params?: {
  alert_type?: string;
  severity?: string;
  impact?: string;
  resolved_only?: boolean;
  skip?: number;
  limit?: number;
}): Promise<OriginAlertListResponse> {
  const searchParams = new URLSearchParams();
  if (params?.alert_type) searchParams.set('alert_type', params.alert_type);
  if (params?.severity) searchParams.set('severity', params.severity);
  if (params?.impact) searchParams.set('impact', params.impact);
  if (params?.resolved_only !== undefined) searchParams.set('resolved_only', params.resolved_only.toString());
  if (params?.skip !== undefined) searchParams.set('skip', params.skip.toString());
  if (params?.limit !== undefined) searchParams.set('limit', params.limit.toString());
  
  const query = searchParams.toString();
  return fetchApi<OriginAlertListResponse>(`/api/v1/identity/audit/alerts${query ? `?${query}` : ''}`);
}

export async function resolveAlert(
  personKey: string,
  alertType: string,
  request: { resolved_by: string; notes?: string }
): Promise<{ message: string; person_key: string; alert_type: string }> {
  return fetchApi<{ message: string; person_key: string; alert_type: string }>(
    `/api/v1/identity/audit/alerts/${personKey}/${alertType}/resolve`,
    {
      method: 'POST',
      body: JSON.stringify(request),
    }
  );
}

export async function muteAlert(
  personKey: string,
  alertType: string,
  request: { muted_until: string; notes?: string }
): Promise<{ message: string; person_key: string; alert_type: string }> {
  return fetchApi<{ message: string; person_key: string; alert_type: string }>(
    `/api/v1/identity/audit/alerts/${personKey}/${alertType}/mute`,
    {
      method: 'POST',
      body: JSON.stringify(request),
    }
  );
}

export async function getOriginAuditStats(): Promise<OriginAuditStats> {
  return fetchApi<OriginAuditStats>('/api/v1/identity/audit/stats');
}

// ============================================================================
// Identity Gap Recovery API
// ============================================================================

export interface IdentityGapRow {
  lead_id: string;
  lead_date: string;
  person_key: string | null;
  has_identity: boolean;
  has_origin: boolean;
  trips_14d: number;
  gap_reason: string;
  gap_age_days: number;
  risk_level: string;
}

export interface IdentityGapTotals {
  total_leads: number;
  unresolved: number;
  resolved: number;
  pct_unresolved: number;
  matched_last_24h: number;
  last_job_run: string | null;
  job_freshness_hours: number | null;
}

export interface IdentityGapBreakdown {
  gap_reason: string;
  risk_level: string;
  count: number;
}

export interface IdentityGapResponse {
  totals: IdentityGapTotals;
  breakdown: IdentityGapBreakdown[];
  items: IdentityGapRow[];
  meta: {
    page: number;
    page_size: number;
    total: number;
    total_pages: number;
  };
}

export interface IdentityGapAlertRow {
  lead_id: string;
  alert_type: string;
  severity: string;
  days_open: number;
  suggested_action: string;
}

export interface IdentityGapAlertsResponse {
  items: IdentityGapAlertRow[];
  total: number;
  meta: Record<string, any>;
}

export async function getIdentityGaps(params?: {
  date_from?: string;
  date_to?: string;
  risk_level?: 'high' | 'medium' | 'low';
  gap_reason?: string;
  page?: number;
  page_size?: number;
}): Promise<IdentityGapResponse> {
  const searchParams = new URLSearchParams();
  if (params?.date_from) searchParams.set('date_from', params.date_from);
  if (params?.date_to) searchParams.set('date_to', params.date_to);
  if (params?.risk_level) searchParams.set('risk_level', params.risk_level);
  if (params?.gap_reason) searchParams.set('gap_reason', params.gap_reason);
  if (params?.page !== undefined) searchParams.set('page', params.page.toString());
  if (params?.page_size !== undefined) searchParams.set('page_size', params.page_size.toString());
  
  const query = searchParams.toString();
  return fetchApi<IdentityGapResponse>(`/api/v1/ops/identity-gaps${query ? `?${query}` : ''}`);
}

export async function getIdentityGapAlerts(): Promise<IdentityGapAlertsResponse> {
  return fetchApi<IdentityGapAlertsResponse>('/api/v1/ops/identity-gaps/alerts');
}

// ============================================================================
// Scout Attribution API
// ============================================================================

import type {
  ScoutAttributionMetrics,
  ScoutAttributionMetricsDaily,
  ScoutAttributionConflictsResponse,
  ScoutAttributionBacklogResponse,
  ScoutAttributionJobStatus,
  ScoutLiquidationBaseResponse,
  YangoCollectionWithScoutResponse,
} from './types';

export async function getScoutAttributionMetrics(): Promise<ScoutAttributionMetrics> {
  return fetchApi<ScoutAttributionMetrics>('/api/v1/scouts/attribution/metrics');
}

export async function getScoutAttributionMetricsDaily(params?: {
  days?: number;
}): Promise<ScoutAttributionMetricsDaily> {
  const searchParams = new URLSearchParams();
  if (params?.days !== undefined) searchParams.set('days', params.days.toString());
  
  const query = searchParams.toString();
  return fetchApi<ScoutAttributionMetricsDaily>(`/api/v1/scouts/attribution/metrics/daily${query ? `?${query}` : ''}`);
}

export async function getScoutAttributionConflicts(params?: {
  page?: number;
  page_size?: number;
}): Promise<ScoutAttributionConflictsResponse> {
  const searchParams = new URLSearchParams();
  if (params?.page !== undefined) searchParams.set('page', params.page.toString());
  if (params?.page_size !== undefined) searchParams.set('page_size', params.page_size.toString());
  
  const query = searchParams.toString();
  return fetchApi<ScoutAttributionConflictsResponse>(`/api/v1/scouts/attribution/conflicts${query ? `?${query}` : ''}`);
}

export async function getScoutAttributionBacklog(params?: {
  category?: string;
  page?: number;
  page_size?: number;
}): Promise<ScoutAttributionBacklogResponse> {
  const searchParams = new URLSearchParams();
  if (params?.category) searchParams.set('category', params.category);
  if (params?.page !== undefined) searchParams.set('page', params.page.toString());
  if (params?.page_size !== undefined) searchParams.set('page_size', params.page_size.toString());
  
  const query = searchParams.toString();
  return fetchApi<ScoutAttributionBacklogResponse>(`/api/v1/scouts/attribution/backlog${query ? `?${query}` : ''}`);
}

export async function getScoutAttributionJobStatus(): Promise<ScoutAttributionJobStatus> {
  return fetchApi<ScoutAttributionJobStatus>('/api/v1/scouts/attribution/job-status');
}

export async function runScoutAttributionNow(): Promise<{ status: string; run_id: number; message: string }> {
  return fetchApi<{ status: string; run_id: number; message: string }>('/api/v1/scouts/attribution/run-now', {
    method: 'POST',
  });
}

export async function getScoutLiquidationBase(params?: {
  page?: number;
  page_size?: number;
  filters?: string;
}): Promise<ScoutLiquidationBaseResponse> {
  const searchParams = new URLSearchParams();
  if (params?.page !== undefined) searchParams.set('page', params.page.toString());
  if (params?.page_size !== undefined) searchParams.set('page_size', params.page_size.toString());
  if (params?.filters) searchParams.set('filters', params.filters);
  
  const query = searchParams.toString();
  return fetchApi<ScoutLiquidationBaseResponse>(`/api/v1/scouts/liquidation/base${query ? `?${query}` : ''}`);
}

export async function getYangoCollectionWithScout(params?: {
  page?: number;
  page_size?: number;
  scout_missing_only?: boolean;
  conflicts_only?: boolean;
  scout_id?: number;
}): Promise<YangoCollectionWithScoutResponse> {
  const searchParams = new URLSearchParams();
  if (params?.page !== undefined) searchParams.set('page', params.page.toString());
  if (params?.page_size !== undefined) searchParams.set('page_size', params.page_size.toString());
  if (params?.scout_missing_only !== undefined) searchParams.set('scout_missing_only', params.scout_missing_only.toString());
  if (params?.conflicts_only !== undefined) searchParams.set('conflicts_only', params.conflicts_only.toString());
  if (params?.scout_id !== undefined) searchParams.set('scout_id', params.scout_id.toString());
  
  const query = searchParams.toString();
  return fetchApi<YangoCollectionWithScoutResponse>(`/api/v1/yango/cabinet/collection-with-scout${query ? `?${query}` : ''}`);
}
