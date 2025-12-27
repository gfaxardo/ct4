const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

export interface IdentityRegistry {
  person_key: string
  created_at: string
  updated_at: string
  confidence_level: 'HIGH' | 'MEDIUM' | 'LOW'
  primary_phone?: string
  primary_document?: string
  primary_license?: string
  primary_full_name?: string
  flags?: Record<string, any>
}

export interface IdentityLink {
  id: number
  person_key: string
  source_table: string
  source_pk: string
  snapshot_date: string
  match_rule: string
  match_score: number
  confidence_level: 'HIGH' | 'MEDIUM' | 'LOW'
  evidence?: Record<string, any>
  linked_at: string
  run_id?: number
}

export interface PersonDetail {
  person: IdentityRegistry
  links: IdentityLink[]
  driver_links?: IdentityLink[]
  has_driver_conversion: boolean
}

export interface IdentityUnmatched {
  id: number
  source_table: string
  source_pk: string
  snapshot_date: string
  reason_code: string
  details?: Record<string, any>
  candidates_preview?: Record<string, any>
  status: 'OPEN' | 'RESOLVED' | 'IGNORED'
  created_at: string
  resolved_at?: string
  run_id?: number
}

export interface IngestionRun {
  id: number
  started_at: string
  completed_at?: string
  status: 'RUNNING' | 'COMPLETED' | 'FAILED'
  stats?: Record<string, any>
  error_message?: string
  scope_date_from?: string
  scope_date_to?: string
  incremental?: boolean
}

export async function runIngestion(): Promise<IngestionRun> {
  const res = await fetch(`${API_URL}/api/v1/identity/run`, { method: 'POST' })
  if (!res.ok) throw new Error('Error ejecutando ingesta')
  return res.json()
}

export async function listPersons(params?: {
  phone?: string
  document?: string
  license?: string
  name?: string
  confidence_level?: string
  skip?: number
  limit?: number
}): Promise<IdentityRegistry[]> {
  const searchParams = new URLSearchParams()
  if (params) {
    Object.entries(params).forEach(([key, value]) => {
      if (value !== undefined) searchParams.append(key, String(value))
    })
  }
  const res = await fetch(`${API_URL}/api/v1/identity/persons?${searchParams}`)
  if (!res.ok) throw new Error('Error obteniendo personas')
  return res.json()
}

export async function getPerson(personKey: string): Promise<PersonDetail> {
  const res = await fetch(`${API_URL}/api/v1/identity/persons/${personKey}`)
  if (!res.ok) throw new Error('Error obteniendo persona')
  return res.json()
}

export async function listUnmatched(params?: {
  reason_code?: string
  status?: string
  skip?: number
  limit?: number
}): Promise<IdentityUnmatched[]> {
  const searchParams = new URLSearchParams()
  if (params) {
    Object.entries(params).forEach(([key, value]) => {
      if (value !== undefined) searchParams.append(key, String(value))
    })
  }
  const res = await fetch(`${API_URL}/api/v1/identity/unmatched?${searchParams}`)
  if (!res.ok) throw new Error('Error obteniendo unmatched')
  return res.json()
}

export async function resolveUnmatched(id: number, personKey: string): Promise<void> {
  const res = await fetch(`${API_URL}/api/v1/identity/unmatched/${id}/resolve`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ person_key: personKey }),
  })
  if (!res.ok) throw new Error('Error resolviendo unmatched')
}

export async function listIngestionRuns(params?: {
  skip?: number
  limit?: number
}): Promise<IngestionRun[]> {
  const searchParams = new URLSearchParams()
  if (params) {
    Object.entries(params).forEach(([key, value]) => {
      if (value !== undefined) searchParams.append(key, String(value))
    })
  }
  const res = await fetch(`${API_URL}/api/v1/ops/ingestion-runs?${searchParams}`)
  if (!res.ok) throw new Error('Error obteniendo corridas')
  return res.json()
}

export interface Stats {
  total_persons: number
  total_unmatched: number
  total_links: number
}

export async function getStats(): Promise<Stats> {
  const res = await fetch(`${API_URL}/api/v1/identity/stats`)
  if (!res.ok) throw new Error('Error obteniendo estadísticas')
  return res.json()
}

