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
} from './types';

export async function getIdentityStats(): Promise<IdentityStats> {
  return fetchApi<IdentityStats>('/api/v1/identity/stats');
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
