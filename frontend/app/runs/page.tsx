'use client'

import { useEffect, useState, useRef } from 'react'
import { listIngestionRuns, runIngestion, IngestionRun, getRunReport, RunReportResponse } from '@/lib/api'
import { formatDate } from '@/lib/utils'
import WeeklyFilters from '@/components/WeeklyFilters'
import WeeklyMetricsView from '@/components/WeeklyMetricsView'

export default function RunsPage() {
  const [runs, setRuns] = useState<IngestionRun[]>([])
  const [loading, setLoading] = useState(true)
  const [running, setRunning] = useState(false)
  const [selectedReport, setSelectedReport] = useState<RunReportResponse | null>(null)
  const [loadingReport, setLoadingReport] = useState(false)
  const [viewMode, setViewMode] = useState<'summary' | 'weekly'>('summary')
  const [selectedWeek, setSelectedWeek] = useState<string>('')
  const [selectedSource, setSelectedSource] = useState<string>('')
  const pollIntervalRef = useRef<NodeJS.Timeout | null>(null)

  useEffect(() => {
    loadRuns()
    return () => {
      if (pollIntervalRef.current) {
        clearInterval(pollIntervalRef.current)
      }
    }
  }, [])

  useEffect(() => {
    if (selectedReport?.run.id) {
      const runId = selectedReport.run.id
      setLoadingReport(true)
      const params: any = viewMode === 'weekly' 
        ? { group_by: 'week', include_weekly: true }
        : { group_by: 'none', include_weekly: false }
      
      getRunReport(runId, params)
        .then(report => {
          setSelectedReport(report)
          if (viewMode === 'weekly' && report.available_event_weeks && report.available_event_weeks.length > 0 && !selectedWeek) {
            setSelectedWeek(report.available_event_weeks[report.available_event_weeks.length - 1])
          }
        })
        .catch(error => {
          console.error('Error cargando reporte:', error)
          alert('Error cargando reporte')
        })
        .finally(() => {
          setLoadingReport(false)
        })
    }
  }, [viewMode, selectedReport?.run.id])

  async function loadRuns() {
    setLoading(true)
    try {
      const data = await listIngestionRuns({ limit: 50 })
      setRuns(data)
    } catch (error) {
      console.error('Error cargando corridas:', error)
    } finally {
      setLoading(false)
    }
  }

  async function handleRunIngestion() {
    if (running) return
    
    setRunning(true)
    try {
      const newRun = await runIngestion()
      await loadRuns()
      
      if (newRun.status === 'RUNNING') {
        if (pollIntervalRef.current) {
          clearInterval(pollIntervalRef.current)
        }
        
        pollIntervalRef.current = setInterval(async () => {
          try {
            const updatedRuns = await listIngestionRuns({ limit: 50 })
            setRuns(updatedRuns)
            
            const currentRun = updatedRuns.find(r => r.id === newRun.id)
            if (currentRun && (currentRun.status === 'COMPLETED' || currentRun.status === 'FAILED')) {
              if (pollIntervalRef.current) {
                clearInterval(pollIntervalRef.current)
                pollIntervalRef.current = null
              }
              setRunning(false)
            }
          } catch (error) {
            console.error('Error en polling:', error)
            if (pollIntervalRef.current) {
              clearInterval(pollIntervalRef.current)
              pollIntervalRef.current = null
            }
            setRunning(false)
          }
        }, 2000)
        
        setTimeout(() => {
          if (pollIntervalRef.current) {
            clearInterval(pollIntervalRef.current)
            pollIntervalRef.current = null
          }
          setRunning(false)
        }, 600000)
      } else {
        setRunning(false)
      }
    } catch (error) {
      console.error('Error ejecutando ingesta:', error)
      alert('Error ejecutando ingesta')
      setRunning(false)
    }
  }

  async function handleViewReport(runId: number) {
    setLoadingReport(true)
    try {
      const params: any = {
        group_by: 'none',
        include_weekly: false
      }
      const report = await getRunReport(runId, params)
      setSelectedReport(report)
    } catch (error) {
      console.error('Error cargando reporte:', error)
      alert('Error cargando reporte')
    } finally {
      setLoadingReport(false)
    }
  }

  async function handleApplyFilters(runId: number) {
    setLoadingReport(true)
    try {
      const params: any = {
        group_by: 'week',
        include_weekly: true
      }
      if (selectedSource && selectedSource !== 'all') {
        params.source_table = selectedSource
      }
      if (selectedWeek) {
        params.event_week = selectedWeek
      }
      const report = await getRunReport(runId, params)
      setSelectedReport(report)
    } catch (error) {
      console.error('Error cargando reporte semanal:', error)
      alert('Error cargando reporte semanal')
    } finally {
      setLoadingReport(false)
    }
  }

  return (
    <div className="px-4 py-6">
      <div className="flex justify-between items-center mb-6">
        <h1 className="text-3xl font-bold">Corridas de Ingesta</h1>
        <button
          onClick={handleRunIngestion}
          disabled={running}
          className="bg-blue-600 text-white px-4 py-2 rounded-md hover:bg-blue-700 disabled:bg-gray-400 disabled:cursor-not-allowed"
        >
          {running ? 'Ejecutando...' : 'Ejecutar Ingesta'}
        </button>
      </div>

      {loading ? (
        <div className="text-center py-12">Cargando...</div>
      ) : (
        <div className="bg-white rounded-lg shadow overflow-hidden">
          <table className="min-w-full divide-y divide-gray-200">
            <thead className="bg-gray-50">
              <tr>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">ID</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Estado</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Iniciada</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Completada</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Estadísticas</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Error</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Acciones</th>
              </tr>
            </thead>
            <tbody className="bg-white divide-y divide-gray-200">
              {runs.map((run) => (
                <tr key={run.id} className="hover:bg-gray-50">
                  <td className="px-6 py-4 whitespace-nowrap text-sm font-mono">{run.id}</td>
                  <td className="px-6 py-4 whitespace-nowrap">
                    <span className={`px-2 py-1 text-xs font-semibold rounded-full ${
                      run.status === 'COMPLETED' ? 'bg-green-100 text-green-800' :
                      run.status === 'FAILED' ? 'bg-red-100 text-red-800' :
                      'bg-yellow-100 text-yellow-800'
                    }`}>
                      {run.status}
                    </span>
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">{formatDate(run.started_at)}</td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                    {run.completed_at ? formatDate(run.completed_at) : '-'}
                  </td>
                  <td className="px-6 py-4 text-sm">
                    {run.stats && (
                      <details>
                        <summary className="cursor-pointer text-blue-600 hover:text-blue-800">Ver</summary>
                        <pre className="mt-2 text-xs bg-gray-50 p-2 rounded overflow-auto max-h-40">
                          {JSON.stringify(run.stats, null, 2)}
                        </pre>
                      </details>
                    )}
                  </td>
                  <td className="px-6 py-4 text-sm text-red-600">
                    {run.error_message || '-'}
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm">
                    {run.status === 'COMPLETED' && (
                      <button
                        onClick={() => handleViewReport(run.id)}
                        disabled={loadingReport}
                        className="text-blue-600 hover:text-blue-800 disabled:text-gray-400"
                      >
                        {loadingReport ? 'Cargando...' : 'Ver Reporte'}
                      </button>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
          {runs.length === 0 && (
            <div className="text-center py-12 text-gray-500">No se encontraron corridas</div>
          )}
        </div>
      )}

      {selectedReport && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-lg shadow-xl max-w-6xl w-full max-h-[90vh] overflow-y-auto">
            <div className="p-6">
              <div className="flex justify-between items-center mb-4">
                <h2 className="text-2xl font-bold">Reporte de Corrida #{selectedReport.run.id}</h2>
                <button
                  onClick={() => {
                    setSelectedReport(null)
                    setViewMode('summary')
                    setSelectedWeek('')
                    setSelectedSource('')
                  }}
                  className="text-gray-500 hover:text-gray-700 text-2xl"
                >
                  ×
                </button>
              </div>

              <WeeklyFilters
                viewMode={viewMode}
                onViewModeChange={setViewMode}
                availableWeeks={selectedReport.available_event_weeks}
                selectedWeek={selectedWeek}
                selectedSource={selectedSource}
                onWeekChange={setSelectedWeek}
                onSourceChange={setSelectedSource}
                onApplyFilters={() => handleApplyFilters(selectedReport.run.id)}
                loading={loadingReport}
                weeklyLabel="Semanal (evento)"
              />

              {/* #region agent log */}
              {selectedReport && (() => {
                fetch('http://127.0.0.1:7243/ingest/baceb9d4-bf74-4f4f-b924-f2a8877afe92',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({location:'runs/page.tsx:render:check',message:'Renderizando reporte',data:{viewMode,hasWeekly:!!selectedReport.weekly,weeklyCount:selectedReport.weekly?.length||0,hasWeeklyTrend:!!selectedReport.weekly_trend},timestamp:Date.now(),sessionId:'debug-session',runId:'initial',hypothesisId:'E'})}).catch(()=>{});
                return null;
              })()}
              {/* #endregion */}
              {viewMode === 'summary' ? (
                <>
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mb-6">
                    <div className="bg-gray-50 p-4 rounded">
                      <h3 className="font-semibold mb-2">Matched Breakdown</h3>
                  <div className="space-y-2">
                    <div>
                      <p className="text-sm font-medium">Por Regla:</p>
                      <ul className="text-sm mt-1 space-y-1">
                        {Object.entries(selectedReport.matched_breakdown.by_match_rule).map(([rule, count]) => (
                          <li key={rule} className="flex justify-between">
                            <span>{rule}:</span>
                            <span className="font-medium">{count}</span>
                          </li>
                        ))}
                      </ul>
                    </div>
                    <div className="mt-3">
                      <p className="text-sm font-medium">Por Confianza:</p>
                      <ul className="text-sm mt-1 space-y-1">
                        {Object.entries(selectedReport.matched_breakdown.by_confidence).map(([conf, count]) => (
                          <li key={conf} className="flex justify-between">
                            <span>{conf}:</span>
                            <span className="font-medium">{count}</span>
                          </li>
                        ))}
                      </ul>
                    </div>
                  </div>
                </div>

                <div className="bg-gray-50 p-4 rounded">
                  <h3 className="font-semibold mb-2">Unmatched Breakdown</h3>
                  <div className="space-y-2">
                    <div>
                      <p className="text-sm font-medium">Por Razón:</p>
                      <ul className="text-sm mt-1 space-y-1">
                        {Object.entries(selectedReport.unmatched_breakdown.by_reason_code).map(([reason, count]) => (
                          <li key={reason} className="flex justify-between">
                            <span>{reason}:</span>
                            <span className="font-medium">{count}</span>
                          </li>
                        ))}
                      </ul>
                    </div>
                    {selectedReport.unmatched_breakdown.top_missing_keys.length > 0 && (
                      <div className="mt-3">
                        <p className="text-sm font-medium">Top Missing Keys:</p>
                        <ul className="text-sm mt-1 space-y-1">
                          {selectedReport.unmatched_breakdown.top_missing_keys.map((item) => (
                            <li key={item.key} className="flex justify-between">
                              <span>{item.key}:</span>
                              <span className="font-medium">{item.count}</span>
                            </li>
                          ))}
                        </ul>
                      </div>
                    )}
                  </div>
                </div>
              </div>

              <div className="mb-6">
                <h3 className="font-semibold mb-2">Conteos por Fuente</h3>
                <div className="bg-gray-50 p-4 rounded">
                  <pre className="text-sm overflow-auto">
                    {JSON.stringify(selectedReport.counts_by_source_table, null, 2)}
                  </pre>
                </div>
              </div>

                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    <div>
                      <h3 className="font-semibold mb-2">Top Matched (10)</h3>
                      <div className="bg-gray-50 p-4 rounded max-h-60 overflow-y-auto">
                        <pre className="text-xs">
                          {JSON.stringify(selectedReport.samples.top_matched, null, 2)}
                        </pre>
                      </div>
                    </div>
                    <div>
                      <h3 className="font-semibold mb-2">Top Unmatched (10)</h3>
                      <div className="bg-gray-50 p-4 rounded max-h-60 overflow-y-auto">
                        <pre className="text-xs">
                          {JSON.stringify(selectedReport.samples.top_unmatched, null, 2)}
                        </pre>
                      </div>
                    </div>
                  </div>
                </>
              ) : (
                <>
                  <WeeklyMetricsView
                    weekly={selectedReport.weekly || []}
                    weekly_trend={selectedReport.weekly_trend}
                    loading={loadingReport}
                  />
                  
                  {selectedReport.scouting_kpis && selectedReport.scouting_kpis.length > 0 && (
                    <div className="mt-8">
                      <h3 className="font-semibold mb-3 text-lg">Scouting — Observación (Pre-Atribución)</h3>
                      <div className="overflow-x-auto">
                        <table className="min-w-full divide-y divide-gray-200">
                          <thead className="bg-gray-50">
                            <tr>
                              <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Semana</th>
                              <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Processed</th>
                              <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Candidates</th>
                              <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Candidate Rate</th>
                              <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">High Confidence</th>
                              <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Avg Time to Match (días)</th>
                            </tr>
                          </thead>
                          <tbody className="bg-white divide-y divide-gray-200">
                            {selectedReport.scouting_kpis.map((kpi, idx) => (
                              <tr key={idx} className="hover:bg-gray-50">
                                <td className="px-4 py-3 text-sm">{kpi.week_label}</td>
                                <td className="px-4 py-3 text-sm">{kpi.processed_scouting}</td>
                                <td className="px-4 py-3 text-sm">{kpi.candidates_detected}</td>
                                <td className="px-4 py-3 text-sm font-medium">{kpi.candidate_rate.toFixed(2)}%</td>
                                <td className="px-4 py-3 text-sm">{kpi.high_confidence_candidates}</td>
                                <td className="px-4 py-3 text-sm">{kpi.avg_time_to_match_days !== null ? kpi.avg_time_to_match_days.toFixed(2) : '-'}</td>
                              </tr>
                            ))}
                          </tbody>
                        </table>
                      </div>
                    </div>
                  )}
                </>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  )
}