export interface WeeklyData {
  week_start: string
  week_label: string
  source_table: string
  matched: number
  unmatched: number
  processed_total: number
  match_rate: number
  matched_by_rule: Record<string, number>
  matched_by_confidence: Record<string, number>
  unmatched_by_reason: Record<string, number>
  top_missing_keys: Array<{ key: string; count: number }>
}

export interface WeeklyTrend {
  week_label: string
  source_table: string | null
  delta_match_rate: number | null
  delta_matched: number | null
  delta_unmatched: number | null
  current_match_rate: number
  previous_match_rate: number | null
}

export interface ScoutingKPIData {
  week_label: string
  source_table: string
  processed_scouting: number
  candidates_detected: number
  candidate_rate: number
  high_confidence_candidates: number
  avg_time_to_match_days: number | null
}

export interface RunReportResponse {
  run: {
    id: number
    status: string
    started_at?: string
    completed_at?: string
    scope_date_from?: string
    scope_date_to?: string
    incremental?: boolean
  }
  counts_by_source_table: Record<string, {
    total_processed: number
    matched_count: number
    unmatched_count: number
    skipped_count: number
  }>
  matched_breakdown: {
    by_match_rule: Record<string, number>
    by_confidence: Record<string, number>
  }
  unmatched_breakdown: {
    by_reason_code: Record<string, number>
    top_missing_keys: Array<{ key: string; count: number }>
  }
  samples: {
    top_unmatched: Array<any>
    top_matched: Array<any>
  }
  weekly?: WeeklyData[]
  weekly_trend?: WeeklyTrend[]
  available_event_weeks?: string[]
  scouting_kpis?: ScoutingKPIData[]
}

export async function getRunReport(
  runId: number,
  params?: {
    group_by?: 'none' | 'week'
    source_table?: string
    event_week?: string
    event_date_from?: string
    event_date_to?: string
    include_weekly?: boolean
  }
): Promise<RunReportResponse> {
  // #region agent log
  fetch('http://127.0.0.1:7243/ingest/baceb9d4-bf74-4f4f-b924-f2a8877afe92',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({location:'api.ts:getRunReport:entry',message:'Llamando getRunReport',data:{runId,params},timestamp:Date.now(),sessionId:'debug-session',runId:'initial',hypothesisId:'C'})}).catch(()=>{});
  // #endregion
  const searchParams = new URLSearchParams()
  if (params) {
    if (params.group_by) searchParams.append('group_by', params.group_by)
    if (params.source_table) searchParams.append('source_table', params.source_table)
    if (params.event_week) searchParams.append('event_week', params.event_week)
    if (params.event_date_from) searchParams.append('event_date_from', params.event_date_from)
    if (params.event_date_to) searchParams.append('event_date_to', params.event_date_to)
    if (params.include_weekly !== undefined) searchParams.append('include_weekly', String(params.include_weekly))
  }
  const queryString = searchParams.toString()
  const url = `${API_URL}/api/v1/identity/runs/${runId}/report${queryString ? `?${queryString}` : ''}`
  // #region agent log
  fetch('http://127.0.0.1:7243/ingest/baceb9d4-bf74-4f4f-b924-f2a8877afe92',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({location:'api.ts:getRunReport:url',message:'URL construida',data:{url,queryString},timestamp:Date.now(),sessionId:'debug-session',runId:'initial',hypothesisId:'C'})}).catch(()=>{});
  // #endregion
  const res = await fetch(url)
  if (!res.ok) throw new Error('Error obteniendo reporte de corrida')
  const data = await res.json()
  // #region agent log
  fetch('http://127.0.0.1:7243/ingest/baceb9d4-bf74-4f4f-b924-f2a8877afe92',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({location:'api.ts:getRunReport:response',message:'Respuesta recibida',data:{hasWeekly:!!data.weekly,hasWeeklyTrend:!!data.weekly_trend,hasAvailableWeeks:!!data.available_event_weeks,weeklyCount:data.weekly?.length||0,weeklyTrendCount:data.weekly_trend?.length||0},timestamp:Date.now(),sessionId:'debug-session',runId:'initial',hypothesisId:'C'})}).catch(()=>{});
  // #endregion
  return data
}

