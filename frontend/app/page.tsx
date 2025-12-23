'use client'

import { useEffect, useState } from 'react'
import { listIngestionRuns, getStats, IngestionRun, getRunReport, RunReportResponse, getGlobalMetrics, MetricsResponse, listAlerts, acknowledgeAlert, Alert } from '@/lib/api'
import Link from 'next/link'
import WeeklyFilters from '@/components/WeeklyFilters'
import WeeklyMetricsView from '@/components/WeeklyMetricsView'

export default function Dashboard() {
  const [stats, setStats] = useState({
    totalPersons: 0,
    totalUnmatched: 0,
    lastRun: null as IngestionRun | null,
  })
  const [runReport, setRunReport] = useState<RunReportResponse | null>(null)
  const [globalMetrics, setGlobalMetrics] = useState<MetricsResponse | null>(null)
  const [viewMode, setViewMode] = useState<'summary' | 'weekly'>('summary')
  const [selectedWeek, setSelectedWeek] = useState<string>('')
  const [selectedSource, setSelectedSource] = useState<string>('')
  const [globalWeeklyMetrics, setGlobalWeeklyMetrics] = useState<MetricsResponse | null>(null)
  const [loadingWeekly, setLoadingWeekly] = useState(false)
  const [loading, setLoading] = useState(true)
  const [alerts, setAlerts] = useState<Alert[]>([])
  const [loadingAlerts, setLoadingAlerts] = useState(false)

  useEffect(() => {
    async function loadStats() {
      try {
        const [statsData, runs] = await Promise.all([
          getStats(),
          listIngestionRuns({ limit: 1 }),
        ])

        const lastRun = runs[0] || null
        setStats({
          totalPersons: statsData.total_persons,
          totalUnmatched: statsData.total_unmatched,
          lastRun,
        })

        // Cargar métricas globales para el dashboard (inicialmente breakdowns)
        try {
          const metrics = await getGlobalMetrics({ mode: 'breakdowns' })
          setGlobalMetrics(metrics)
        } catch (error) {
          console.error('Error cargando métricas globales:', error)
        }

        // Cargar reporte de última corrida para mostrar detalles específicos
        if (lastRun && lastRun.status === 'COMPLETED') {
          try {
            const report = await getRunReport(lastRun.id)
            setRunReport(report)
          } catch (error) {
            console.error('Error cargando reporte:', error)
          }
        }
      } catch (error) {
        console.error('Error cargando estadísticas:', error)
      } finally {
        setLoading(false)
      }
    }
    loadStats()
    loadAlerts()
  }, [])
  
  async function loadAlerts() {
    setLoadingAlerts(true)
    try {
      const alertsData = await listAlerts(50)
      setAlerts(alertsData)
    } catch (error) {
      console.error('Error cargando alertas:', error)
    } finally {
      setLoadingAlerts(false)
    }
  }
  
  async function handleAcknowledgeAlert(alertId: number) {
    try {
      await acknowledgeAlert(alertId)
      setAlerts(alerts.filter(a => a.id !== alertId))
    } catch (error) {
      console.error('Error reconociendo alerta:', error)
      alert('Error reconociendo alerta')
    }
  }

  useEffect(() => {
    async function loadMetricsByMode() {
      try {
        if (viewMode === 'weekly') {
          setLoadingWeekly(true)
          const weeklyMetrics = await getGlobalMetrics({ mode: 'weekly' })
          setGlobalWeeklyMetrics(weeklyMetrics)
          if (weeklyMetrics.available_event_weeks && weeklyMetrics.available_event_weeks.length > 0) {
            setSelectedWeek(prev => prev || weeklyMetrics.available_event_weeks![weeklyMetrics.available_event_weeks!.length - 1])
          }
          setLoadingWeekly(false)
        } else {
          const metrics = await getGlobalMetrics({ mode: 'breakdowns' })
          setGlobalMetrics(metrics)
        }
      } catch (error) {
        console.error('Error cargando métricas:', error)
        setLoadingWeekly(false)
      }
    }
    loadMetricsByMode()
  }, [viewMode])

  function parseEventWeek(weekLabel: string): { from: string; to: string } | null {
    try {
      const [yearStr, weekStr] = weekLabel.split('-W')
      const year = parseInt(yearStr, 10)
      const week = parseInt(weekStr, 10)
      
      if (isNaN(year) || isNaN(week) || week < 1 || week > 53) {
        return null
      }
      
      const simple = new Date(year, 0, 1 + (week - 1) * 7)
      const dow = simple.getDay()
      const ISOweekStart = simple
      if (dow <= 4) {
        ISOweekStart.setDate(simple.getDate() - simple.getDay() + 1)
      } else {
        ISOweekStart.setDate(simple.getDate() + 8 - simple.getDay())
      }
      
      const weekStart = new Date(ISOweekStart)
      const weekEnd = new Date(weekStart)
      weekEnd.setDate(weekStart.getDate() + 6)
      
      return {
        from: weekStart.toISOString().split('T')[0],
        to: weekEnd.toISOString().split('T')[0]
      }
    } catch {
      return null
    }
  }

  async function handleApplyWeeklyFilters() {
    setLoadingWeekly(true)
    try {
      const params: any = { mode: 'weekly' }
      if (selectedSource && selectedSource !== 'all') {
        params.source_table = selectedSource
      }
      if (selectedWeek) {
        const weekDates = parseEventWeek(selectedWeek)
        if (weekDates) {
          params.event_date_from = weekDates.from
          params.event_date_to = weekDates.to
        }
      }
      const metrics = await getGlobalMetrics(params)
      setGlobalWeeklyMetrics(metrics)
    } catch (error) {
      console.error('Error cargando métricas semanales:', error)
      alert('Error cargando métricas semanales')
    } finally {
      setLoadingWeekly(false)
    }
  }

  if (loading) {
    return <div className="text-center py-12">Cargando...</div>
  }

  const matchRate = stats.totalPersons > 0
    ? ((stats.totalPersons / (stats.totalPersons + stats.totalUnmatched)) * 100).toFixed(1)
    : '0'

  return (
    <div className="px-4 py-6">
      <h1 className="text-3xl font-bold mb-6">Dashboard</h1>
      
      {alerts.length > 0 && (
        <div className="mb-6">
          <h2 className="text-xl font-bold mb-3">Alertas Activas</h2>
          <div className="space-y-2">
            {alerts.map((alert) => (
              <div
                key={alert.id}
                className={`p-4 rounded-lg border-l-4 ${
                  alert.severity === 'error'
                    ? 'bg-red-50 border-red-500'
                    : alert.severity === 'warning'
                    ? 'bg-yellow-50 border-yellow-500'
                    : 'bg-blue-50 border-blue-500'
                }`}
              >
                <div className="flex justify-between items-start">
                  <div className="flex-1">
                    <div className="flex items-center gap-2 mb-1">
                      <span className={`px-2 py-1 text-xs font-semibold rounded ${
                        alert.severity === 'error'
                          ? 'bg-red-200 text-red-800'
                          : alert.severity === 'warning'
                          ? 'bg-yellow-200 text-yellow-800'
                          : 'bg-blue-200 text-blue-800'
                      }`}>
                        {alert.severity.toUpperCase()}
                      </span>
                      <span className="text-sm font-medium text-gray-700">{alert.week_label}</span>
                    </div>
                    <p className="text-sm text-gray-700">{alert.message}</p>
                    {alert.details && (
                      <details className="mt-2">
                        <summary className="text-xs text-gray-500 cursor-pointer">Ver detalles</summary>
                        <pre className="mt-1 text-xs bg-white p-2 rounded overflow-auto">
                          {JSON.stringify(alert.details, null, 2)}
                        </pre>
                      </details>
                    )}
                  </div>
                  <button
                    onClick={() => handleAcknowledgeAlert(alert.id)}
                    className="ml-4 px-3 py-1 text-xs bg-gray-200 hover:bg-gray-300 rounded text-gray-700"
                  >
                    Reconocer
                  </button>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-8">
        <div className="bg-white rounded-lg shadow p-6">
          <h2 className="text-sm font-medium text-gray-500 mb-2">Personas Identificadas</h2>
          <p className="text-3xl font-bold">{stats.totalPersons}</p>
        </div>

        <div className="bg-white rounded-lg shadow p-6">
          <h2 className="text-sm font-medium text-gray-500 mb-2">Sin Resolver</h2>
          <p className="text-3xl font-bold">{stats.totalUnmatched}</p>
        </div>

        <div className="bg-white rounded-lg shadow p-6">
          <h2 className="text-sm font-medium text-gray-500 mb-2">Tasa de Match</h2>
          <p className="text-3xl font-bold">{matchRate}%</p>
        </div>
      </div>

      <div className="mb-6">
        <h2 className="text-2xl font-bold mb-4">Métricas Semanales (Global)</h2>
        <WeeklyFilters
          viewMode={viewMode}
          onViewModeChange={setViewMode}
          availableWeeks={globalWeeklyMetrics?.available_event_weeks}
          selectedWeek={selectedWeek}
          selectedSource={selectedSource}
          onWeekChange={setSelectedWeek}
          onSourceChange={setSelectedSource}
          onApplyFilters={handleApplyWeeklyFilters}
          loading={loadingWeekly}
          weeklyLabel="Semanal (Global)"
        />
      </div>

      {/* Métricas Globales */}
      {viewMode === 'summary' && globalMetrics && (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mb-8">
          <div className="bg-white rounded-lg shadow p-6">
            <h2 className="text-lg font-semibold mb-4">Matched por Regla (Global)</h2>
            <div className="space-y-2">
              {globalMetrics.breakdowns && Object.entries(globalMetrics.breakdowns.matched_by_rule).map(([rule, count]) => (
                <div key={rule} className="flex justify-between items-center">
                  <span className="text-sm">{rule}</span>
                  <span className="font-medium">{count}</span>
                </div>
              ))}
              {(!globalMetrics.breakdowns || Object.keys(globalMetrics.breakdowns.matched_by_rule).length === 0) && (
                <p className="text-sm text-gray-500">No hay matches</p>
              )}
            </div>
          </div>

          <div className="bg-white rounded-lg shadow p-6">
            <h2 className="text-lg font-semibold mb-4">Unmatched por Razón (Top 5) - Global</h2>
            <div className="space-y-2">
              {globalMetrics.breakdowns && Object.entries(globalMetrics.breakdowns.unmatched_by_reason)
                .slice(0, 5)
                .map(([reason, count]) => (
                  <div key={reason} className="flex justify-between items-center">
                    <span className="text-sm">{reason}</span>
                    <span className="font-medium">{count}</span>
                  </div>
                ))}
              {(!globalMetrics.breakdowns || Object.keys(globalMetrics.breakdowns.unmatched_by_reason).length === 0) && (
                <p className="text-sm text-gray-500">No hay unmatched</p>
              )}
            </div>
          </div>
        </div>
      )}

      {viewMode === 'weekly' && (
        <WeeklyMetricsView
          weekly={globalWeeklyMetrics?.weekly || []}
          weekly_trend={globalWeeklyMetrics?.weekly_trend}
          loading={loadingWeekly}
        />
      )}

      {stats.lastRun && (
        <div className="bg-white rounded-lg shadow p-6 mb-6">
          <h2 className="text-lg font-semibold mb-4">Última Corrida</h2>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            <div>
              <p className="text-sm text-gray-500">Estado</p>
              <p className="font-medium">{stats.lastRun.status}</p>
            </div>
            <div>
              <p className="text-sm text-gray-500">Iniciada</p>
              <p className="font-medium">{new Date(stats.lastRun.started_at).toLocaleString('es-ES')}</p>
            </div>
            {stats.lastRun.completed_at && (
              <div>
                <p className="text-sm text-gray-500">Completada</p>
                <p className="font-medium">{new Date(stats.lastRun.completed_at).toLocaleString('es-ES')}</p>
              </div>
            )}
            <div>
              <Link href="/runs" className="text-blue-600 hover:text-blue-800">
                Ver todas →
              </Link>
            </div>
          </div>
        </div>
      )}

      {/* Reporte de Última Corrida (para referencia) */}
      {runReport && (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          <div className="bg-white rounded-lg shadow p-6">
            <h2 className="text-lg font-semibold mb-4">Matched por Regla (Última Corrida)</h2>
            <div className="space-y-2">
              {Object.entries(runReport.matched_breakdown.by_match_rule).map(([rule, count]) => (
                <div key={rule} className="flex justify-between items-center">
                  <span className="text-sm">{rule}</span>
                  <span className="font-medium">{count}</span>
                </div>
              ))}
              {Object.keys(runReport.matched_breakdown.by_match_rule).length === 0 && (
                <p className="text-sm text-gray-500">No hay matches en este run</p>
              )}
            </div>
          </div>

          <div className="bg-white rounded-lg shadow p-6">
            <h2 className="text-lg font-semibold mb-4">Unmatched por Razón (Top 5) - Última Corrida</h2>
            <div className="space-y-2">
              {Object.entries(runReport.unmatched_breakdown.by_reason_code)
                .slice(0, 5)
                .map(([reason, count]) => (
                  <div key={reason} className="flex justify-between items-center">
                    <span className="text-sm">{reason}</span>
                    <span className="font-medium">{count}</span>
                  </div>
                ))}
              {Object.keys(runReport.unmatched_breakdown.by_reason_code).length === 0 && (
                <p className="text-sm text-gray-500">No hay unmatched en este run</p>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  )
}


