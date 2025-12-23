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