export interface MetricsScope {
  run_id?: number
  source_table?: string
  event_date_from?: string
  event_date_to?: string
  mode: 'summary' | 'weekly' | 'breakdowns'
}

export interface MetricsResponse {
  scope: MetricsScope
  totals: {
    total_processed: number
    matched: number
    unmatched: number
    match_rate: number
  }
  weekly?: WeeklyData[]
  weekly_trend?: WeeklyTrend[]
  available_event_weeks?: string[]
  breakdowns?: {
    matched_by_rule: Record<string, number>
    matched_by_confidence: Record<string, number>
    unmatched_by_reason: Record<string, number>
  }
}

export async function getGlobalMetrics(params?: {
  mode?: 'summary' | 'weekly' | 'breakdowns'
  source_table?: string
  event_date_from?: string
  event_date_to?: string
}): Promise<MetricsResponse> {
  const searchParams = new URLSearchParams()
  if (params) {
    if (params.mode) searchParams.append('mode', params.mode)
    if (params.source_table) searchParams.append('source_table', params.source_table)
    if (params.event_date_from) searchParams.append('event_date_from', params.event_date_from)
    if (params.event_date_to) searchParams.append('event_date_to', params.event_date_to)
  }
  const queryString = searchParams.toString()
  const url = `${API_URL}/api/v1/identity/metrics/global${queryString ? `?${queryString}` : ''}`
  const res = await fetch(url)
  if (!res.ok) throw new Error('Error obteniendo métricas globales')
  return res.json()
}

export async function getRunMetrics(
  runId: number,
  params?: {
    mode?: 'summary' | 'weekly' | 'breakdowns'
    source_table?: string
    event_date_from?: string
    event_date_to?: string
  }
): Promise<MetricsResponse> {
  const searchParams = new URLSearchParams()
  if (params) {
    if (params.mode) searchParams.append('mode', params.mode)
    if (params.source_table) searchParams.append('source_table', params.source_table)
    if (params.event_date_from) searchParams.append('event_date_from', params.event_date_from)
    if (params.event_date_to) searchParams.append('event_date_to', params.event_date_to)
  }
  const queryString = searchParams.toString()
  const url = `${API_URL}/api/v1/identity/metrics/run/${runId}${queryString ? `?${queryString}` : ''}`
  const res = await fetch(url)
  if (!res.ok) throw new Error('Error obteniendo métricas de corrida')
  return res.json()
}

export async function getWindowMetrics(
  from: string,
  to: string,
  params?: {
    mode?: 'summary' | 'weekly' | 'breakdowns'
    source_table?: string
  }
): Promise<MetricsResponse> {
  const searchParams = new URLSearchParams()
  searchParams.append('from', from)
  searchParams.append('to', to)
  if (params) {
    if (params.mode) searchParams.append('mode', params.mode)
    if (params.source_table) searchParams.append('source_table', params.source_table)
  }
  const queryString = searchParams.toString()
  const url = `${API_URL}/api/v1/identity/metrics/window?${queryString}`
  const res = await fetch(url)
  if (!res.ok) throw new Error('Error obteniendo métricas de ventana')
  return res.json()
}

export interface Alert {
  id: number
  alert_type: string
  severity: 'info' | 'warning' | 'error'
  week_label: string
  message: string
  details?: Record<string, any>
  created_at?: string
  run_id?: number
}

export async function listAlerts(limit: number = 100): Promise<Alert[]> {
  const res = await fetch(`${API_URL}/api/v1/ops/alerts?limit=${limit}`)
  if (!res.ok) throw new Error('Error obteniendo alertas')
  return res.json()
}

export async function acknowledgeAlert(alertId: number): Promise<void> {
  const res = await fetch(`${API_URL}/api/v1/ops/alerts/${alertId}/acknowledge`, {
    method: 'POST',
  })
  if (!res.ok) throw new Error('Error reconociendo alerta')
}

