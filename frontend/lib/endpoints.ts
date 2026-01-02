/**
 * Endpoints y query builders
 * Basado en FRONTEND_BACKEND_CONTRACT_v1.md
 */

export const ENDPOINTS = {
  // Identity
  IDENTITY_STATS: '/api/v1/identity/stats',
  IDENTITY_PERSONS: '/api/v1/identity/persons',
  IDENTITY_PERSON: (personKey: string) => `/api/v1/identity/persons/${personKey}`,
  IDENTITY_UNMATCHED: '/api/v1/identity/unmatched',
  IDENTITY_UNMATCHED_RESOLVE: (id: number) => `/api/v1/identity/unmatched/${id}/resolve`,
  IDENTITY_METRICS_GLOBAL: '/api/v1/identity/metrics/global',
  IDENTITY_METRICS_RUN: (runId: number) => `/api/v1/identity/metrics/run/${runId}`,
  IDENTITY_RUNS: '/api/v1/identity/runs',
  IDENTITY_RUN_REPORT: (runId: number) => `/api/v1/identity/runs/${runId}/report`,
  
  // Dashboard
  DASHBOARD_SCOUT_SUMMARY: '/api/v1/dashboard/scout/summary',
  DASHBOARD_SCOUT_OPEN_ITEMS: '/api/v1/dashboard/scout/open_items',
  DASHBOARD_YANGO_SUMMARY: '/api/v1/dashboard/yango/summary',
  DASHBOARD_YANGO_RECEIVABLE_ITEMS: '/api/v1/dashboard/yango/receivable_items',
  
  // Payments
  PAYMENTS_ELIGIBILITY: '/api/v1/payments/eligibility',
  
  // Yango Payments
  YANGO_RECONCILIATION_SUMMARY: '/api/v1/yango/payments/reconciliation/summary',
  YANGO_RECONCILIATION_ITEMS: '/api/v1/yango/payments/reconciliation/items',
  YANGO_LEDGER_UNMATCHED: '/api/v1/yango/payments/reconciliation/ledger/unmatched',
  YANGO_LEDGER_MATCHED: '/api/v1/yango/payments/reconciliation/ledger/matched',
  YANGO_DRIVER_DETAIL: (driverId: string) => `/api/v1/yango/payments/reconciliation/driver/${driverId}`,
  
  // Ops
  OPS_ALERTS: '/api/v1/ops/alerts',
  OPS_ACKNOWLEDGE_ALERT: (alertId: number) => `/api/v1/ops/alerts/${alertId}/acknowledge`,
  OPS_DATA_HEALTH: '/api/v1/ops/data-health',
  OPS_RAW_HEALTH_STATUS: '/api/v1/ops/raw-health/status',
  OPS_RAW_HEALTH_FRESHNESS: '/api/v1/ops/raw-health/freshness',
  OPS_RAW_HEALTH_INGESTION_DAILY: '/api/v1/ops/raw-health/ingestion-daily',
  OPS_HEALTH_CHECKS: '/api/v1/ops/health-checks',
  OPS_HEALTH_GLOBAL: '/api/v1/ops/health-global',
} as const;

/**
 * Helper para construir query strings
 */
export function buildQueryString(params: Record<string, any>): string {
  const searchParams = new URLSearchParams();
  
  Object.entries(params).forEach(([key, value]) => {
    if (value !== undefined && value !== null && value !== '') {
      searchParams.set(key, String(value));
    }
  });
  
  const query = searchParams.toString();
  return query ? `?${query}` : '';
}

/**
 * Builder para endpoint de identity runs
 */
export function identityRuns(params?: {
  limit?: number;
  offset?: number;
  status?: 'RUNNING' | 'COMPLETED' | 'FAILED';
  job_type?: 'identity_run' | 'drivers_index_refresh';
}): string {
  const queryParams: Record<string, any> = {};
  
  if (params?.limit !== undefined) queryParams.limit = params.limit;
  if (params?.offset !== undefined) queryParams.offset = params.offset;
  if (params?.status) queryParams.status = params.status;
  if (params?.job_type) queryParams.job_type = params.job_type;
  
  return `${ENDPOINTS.IDENTITY_RUNS}${buildQueryString(queryParams)}`;
}

/**
 * Builder para endpoint de ops alerts
 */
export function opsAlerts(params?: {
  limit?: number;
  offset?: number;
  severity?: 'info' | 'warning' | 'error';
  acknowledged?: boolean;
  week_label?: string;
}): string {
  const queryParams: Record<string, any> = {};
  
  if (params?.limit !== undefined) queryParams.limit = params.limit;
  if (params?.offset !== undefined) queryParams.offset = params.offset;
  if (params?.severity) queryParams.severity = params.severity;
  if (params?.acknowledged !== undefined) queryParams.acknowledged = params.acknowledged;
  if (params?.week_label) queryParams.week_label = params.week_label;
  
  return `${ENDPOINTS.OPS_ALERTS}${buildQueryString(queryParams)}`;
}

/**
 * Builder para endpoint de acknowledge alert
 */
export function opsAcknowledgeAlert(alertId: number): string {
  return ENDPOINTS.OPS_ACKNOWLEDGE_ALERT(alertId);
}

/**
 * Builder para endpoint de ops data health
 */
export function opsDataHealth(): string {
  return ENDPOINTS.OPS_DATA_HEALTH;
}

/**
 * Builder para endpoint de ops raw health status
 */
export function opsRawHealthStatus(params?: {
  limit?: number;
  offset?: number;
  source?: string;
}): string {
  const queryParams: Record<string, any> = {};
  
  if (params?.limit !== undefined) queryParams.limit = params.limit;
  if (params?.offset !== undefined) queryParams.offset = params.offset;
  if (params?.source !== undefined) queryParams.source = params.source;
  
  return `${ENDPOINTS.OPS_RAW_HEALTH_STATUS}${buildQueryString(queryParams)}`;
}

/**
 * Builder para endpoint de ops raw health freshness
 */
export function opsRawHealthFreshness(params?: {
  limit?: number;
  offset?: number;
  source?: string;
}): string {
  const queryParams: Record<string, any> = {};
  
  if (params?.limit !== undefined) queryParams.limit = params.limit;
  if (params?.offset !== undefined) queryParams.offset = params.offset;
  if (params?.source !== undefined) queryParams.source = params.source;
  
  return `${ENDPOINTS.OPS_RAW_HEALTH_FRESHNESS}${buildQueryString(queryParams)}`;
}

/**
 * Builder para endpoint de ops raw health ingestion daily
 */
export function opsRawHealthIngestionDaily(params?: {
  limit?: number;
  offset?: number;
  source?: string;
  date_from?: string;
  date_to?: string;
}): string {
  const queryParams: Record<string, any> = {};
  
  if (params?.limit !== undefined) queryParams.limit = params.limit;
  if (params?.offset !== undefined) queryParams.offset = params.offset;
  if (params?.source !== undefined) queryParams.source = params.source;
  if (params?.date_from !== undefined) queryParams.date_from = params.date_from;
  if (params?.date_to !== undefined) queryParams.date_to = params.date_to;
  
  return `${ENDPOINTS.OPS_RAW_HEALTH_INGESTION_DAILY}${buildQueryString(queryParams)}`;
}