// Dashboard APIs
export interface ScoutSummary {
  totals: {
    payable_amount: number
    payable_items: number
    payable_drivers: number
    payable_scouts: number
    blocked_amount: number
    blocked_items: number
  }
  by_week: Array<{
    week_start_monday: string
    iso_year_week: string
    payable_amount: number
    payable_items: number
    blocked_amount: number
    blocked_items: number
  }>
  top_scouts: Array<{
    acquisition_scout_id: number | null
    acquisition_scout_name: string | null
    amount: number
    items: number
    drivers: number
  }>
}

export interface ScoutOpenItem {
  payment_item_key: string
  person_key: string
  lead_origin: string | null
  scout_id: number | null
  acquisition_scout_id: number | null
  acquisition_scout_name: string | null
  attribution_confidence: string | null
  attribution_rule: string | null
  milestone_type: string | null
  milestone_value: number | null
  payable_date: string | null
  achieved_date: string | null
  amount: number
  currency: string | null
  driver_id: string | null
}

export interface ScoutOpenItems {
  items: ScoutOpenItem[]
  total: number
  limit: number
  offset: number
}

export interface YangoSummary {
  totals: {
    receivable_amount: number
    receivable_items: number
    receivable_drivers: number
  }
  by_week: Array<{
    week_start_monday: string
    iso_year_week: string
    amount: number
    items: number
    drivers: number
  }>
}

export interface YangoReceivableItem {
  pay_week_start_monday: string
  pay_iso_year_week: string
  payable_date: string
  achieved_date: string | null
  lead_date: string | null
  lead_origin: string | null
  payer: string
  milestone_type: string | null
  milestone_value: number | null
  window_days: number | null
  trips_in_window: number | null
  person_key: string
  driver_id: string | null
  amount: number
  currency: string | null
  created_at_export: string | null
}

export interface YangoReceivableItems {
  items: YangoReceivableItem[]
  total: number
  limit: number
  offset: number
}

export async function getScoutSummary(params?: {
  week_start?: string
  week_end?: string
  scout_id?: number
  lead_origin?: 'cabinet' | 'migration'
}): Promise<ScoutSummary> {
  const searchParams = new URLSearchParams()
  if (params) {
    if (params.week_start) searchParams.append('week_start', params.week_start)
    if (params.week_end) searchParams.append('week_end', params.week_end)
    if (params.scout_id) searchParams.append('scout_id', String(params.scout_id))
    if (params.lead_origin) searchParams.append('lead_origin', params.lead_origin)
  }
  const res = await fetch(`${API_URL}/api/v1/dashboard/scout/summary?${searchParams}`)
  if (!res.ok) throw new Error('Error obteniendo resumen scout')
  return res.json()
}

export async function getScoutOpenItems(params?: {
  week_start_monday?: string
  scout_id?: number
  confidence?: 'policy' | 'high' | 'medium' | 'unknown'
  limit?: number
  offset?: number
}): Promise<ScoutOpenItems> {
  const searchParams = new URLSearchParams()
  if (params) {
    if (params.week_start_monday) searchParams.append('week_start_monday', params.week_start_monday)
    if (params.scout_id) searchParams.append('scout_id', String(params.scout_id))
    if (params.confidence) searchParams.append('confidence', params.confidence)
    if (params.limit) searchParams.append('limit', String(params.limit))
    if (params.offset) searchParams.append('offset', String(params.offset))
  }
  const res = await fetch(`${API_URL}/api/v1/dashboard/scout/open_items?${searchParams}`)
  if (!res.ok) throw new Error('Error obteniendo items abiertos scout')
  return res.json()
}

export async function getYangoSummary(params?: {
  week_start?: string
  week_end?: string
}): Promise<YangoSummary> {
  const searchParams = new URLSearchParams()
  if (params) {
    if (params.week_start) searchParams.append('week_start', params.week_start)
    if (params.week_end) searchParams.append('week_end', params.week_end)
  }
  const res = await fetch(`${API_URL}/api/v1/dashboard/yango/summary?${searchParams}`)
  if (!res.ok) throw new Error('Error obteniendo resumen Yango')
  return res.json()
}

export async function getYangoReceivableItems(params?: {
  week_start_monday?: string
  limit?: number
  offset?: number
}): Promise<YangoReceivableItems> {
  const searchParams = new URLSearchParams()
  if (params) {
    if (params.week_start_monday) searchParams.append('week_start_monday', params.week_start_monday)
    if (params.limit) searchParams.append('limit', String(params.limit))
    if (params.offset) searchParams.append('offset', String(params.offset))
  }
  const res = await fetch(`${API_URL}/api/v1/dashboard/yango/receivable_items?${searchParams}`)
  if (!res.ok) throw new Error('Error obteniendo items por cobrar Yango')
  return res.json()
}

// Yango Reconciliation APIs
export interface YangoReconciliationSummaryRow {
  pay_week_start_monday?: string | null
  milestone_value?: number | null
  reconciliation_status?: string | null
  // Campos de summary original (compatibilidad)
  count_items?: number | null
  count_drivers_with_driver_id?: number | null
  count_drivers_with_person_key?: number | null
  count_drivers_total?: number | null
  sum_amount_expected?: number | null
  count_paid?: number | null
  count_pending?: number | null
  count_anomalies?: number | null
  min_payable_date?: string | null
  max_payable_date?: string | null
  min_paid_date?: string | null
  max_paid_date?: string | null
  // Campos de summary_ui (actuales, desde claims)
  rows_count?: number | null
  amount_expected_sum?: number | null
  amount_paid_confirmed_sum?: number | null  // Pagos con identidad confirmada (upstream)
  amount_paid_enriched_sum?: number | null  // Pagos con identidad enriquecida (match por nombre)
  amount_paid_total_visible?: number | null  // Total visible: confirmed + enriched
  amount_paid_sum?: number | null  // Para compatibilidad, alias de amount_paid_total_visible
  amount_paid_assumed?: number | null  // Pagos estimados (pending_active)
  amount_pending_active_sum?: number | null
  amount_pending_expired_sum?: number | null
  amount_diff?: number | null
  amount_diff_assumed?: number | null  // Diff estimado (expected - assumed)
  count_expected?: number | null
  count_paid_confirmed?: number | null  // Count de pagos confirmados
  count_paid_enriched?: number | null  // Count de pagos enriquecidos
  // count_paid ya está definido arriba (compatibilidad, debería ser confirmed + enriched)
  count_pending_active?: number | null
  count_pending_expired?: number | null
  count_drivers?: number | null
  anomalies_total?: number | null  // Alias para count_pending_expired
}

export interface YangoReconciliationSummaryResponse {
  status: string
  count: number
  filters: Record<string, any>
  rows: YangoReconciliationSummaryRow[]
}

export interface YangoReconciliationItemRow {
  pay_week_start_monday?: string | null
  pay_iso_year_week?: string | null
  payable_date?: string | null
  achieved_date?: string | null
  lead_date?: string | null
  lead_origin?: string | null
  payer?: string | null
  milestone_type?: string | null
  milestone_value?: number | null
  window_days?: number | null
  trips_in_window?: number | null
  person_key?: string | null
  driver_id?: string | null
  expected_amount?: number | null
  currency?: string | null
  created_at_export?: string | null
  paid_payment_key?: string | null
  paid_payment_key_confirmed?: string | null  // Payment key del pago confirmado
  paid_payment_key_enriched?: string | null  // Payment key del pago enriquecido
  paid_snapshot_at?: string | null
  paid_source_pk?: string | null
  paid_date?: string | null
  paid_date_confirmed?: string | null  // Fecha del pago confirmado
  paid_date_enriched?: string | null  // Fecha del pago enriquecido
  paid_time?: string | null
  paid_raw_driver_name?: string | null
  paid_driver_name_normalized?: string | null
  paid_is_paid?: boolean | null
  is_paid_confirmed?: boolean | null  // Si el pago está confirmado
  is_paid_enriched?: boolean | null  // Si el pago está enriquecido
  is_paid_effective?: boolean | null
  paid_match_rule?: string | null  // Deprecated, usar match_rule
  paid_match_confidence?: string | null  // Deprecated, usar match_confidence
  match_method?: string | null
  reconciliation_status?: string | null  // Mapeado desde paid_status para compatibilidad
  sort_date?: string | null
  // Campos nuevos de claims view
  due_date?: string | null  // Fecha de vencimiento (lead_date + 14 días)
  window_status?: 'active' | 'expired' | null  // Estado de la ventana: 'active' o 'expired'
  paid_status?: 'paid_confirmed' | 'paid_enriched' | 'pending_active' | 'pending_expired' | null  // Estado real del pago
  // Campos de identity enrichment
  identity_status?: 'confirmed' | 'enriched' | 'ambiguous' | 'no_match' | null  // Estado de identidad desde ledger enriquecido
  match_rule?: string | null  // 'source_upstream' | 'name_full_unique' | 'name_tokens_unique' | 'ambiguous' | 'no_match'
  match_confidence?: 'high' | 'medium' | 'low' | null  // Confianza del match
}

export interface YangoReconciliationItemsResponse {
  status: string
  count: number
  filters: Record<string, any>
  rows: YangoReconciliationItemRow[]
}

export async function getYangoReconciliationSummary(params?: {
  week_start?: string
  milestone_value?: number
  status?: 'paid' | 'pending' | 'anomaly_paid_without_expected'
  mode?: 'real' | 'assumed'  // Modo: 'real' (pagos reales) o 'assumed' (pagos estimados)
  limit?: number
}): Promise<YangoReconciliationSummaryResponse> {
  const searchParams = new URLSearchParams()
  if (params) {
    if (params.week_start) searchParams.append('week_start', params.week_start)
    if (params.milestone_value) searchParams.append('milestone_value', String(params.milestone_value))
    if (params.status) searchParams.append('status', params.status)
    if (params.mode) searchParams.append('mode', params.mode)
    if (params.limit) searchParams.append('limit', String(params.limit))
  }
  const res = await fetch(`${API_URL}/api/v1/yango/payments/reconciliation/summary?${searchParams}`)
  if (!res.ok) throw new Error('Error obteniendo resumen de reconciliación Yango')
  return res.json()
}

export async function getYangoReconciliationItems(params?: {
  status?: 'paid' | 'pending' | 'pending_active' | 'pending_expired' | 'anomaly_paid_without_expected'
  week_start?: string
  milestone_value?: number
  driver_id?: string
  person_key?: string
  limit?: number
  offset?: number
}): Promise<YangoReconciliationItemsResponse> {
  const searchParams = new URLSearchParams()
  if (params) {
    if (params.status) searchParams.append('status', params.status)
    if (params.week_start) searchParams.append('week_start', params.week_start)
    if (params.milestone_value) searchParams.append('milestone_value', String(params.milestone_value))
    if (params.driver_id) searchParams.append('driver_id', params.driver_id)
    if (params.person_key) searchParams.append('person_key', params.person_key)
    if (params.limit) searchParams.append('limit', String(params.limit))
    if (params.offset) searchParams.append('offset', String(params.offset))
  }
  const url = `${API_URL}/api/v1/yango/payments/reconciliation/items?${searchParams}`
  const res = await fetch(url)
  if (!res.ok) throw new Error('Error obteniendo items de reconciliación Yango')
  return res.json()
}

export interface YangoLedgerUnmatchedRow {
  payment_key?: string | null
  pay_date?: string | null
  is_paid?: boolean | null
  milestone_value?: number | null
  driver_id?: string | null  // Alias de driver_id_final
  person_key?: string | null  // Alias de person_key_final
  raw_driver_name?: string | null
  driver_name_normalized?: string | null
  match_rule?: string | null
  match_confidence?: string | null
  latest_snapshot_at?: string | null
  source_pk?: string | null
  identity_source?: string | null  // 'original' | 'enriched_by_name' | 'none' (deprecated, usar identity_status)
  identity_enriched?: boolean | null
  driver_id_final?: string | null
  person_key_final?: string | null
  identity_status?: 'confirmed' | 'enriched' | 'ambiguous' | 'no_match' | null  // Estado de identidad desde ledger enriquecido
}

export interface YangoLedgerUnmatchedResponse {
  status: string
  count: number
  total: number
  filters: Record<string, any>
  rows: YangoLedgerUnmatchedRow[]
}

export async function getYangoLedgerUnmatched(params?: {
  is_paid?: boolean
  milestone_value?: number
  limit?: number
  offset?: number
}): Promise<YangoLedgerUnmatchedResponse> {
  const searchParams = new URLSearchParams()
  if (params) {
    if (params.is_paid !== undefined) searchParams.append('is_paid', String(params.is_paid))
    if (params.milestone_value) searchParams.append('milestone_value', String(params.milestone_value))
    if (params.limit) searchParams.append('limit', String(params.limit))
    if (params.offset) searchParams.append('offset', String(params.offset))
  }
  const url = `${API_URL}/api/v1/yango/payments/reconciliation/ledger/unmatched?${searchParams}`
  const res = await fetch(url)
  if (!res.ok) throw new Error('Error obteniendo ledger sin match')
  return res.json()
}

export async function getYangoLedgerMatched(params?: {
  milestone_value?: number
  limit?: number
  offset?: number
}): Promise<YangoLedgerUnmatchedResponse> {
  const searchParams = new URLSearchParams()
  if (params) {
    if (params.milestone_value) searchParams.append('milestone_value', String(params.milestone_value))
    if (params.limit) searchParams.append('limit', String(params.limit))
    if (params.offset) searchParams.append('offset', String(params.offset))
  }
  const url = `${API_URL}/api/v1/yango/payments/reconciliation/ledger/matched?${searchParams}`
  const res = await fetch(url)
  if (!res.ok) throw new Error('Error obteniendo ledger con match')
  return res.json()
}

export interface ClaimDetailRow {
  milestone_value?: number | null
  expected_amount?: number | null
  currency?: string | null
  lead_date?: string | null
  due_date?: string | null
  pay_week_start_monday?: string | null
  paid_status?: string | null
  paid_payment_key?: string | null
  paid_date?: string | null
  is_paid_effective?: boolean | null
  match_method?: string | null
}

export interface YangoDriverDetailResponse {
  status: string
  driver_id: string
  person_key?: string | null
  claims: ClaimDetailRow[]
  summary: {
    total_expected: number
    total_paid: number
    count_paid: number
    count_pending_active: number
    count_pending_expired: number
  }
}

export async function getYangoDriverDetail(driver_id: string): Promise<YangoDriverDetailResponse> {
  const url = `${API_URL}/api/v1/yango/payments/reconciliation/driver/${encodeURIComponent(driver_id)}`
  const res = await fetch(url)
  if (!res.ok) throw new Error(`Error obteniendo detalle del conductor ${driver_id}`)
  return res.json()
}

// Liquidation APIs
export interface ScoutPreview {
  preview_items: number
  preview_amount: number
}

export interface ScoutMarkPaidRequest {
  scout_id: number
  cutoff_date: string
  paid_by: string
  payment_ref: string
  notes?: string
}

export interface ScoutMarkPaidResponse {
  inserted_items: number
  inserted_amount: number
  preview_items: number
  preview_amount: number
  message: string
}

export async function scoutLiquidationPreview(
  scout_id: number,
  cutoff_date: string
): Promise<ScoutPreview> {
  const searchParams = new URLSearchParams()
  searchParams.append('scout_id', String(scout_id))
  searchParams.append('cutoff_date', cutoff_date)
  const res = await fetch(`${API_URL}/api/v1/liquidation/scout/preview?${searchParams}`)
  if (!res.ok) throw new Error('Error obteniendo preview de liquidación')
  return res.json()
}

export async function scoutLiquidationMarkPaid(
  payload: ScoutMarkPaidRequest,
  adminToken: string
): Promise<ScoutMarkPaidResponse> {
  const res = await fetch(`${API_URL}/api/v1/liquidation/scout/mark_paid`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'X-Admin-Token': adminToken,
    },
    body: JSON.stringify(payload),
  })
  if (!res.ok) {
    const error = await res.json().catch(() => ({ detail: 'Error marcando items como pagados' }))
    throw new Error(error.detail || 'Error marcando items como pagados')
  }
  return res.json()
}


